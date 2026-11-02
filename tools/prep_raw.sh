#!/bin/sh
# usage: sh tools/prep_raw.sh   (raw/rahul.mp4 is the clip Story99 supplied; it is not in this repo)
# Pulls the two audio tracks the cut and the transcription read from the raw clip.
set -e
mkdir -p build
ffmpeg -v error -y -i raw/rahul.mp4 -map 0:a:0 -c:a pcm_s24le build/raw48k.wav
ffmpeg -v error -y -i raw/rahul.mp4 -map 0:a:0 -ac 1 -ar 16000 build/raw16k.wav
