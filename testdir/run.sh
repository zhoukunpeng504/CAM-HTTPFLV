ffmpeg \
-fflags nobuffer \
-flags  low_delay \
-f gdigrab \
-s 1280x720  -r 30  \
-pix_fmt yuv420p \
-offset_x 0 -offset_y 0 -i desktop \
-c:v libx264 \
-x264opts keyint=25:minkeyint=25:scenecut=-1 \
-tune zerolatency \
-profile:v baseline \
-preset veryfast -bf 0 -refs 3 \
-b:v 500k -bufsize 500k \
-utc_timing_url "https://time.akamai.com/?iso" \
-use_timeline 0 \
-format_options "movflags=cmaf" \
-frag_type duration \
-adaptation_sets "id=0, seg_duration=1, frag_duration=0.1, streams=v" \
-streaming 1 \
-ldash 1 \
-export_side_data prft \
-write_prft 1 \
-target_latency 0.5 \
-window_size 5 \
-extra_window_size 10 \
-remove_at_exit 1 \
-method PUT \
-f dash \
http://192.168.1.166:8000/hik1/manifest.mpd