/**
 * Jessibuca self-contained demo player (English build)
 * Requires: jQuery + Bootstrap 5 + jessibuca (v3) core
 * Every asset is referenced by a local relative path.
 */
(function ($) {
    'use strict';

    var DECODER_PATH = 'player/jessibuca/decoder.js';
    var STORAGE_URL_KEY = 'jb_local_url_history';
    var STORAGE_CFG_KEY = 'jb_local_config';
    var MAX_LOG = 500;

    var player = null;      // Jessibuca instance
    var configDirty = false; // an init-time option changed; the instance must be rebuilt
    var recording = false;
    var suppressMuteLog = false; // don't log the volume set during initialisation

    /* ------------------------------------------------------------------ */
    /* Log                                                                 */
    /* ------------------------------------------------------------------ */
    var $log = $('#logPanel');

    function pad(n) {
        return n < 10 ? '0' + n : '' + n;
    }

    function nowText() {
        var d = new Date();
        return pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    }

    function log(msg, level) {
        level = level || 'info';
        var $line = $('<div>').addClass('jb-log-' + level);
        $('<span>').addClass('jb-log-time').text('[' + nowText() + ']').appendTo($line);
        $line.append(document.createTextNode(msg));
        $log.append($line);
        var children = $log.children();
        if (children.length > MAX_LOG) {
            children.slice(0, children.length - MAX_LOG).remove();
        }
        $log.scrollTop($log[0].scrollHeight);
    }

    /* ------------------------------------------------------------------ */
    /* Helpers                                                             */
    /* ------------------------------------------------------------------ */
    function formatBytes(bytes) {
        if (!bytes && bytes !== 0) return '-';
        if (bytes > 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + ' MB/s';
        if (bytes > 1024) return (bytes / 1024).toFixed(2) + ' KB/s';
        return bytes + ' B/s';
    }

    function formatDuration(seconds) {
        seconds = Math.floor(seconds || 0);
        var h = Math.floor(seconds / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        var s = seconds % 60;
        return (h > 0 ? pad(h) + ':' : '') + pad(m) + ':' + pad(s);
    }

    function errorText(err) {
        var map = {
            playError: 'Playback failed: the url is empty',
            fetchError: 'http request failed',
            websocketError: 'websocket request failed',
            webcodecsH265NotSupport: 'webcodecs does not support H265',
            mediaSourceH265NotSupport: 'MediaSource does not support H265',
            wasmDecodeError: 'wasm decoding failed'
        };
        return map[err] || String(err);
    }

    /* ------------------------------------------------------------------ */
    /* Configuration                                                       */
    /* ------------------------------------------------------------------ */
    // The decoders are rendered as checkboxes but are mutually exclusive (same as the official demo)
    function decodeMode() {
        return $('.jb-decoder:checked').first().val() || 'wasm';
    }

    function buildConfig() {
        var mode = decodeMode();
        var scaleMode = parseInt($('#scaleMode').val(), 10);
        var timeoutReplay = $('#optTimeoutReplay').prop('checked');

        var config = {
            container: document.getElementById('container'),
            decoder: DECODER_PATH,
            videoBuffer: parseFloat($('#videoBuffer').val()) || 0,
            loadingTimeout: parseInt($('#loadingTimeout').val(), 10) || 10,
            heartTimeout: parseInt($('#heartTimeout').val(), 10) || 10,
            isResize: scaleMode === 1,
            isFullResize: scaleMode === 2,
            isFlv: $('#optIsFlv').prop('checked'),
            debug: $('#optDebug').prop('checked'),
            hasAudio: $('#optHasAudio').prop('checked'),
            isNotMute: $('#optIsNotMute').prop('checked'),
            showBandwidth: $('#optShowBandwidth').prop('checked'),
            hotKey: $('#optHotKey').prop('checked'),
            autoWasm: $('#optAutoWasm').prop('checked'),
            supportDblclickFullscreen: $('#optDblclick').prop('checked'),
            hiddenAutoPause: $('#optHiddenAutoPause').prop('checked'),
            keepScreenOn: $('#optKeepScreenOn').prop('checked'),
            controlAutoHide: $('#optControlAutoHide').prop('checked'),
            recordType: $('#recordType').val(),
            loadingText: 'Loading...',
            heartTimeoutReplay: timeoutReplay,
            loadingTimeoutReplay: timeoutReplay,
            wasmDecodeErrorReplay: timeoutReplay,
            useMSE: mode === 'mse',
            useWCS: mode === 'wcs',
            // MediaSource hardware decoding does not support offscreen rendering
            forceNoOffscreen: mode === 'mse',
            operateBtns: {
                fullscreen: true,
                screenshot: true,
                play: true,
                audio: true,
                record: true
            }
        };
        return config;
    }

    function saveConfig() {
        try {
            var data = {
                decodeMode: decodeMode(),
                videoBuffer: $('#videoBuffer').val(),
                recordType: $('#recordType').val(),
                loadingTimeout: $('#loadingTimeout').val(),
                heartTimeout: $('#heartTimeout').val(),
                scaleMode: $('#scaleMode').val(),
                rotate: $('#rotate').val(),
                checks: {}
            };
            $('input[type="checkbox"]').not('.jb-decoder').each(function () {
                data.checks[this.id] = $(this).prop('checked');
            });
            localStorage.setItem(STORAGE_CFG_KEY, JSON.stringify(data));
        } catch (e) { /* ignore failures in private browsing mode */ }
    }

    function restoreConfig() {
        var data = null;
        try {
            data = JSON.parse(localStorage.getItem(STORAGE_CFG_KEY) || 'null');
        } catch (e) { /* ignore */ }
        if (!data) return;
        if (data.decodeMode) {
            $('.jb-decoder').prop('checked', false);
            $('.jb-decoder[value="' + data.decodeMode + '"]').prop('checked', true);
        }
        ['videoBuffer', 'recordType', 'loadingTimeout', 'heartTimeout', 'scaleMode', 'rotate'].forEach(function (id) {
            if (data[id] !== undefined && data[id] !== null) $('#' + id).val(data[id]);
        });
        $.each(data.checks || {}, function (id, checked) {
            $('#' + id).prop('checked', !!checked);
        });
    }

    /* ------------------------------------------------------------------ */
    /* URL history                                                         */
    /* ------------------------------------------------------------------ */
    function urlHistory() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_URL_KEY) || '[]');
        } catch (e) {
            return [];
        }
    }

    function pushUrlHistory(url) {
        var list = urlHistory().filter(function (item) {
            return item !== url;
        });
        list.unshift(url);
        list = list.slice(0, 10);
        try {
            localStorage.setItem(STORAGE_URL_KEY, JSON.stringify(list));
        } catch (e) { /* ignore */ }
        renderUrlHistory(list);
    }

    function renderUrlHistory(list) {
        var $dl = $('#urlHistory').empty();
        (list || urlHistory()).forEach(function (url) {
            $('<option>').attr('value', url).appendTo($dl);
        });
    }

    /* ------------------------------------------------------------------ */
    /* Stats panel                                                         */
    /* ------------------------------------------------------------------ */
    function setStat(id, value) {
        $('#' + id).text(value === undefined || value === null || value === '' ? '-' : value);
    }

    function resetStats() {
        ['stResolution', 'stAudio', 'stFps', 'stVbps', 'stAbps', 'stBuf',
            'stTs', 'stKbps', 'stPerformance', 'stDuration', 'stFirstFrame', 'stRecordTime'
        ].forEach(function (id) {
            setStat(id, '-');
        });
    }

    function refreshPlayState() {
        var playing = !!(player && player.isPlaying && player.isPlaying());
        $('#dotPlay').toggleClass('on', playing);
        $('#playStateText').text(playing ? 'Playing' : (player ? 'Stopped' : 'Not initialised'));
        setStat('stPlaying', playing ? 'Playing' : (player ? 'Idle' : 'Not initialised'));
    }

    function refreshMuteButton() {
        var muted = !!(player && player.isMute && player.isMute());
        // The button has a fixed width sized for the longer label, so the row never reflows
        $('#btnMute').text(muted ? 'Unmute' : 'Mute').attr('title', muted ? 'Unmute' : 'Mute');
    }

    function refreshRecordState(isRecording) {
        recording = !!isRecording;
        $('#dotRecord').toggleClass('rec', recording);
        $('#recordStateText').text(recording ? 'Recording' : 'Not recording');
        $('#btnRecord').text(recording ? 'Stop and save' : 'Start recording')
            .toggleClass('btn-outline-danger', recording)
            .toggleClass('btn-outline-light', !recording);
        if (!recording) setStat('stRecordTime', '-');
    }

    /* ------------------------------------------------------------------ */
    /* Player instance                                                     */
    /* ------------------------------------------------------------------ */
    function bindEvents(jb) {
        jb.on('load', function () {
            log('Player initialised (load)', 'success');
        });

        jb.on('videoInfo', function (data) {
            var codec = data.encType ? '  ' + data.encType : '';
            setStat('stResolution', data.width + ' x ' + data.height + codec);
            log('Video info: ' + data.width + 'x' + data.height + (data.encType ? ', codec ' + data.encType : ''));
        });

        jb.on('audioInfo', function (data) {
            // The field name differs between core versions, so accept either
            var channels = data.channels !== undefined ? data.channels : data.numOfChannels;
            setStat('stAudio', (data.encType ? data.encType + ' / ' : '') + channels + ' ch / ' + data.sampleRate + ' Hz');
            log('Audio info: ' + (data.encType ? data.encType + ', ' : '') + channels + ' channels, sample rate ' + data.sampleRate);
        });

        jb.on('stats', function (s) {
            setStat('stFps', s.fps);
            setStat('stVbps', formatBytes(s.vbps));
            setStat('stAbps', formatBytes(s.abps));
            setStat('stBuf', s.buf);
            setStat('stTs', s.ts);
        });

        jb.on('kBps', function (v) {
            setStat('stKbps', Number(v).toFixed(2) + ' KB/s');
        });

        jb.on('performance', function (v) {
            setStat('stPerformance', ['Stuttering', 'Smooth', 'Very smooth'][v] || v);
        });

        jb.on('timeUpdate', function (ts) {
            setStat('stDuration', formatDuration(ts / 1000));
        });

        jb.on('playToRenderTimes', function (times) {
            setStat('stFirstFrame', times.allTimestamp + ' ms');
            log('First frame rendered in ' + times.allTimestamp + ' ms (network ' + times.streamResponseTimestamp +
                ' ms, demux ' + times.demuxTimestamp + ' ms, decode ' + times.decodeTimestamp + ' ms)');
        });

        jb.on('start', function () {
            log('Rendering started (start)', 'success');
            refreshPlayState();
        });

        jb.on('play', function () {
            refreshPlayState();
            refreshMuteButton();
            log('Playing (play)', 'success');
        });

        jb.on('pause', function () {
            refreshPlayState();
            log('Paused (pause)', 'warn');
        });

        jb.on('mute', function (flag) {
            refreshMuteButton();
            if (!suppressMuteLog) log(flag ? 'Muted' : 'Unmuted');
        });

        jb.on('fullscreen', function (flag) {
            log(flag ? 'Entered fullscreen' : 'Left fullscreen');
        });

        jb.on('recordStart', function () {
            refreshRecordState(true);
            log('Recording started', 'success');
        });

        jb.on('recordEnd', function () {
            refreshRecordState(false);
            log('Recording finished and saved', 'success');
        });

        jb.on('recordingTimestamp', function (ts) {
            setStat('stRecordTime', formatDuration(ts));
        });

        jb.on('timeout', function (err) {
            log('Timeout: ' + err, 'warn');
        });

        jb.on('error', function (err) {
            log('Error: ' + errorText(err), 'error');
            refreshPlayState();
        });

        jb.on('log', function (data) {
            if ($('#optDebug').prop('checked')) {
                log('[core] ' + (typeof data === 'object' ? JSON.stringify(data) : data));
            }
        });
    }

    // The core's destroy() is async; wait for it before rebuilding into the same container
    function createPlayer() {
        return destroyPlayer(true).then(function () {
            player = new window.Jessibuca(buildConfig());
            bindEvents(player);
            applyRuntimeOptions();
            configDirty = false;
            $('#dirtyTip').hide();
            refreshPlayState();
            refreshMuteButton();
            refreshRecordState(false);
            log('Player instance created, decode mode: ' + decodeMode(), 'success');
            return player;
        }).catch(function (e) {
            log('Failed to create the player: ' + (e && e.message ? e.message : e), 'error');
        });
    }

    function applyRuntimeOptions() {
        if (!player) return;
        suppressMuteLog = true;
        player.setScaleMode(parseInt($('#scaleMode').val(), 10));
        var deg = parseInt($('#rotate').val(), 10);
        if (deg) player.setRotate(deg);
        player.setVolume(parseInt($('#volume').val(), 10) / 100);
        setTimeout(function () {
            suppressMuteLog = false;
        }, 0);
    }

    function destroyPlayer(silent) {
        var current = player;
        player = null;
        var pending;
        try {
            pending = current ? Promise.resolve(current.destroy()) : Promise.resolve();
        } catch (e) {
            log('Error while destroying the player: ' + e.message, 'warn');
            pending = Promise.resolve();
        }
        return pending.catch(function (e) {
            log('Error while destroying the player: ' + (e && e.message ? e.message : e), 'warn');
        }).then(function () {
            var $container = $('#container');
            $container.empty().removeAttr('data-jessibuca');
            refreshRecordState(false);
            refreshPlayState();
            if (current && !silent) {
                resetStats();
                log('Player destroyed', 'warn');
            }
        });
    }

    function ensurePlayer() {
        if (!player || configDirty) return createPlayer();
        return Promise.resolve(player);
    }

    /* ------------------------------------------------------------------ */
    /* Interaction                                                         */
    /* ------------------------------------------------------------------ */
    function doPlay() {
        var url = $.trim($('#playUrl').val());
        if (!url) {
            log('Enter a stream URL first', 'error');
            $('#playUrl').focus();
            return;
        }
        if (!/^(wss?|https?):\/\//i.test(url)) {
            log('Unsupported protocol — only ws/wss/http/https are allowed', 'error');
            return;
        }
        ensurePlayer().then(function (jb) {
            if (!jb) return;
            // If a stream is already playing, close it first to avoid stacking streams
            if (jb.isPlaying()) jb.close();
            resetStats();
            log('Starting playback: ' + url);
            return jb.play(url).then(function () {
                pushUrlHistory(url);
                refreshPlayState();
            });
        }).catch(function (e) {
            log('Playback failed: ' + (e && e.message ? e.message : e), 'error');
            refreshPlayState();
        });
    }

    $('#btnPlay').on('click', doPlay);

    $('#playUrl').on('keydown', function (e) {
        if (e.key === 'Enter') doPlay();
    });

    $('#btnPause').on('click', function () {
        if (!player) return;
        player.pause().then(function () {
            refreshPlayState();
        }).catch(function (e) {
            log('Failed to pause: ' + e, 'error');
        });
    });

    $('#btnClose').on('click', function () {
        if (!player) return;
        player.close();
        resetStats();
        refreshPlayState();
        log('Playback stopped (close)', 'warn');
    });

    $('#btnDestroy').on('click', function () {
        destroyPlayer(false);
    });

    $('#btnApply').on('click', function () {
        createPlayer();
    });

    $('#btnMute').on('click', function () {
        if (!player) return;
        if (player.isMute()) {
            player.cancelMute();
            player.audioResume();
            if (parseInt($('#volume').val(), 10) === 0) {
                $('#volume').val(100).trigger('input');
            }
        } else {
            player.mute();
        }
        refreshMuteButton();
    });

    $('#volume').on('input', function () {
        var v = parseInt(this.value, 10);
        $('#volumeText').text(v);
        if (player) {
            player.setVolume(v / 100);
            refreshMuteButton();
        }
    });

    $('#btnScreenshot').on('click', function () {
        if (!player) {
            log('Player is not initialised', 'error');
            return;
        }
        // The current core dist has a broken download branch, so grab base64 and download it ourselves
        var name = 'jessibuca-' + Date.now();
        try {
            var dataUrl = player.screenshot(name, 'png', 0.92, 'base64');
            if (!dataUrl) {
                log('Snapshot failed: no frame available', 'error');
                return;
            }
            var a = document.createElement('a');
            a.href = dataUrl;
            a.download = name + '.png';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            log('Snapshot saved as ' + name + '.png', 'success');
        } catch (e) {
            log('Snapshot failed: ' + (e && e.message ? e.message : e), 'error');
        }
    });

    $('#btnRecord').on('click', function () {
        if (!player) {
            log('Player is not initialised', 'error');
            return;
        }
        if (recording || player.isRecording()) {
            player.stopRecordAndSave();
        } else {
            player.startRecord('jessibuca-' + Date.now(), $('#recordType').val());
        }
    });

    $('#btnFullscreen').on('click', function () {
        if (player) player.setFullscreen(true);
    });

    $('#btnClearView').on('click', function () {
        if (player) {
            player.clearView();
            log('Canvas cleared');
        }
    });

    $('#btnToggleControl').on('click', function () {
        if (player) player.toggleControlBar();
    });

    $('#btnResize').on('click', function () {
        if (player) player.resize();
    });

    $('#scaleMode').on('change', function () {
        if (player) player.setScaleMode(parseInt(this.value, 10));
        saveConfig();
    });

    $('#rotate').on('change', function () {
        if (player) player.setRotate(parseInt(this.value, 10));
        saveConfig();
    });

    $('#optDebug').on('change', function () {
        if (player) player.setDebug($(this).prop('checked'));
    });

    // Decoders are mutually exclusive: checking one clears the rest, clearing all falls back to wasm
    $('.jb-decoder').on('change', function () {
        if (this.checked) {
            $('.jb-decoder').not(this).prop('checked', false);
        } else if (!$('.jb-decoder:checked').length) {
            $('#modeWasm').prop('checked', true);
        }
    });

    // Changing an init-time option requires rebuilding the instance
    $('.jb-init-opt').on('change', function () {
        saveConfig();
        if (player) {
            configDirty = true;
            $('#dirtyTip').show();
        }
    });

    $('#btnClearLog').on('click', function () {
        $log.empty();
    });

    $(window).on('resize', function () {
        if (player) player.resize();
    });

    $(window).on('beforeunload', function () {
        destroyPlayer(true);
    });

    /* ------------------------------------------------------------------ */
    /* Bootstrap                                                           */
    /* ------------------------------------------------------------------ */
    function detectSupport() {
        var mse = typeof window.MediaSource !== 'undefined' &&
            typeof window.MediaSource.isTypeSupported === 'function';
        var wcs = typeof window.VideoDecoder !== 'undefined';
        var wasm = typeof window.WebAssembly === 'object';
        $('#supMse').toggleClass('jb-badge-off', !mse).toggleClass('text-bg-success', mse);
        $('#supWcs').toggleClass('jb-badge-off', !wcs).toggleClass('text-bg-success', wcs);
        $('#supWasm').toggleClass('jb-badge-off', !wasm).toggleClass('text-bg-success', wasm);
        if (!mse) $('#modeMse').prop('disabled', true).prop('checked', false);
        if (!wcs) $('#modeWcs').prop('disabled', true).prop('checked', false);
        if (!$('.jb-decoder:checked').length) $('#modeWasm').prop('checked', true);
    }

    $(function () {
        if (typeof window.Jessibuca !== 'function') {
            log('Failed to load the jessibuca core — check player/jessibuca/jessibuca.js', 'error');
            return;
        }
        $('#coreVersion').text('v3');
        restoreConfig();
        detectSupport();
        renderUrlHistory();
        var history = urlHistory();
        if (history.length) $('#playUrl').val(history[0]);
        $('#volumeText').text($('#volume').val());
        resetStats();
        createPlayer();
        log('Ready — enter a URL and click Play', 'success');
    });

})(jQuery);
