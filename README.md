# Podinator
Ever wished to share a specific podcast moment but struggled to find it? Say goodbye to
endless searching! With Podinator, simply upload your audio/video file
(.mp4/.mp3/.wav) or share a link. The tool transcribes the content, generates a search
index, and allows you to type in a description of the clip you're looking for- saving you
time and ensuring you never miss that favorite podcast moment again!

## Work In Progress
Please note: This repository is currently a work in progress. The descriptions and
features listed here are goals, but not currently implemented.

## Features
- Automatic download of podcasts from URL
- Transcribes audio with timestamps, powered by
[OpenAI's Whisper](https://github.com/openai/whisper)
- Transcription accelerated by Georgi Gerganov's
[whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- Automatic indexing of transcripts for optimized search
- Simple/easy web interface for uploading new episodes

## Install
Clone this repository:
```bash
git clone https://github.com/BenRichey2/podinator.git
```
Install the requirements
```bash
cd podinator && \
python3 -m venv venv && \
source venv/bin/activate && \
python3 -m pip install -r requirements.txt
```
You'll also need to install a library called [`ffmpeg`](https://www.ffmpeg.org/) to
facilitate conversion from `.mp3` to `.wav`, which is needed for `whisper.cpp` to work.
Your best bet is to search online the best way to install `ffmpeg` for your OS.

NOTE: The above commands work for MacOS/Linux. You also must have Python installed on
your host. This was written with Python3.11 on an M2 macbook, so YMMV for any other
versions and OS's.

## Usage
TODO

## Contribute
TODO

## Support
TODO

## [License](./LICENSE)

