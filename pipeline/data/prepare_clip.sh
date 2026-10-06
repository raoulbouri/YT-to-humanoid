#!/usr/bin/env bash
# usage: prepare_clip.sh <raw video> <name> <start_s> <duration_s> <fps>
# Cuts a segment, drops audio, resamples to a constant frame rate (GEM-X breaks on variable-frame-rate files)
# and writes $SONIC_WORK/data/clips/<name>.mp4 plus <name>_source.txt.
set -e
. "$(dirname "$0")/../../lib/config.sh"
SRC=$1; NAME=$2; START=$3; DUR=$4; FPS=$5
mkdir -p "$B/data/clips"
ffmpeg -v error -y -ss "$START" -t "$DUR" -i "$SRC" -an -vf "fps=$FPS" -c:v libx264 -crf 14 -pix_fmt yuv420p "$B/data/clips/$NAME.mp4"
printf 'source: %s\nsegment: %s s + %s s\nprep: no audio, constant %s fps, H.264 crf14\n' "$SRC" "$START" "$DUR" "$FPS" > "$B/data/clips/${NAME}_source.txt"
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames,width,height,r_frame_rate -of csv=p=0 "$B/data/clips/$NAME.mp4"
