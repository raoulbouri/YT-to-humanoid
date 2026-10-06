#!/usr/bin/env bash
# usage: make_gif.sh <in.mp4> <out.gif> [width=640] [fps=8] [colors=64]
# Palette-optimised GIF. The defaults give ~15 MB for the 40 s, 4-panel grid; the scene is gradient-heavy, so GIFs get big fast.
set -e
IN=$1; OUT=$2; W=${3:-640}; FPS=${4:-8}; COLORS=${5:-64}
PAL="$(mktemp -t pal).png"
ffmpeg -v error -y -i "$IN" -vf "fps=$FPS,scale=$W:-1:flags=lanczos,palettegen=max_colors=$COLORS:stats_mode=diff" "$PAL"
ffmpeg -v error -y -i "$IN" -i "$PAL" -lavfi "fps=$FPS,scale=$W:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle" -loop 0 "$OUT"
rm -f "$PAL"; ls -lh "$OUT" | awk '{print $5, $9}'
