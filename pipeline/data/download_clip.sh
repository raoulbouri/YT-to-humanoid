#!/usr/bin/env bash
# usage: download_clip.sh <youtube-url> <name>
# Downloads the video (<=1080p, mp4) to $SONIC_WORK/data/raw/<name>.mp4 with yt-dlp. Check the video's licence before reuse.
set -e
. "$(dirname "$0")/../../lib/config.sh"
URL=$1; NAME=$2
mkdir -p "$B/data/raw"; cd "$B/data/raw"
yt-dlp -f 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]' --merge-output-format mp4 --write-info-json -o "$NAME.%(ext)s" "$URL"
