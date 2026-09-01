/**
 * Jessibuca 本地化 Demo Player
 * 依赖：jQuery + Bootstrap 5 + jessibuca(v3) 内核
 * 所有资源均为本地相对路径引用。
 */
(function ($) {
    'use strict';

    var DECODER_PATH = 'player/jessibuca/decoder.js';
    var STORAGE_URL_KEY = 'jb_local_url_history';
    var STORAGE_CFG_KEY = 'jb_local_config';
    var MAX_LOG = 500;

    var player = null;      // Jessibuca 实例
    var configDirty = false; // 初始化类配置被修改，需要重建实例
    var recording = false;
    var suppressMuteLog = false; // 初始化阶段的音量设置不写日志

    /* ------------------------------------------------------------------ */
    /* 日志                                                                */
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
    /* 工具                                                                */
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
            playError: '播放失败：url 为空',
            fetchError: 'http 请求失败',
            websocketError: 'websocket 请求失败',
            webcodecsH265NotSupport: 'webcodecs 不支持 H265',
            mediaSourceH265NotSupport: 'MediaSource 不支持 H265',
            wasmDecodeError: 'wasm 解码失败'
        };
        return map[err] || String(err);
    }

    /* ------------------------------------------------------------------ */
    /* 配置                                                                */
    /* ------------------------------------------------------------------ */
    // 解码器用复选框呈现，但逻辑上互斥（与官方 demo 一致）
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
            loadingText: '加载中...',
            heartTimeoutReplay: timeoutReplay,
            loadingTimeoutReplay: timeoutReplay,
            wasmDecodeErrorReplay: timeoutReplay,
            useMSE: mode === 'mse',
            useWCS: mode === 'wcs',
            // MediaSource 硬解码不支持离屏渲染
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
        } catch (e) { /* 忽略隐私模式下的异常 */ }
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
    /* URL 历史                                                            */
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
    /* 状态面板                                                            */
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
        $('#playStateText').text(playing ? '播放中' : (player ? '已停止' : '未初始化'));
        setStat('stPlaying', playing ? '播放中' : (player ? '空闲' : '未初始化'));
    }

    function refreshMuteButton() {
        var muted = !!(player && player.isMute && player.isMute());
        // 按钮宽度固定，两种状态都用两个字，避免文案被裁切或整行抖动
        $('#btnMute').text(muted ? '取消' : '静音').attr('title', muted ? '取消静音' : '静音');
    }

    function refreshRecordState(isRecording) {
        recording = !!isRecording;
        $('#dotRecord').toggleClass('rec', recording);
        $('#recordStateText').text(recording ? '录制中' : '未录制');
        $('#btnRecord').text(recording ? '停止并保存' : '开始录制')
            .toggleClass('btn-outline-danger', recording)
            .toggleClass('btn-outline-light', !recording);
        if (!recording) setStat('stRecordTime', '-');
    }

    /* ------------------------------------------------------------------ */
    /* 播放器实例                                                          */
    /* ------------------------------------------------------------------ */
    function bindEvents(jb) {
        jb.on('load', function () {
            log('播放器初始化完成(load)', 'success');
        });

        jb.on('videoInfo', function (data) {
            var codec = data.encType ? '  ' + data.encType : '';
            setStat('stResolution', data.width + ' x ' + data.height + codec);
            log('视频信息：' + data.width + 'x' + data.height + (data.encType ? '，编码 ' + data.encType : ''));
        });

        jb.on('audioInfo', function (data) {
            // 不同版本内核字段名不同，做一次兼容
            var channels = data.channels !== undefined ? data.channels : data.numOfChannels;
            setStat('stAudio', (data.encType ? data.encType + ' / ' : '') + channels + ' 声道 / ' + data.sampleRate + ' Hz');
            log('音频信息：' + (data.encType ? data.encType + '，' : '') + channels + ' 声道，采样率 ' + data.sampleRate);
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
            setStat('stPerformance', ['卡顿', '流畅', '非常流畅'][v] || v);
        });

        jb.on('timeUpdate', function (ts) {
            setStat('stDuration', formatDuration(ts / 1000));
        });

        jb.on('playToRenderTimes', function (times) {
            setStat('stFirstFrame', times.allTimestamp + ' ms');
            log('首帧渲染耗时 ' + times.allTimestamp + ' ms（网络 ' + times.streamResponseTimestamp +
                ' ms，解封装 ' + times.demuxTimestamp + ' ms，解码 ' + times.decodeTimestamp + ' ms）');
        });

        jb.on('start', function () {
            log('开始渲染(start)', 'success');
            refreshPlayState();
        });

        jb.on('play', function () {
            refreshPlayState();
            refreshMuteButton();
            log('播放中(play)', 'success');
        });

        jb.on('pause', function () {
            refreshPlayState();
            log('已暂停(pause)', 'warn');
        });

        jb.on('mute', function (flag) {
            refreshMuteButton();
            if (!suppressMuteLog) log(flag ? '已静音' : '已取消静音');
        });

        jb.on('fullscreen', function (flag) {
            log(flag ? '进入全屏' : '退出全屏');
        });

        jb.on('recordStart', function () {
            refreshRecordState(true);
            log('开始录制', 'success');
        });

        jb.on('recordEnd', function () {
            refreshRecordState(false);
            log('录制结束并保存', 'success');
        });

        jb.on('recordingTimestamp', function (ts) {
            setStat('stRecordTime', formatDuration(ts));
        });

        jb.on('timeout', function (err) {
            log('超时：' + err, 'warn');
        });

        jb.on('error', function (err) {
            log('错误：' + errorText(err), 'error');
            refreshPlayState();
        });

        jb.on('log', function (data) {
            if ($('#optDebug').prop('checked')) {
                log('[core] ' + (typeof data === 'object' ? JSON.stringify(data) : data));
            }
        });
    }

    // 内核的 destroy() 是异步的，必须等它执行完才能在同一个容器上重建实例
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
            log('创建播放器实例，解码模式：' + decodeMode(), 'success');
            return player;
        }).catch(function (e) {
            log('创建播放器失败：' + (e && e.message ? e.message : e), 'error');
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
            log('销毁播放器异常：' + e.message, 'warn');
            pending = Promise.resolve();
        }
        return pending.catch(function (e) {
            log('销毁播放器异常：' + (e && e.message ? e.message : e), 'warn');
        }).then(function () {
            var $container = $('#container');
            $container.empty().removeAttr('data-jessibuca');
            refreshRecordState(false);
            refreshPlayState();
            if (current && !silent) {
                resetStats();
                log('播放器已销毁', 'warn');
            }
        });
    }

    function ensurePlayer() {
        if (!player || configDirty) return createPlayer();
        return Promise.resolve(player);
    }

    /* ------------------------------------------------------------------ */
    /* 交互                                                                */
    /* ------------------------------------------------------------------ */
    function doPlay() {
        var url = $.trim($('#playUrl').val());
        if (!url) {
            log('请先输入播放地址', 'error');
            $('#playUrl').focus();
            return;
        }
        if (!/^(wss?|https?):\/\//i.test(url)) {
            log('地址协议不正确，仅支持 ws/wss/http/https', 'error');
            return;
        }
        ensurePlayer().then(function (jb) {
            if (!jb) return;
            // 若正在播放，先关闭上一路流，避免重复播放
            if (jb.isPlaying()) jb.close();
            resetStats();
            log('开始播放：' + url);
            return jb.play(url).then(function () {
                pushUrlHistory(url);
                refreshPlayState();
            });
        }).catch(function (e) {
            log('播放失败：' + (e && e.message ? e.message : e), 'error');
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
            log('暂停失败：' + e, 'error');
        });
    });

    $('#btnClose').on('click', function () {
        if (!player) return;
        player.close();
        resetStats();
        refreshPlayState();
        log('已停止播放(close)', 'warn');
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
            log('播放器未初始化', 'error');
            return;
        }
        // 当前内核 dist 的 download 分支存在缺陷，这里取 base64 后自行触发下载
        var name = 'jessibuca-' + Date.now();
        try {
            var dataUrl = player.screenshot(name, 'png', 0.92, 'base64');
            if (!dataUrl) {
                log('截图失败：没有可用的画面', 'error');
                return;
            }
            var a = document.createElement('a');
            a.href = dataUrl;
            a.download = name + '.png';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            log('已截图并下载 ' + name + '.png', 'success');
        } catch (e) {
            log('截图失败：' + (e && e.message ? e.message : e), 'error');
        }
    });

    $('#btnRecord').on('click', function () {
        if (!player) {
            log('播放器未初始化', 'error');
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
            log('画布已清空');
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

    // 解码器互斥：选中一个则取消其它，全部取消时回落到 wasm
    $('.jb-decoder').on('change', function () {
        if (this.checked) {
            $('.jb-decoder').not(this).prop('checked', false);
        } else if (!$('.jb-decoder:checked').length) {
            $('#modeWasm').prop('checked', true);
        }
    });

    // 初始化类配置变更后需要重建实例
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
    /* 启动                                                                */
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
            log('jessibuca 内核加载失败，请检查 player/jessibuca/jessibuca.js', 'error');
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
        log('页面就绪，输入地址后点击「播放」', 'success');
    });

})(jQuery);
