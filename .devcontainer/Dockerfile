FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    build-essential cmake curl git \
    libsox-fmt-mp3 sox ffmpeg \
    ca-certificates software-properties-common \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Optional: make python the default
RUN ln -sf /usr/bin/python3 /usr/bin/python

RUN pip install assemblyai dotenv mutagen openai moviepy fuzzywuzzy

