# Lamp Character Simulation

Here is how to get this running on a fresh Ubuntu 24.04 setup (it was built and tested in a VM!).

## Prerequisites

You'll need a few system packages first, mostly so the audio libraries (like PyAudio) compile correctly on Linux. Run this:
```bash
sudo apt update
sudo apt install python3-pip portaudio19-dev python3-dev espeak-ng ffmpeg
```

## Install Python Dependencies

Next, install the requirements. I locked the OpenCV version under 5.0 just to avoid some weird missing CascadeClassifier bugs I ran into on the bleeding-edge version.
```bash
pip3 install -r requirements.txt
```

## Download the Local Models

We are running everything completely offline to fit the constraints, so no paid API keys are needed!

1. **Audio Model**: Download a small English Vosk model (like `vosk-model-small-en-us`), extract it, and rename the folder to exactly `model` right here in the root directory.
2. **LLM/VLM**: Install Ollama (`curl -fsSL https://ollama.com/install.sh | sh`) and pull the tiny models:
```bash
ollama pull moondream
ollama pull qwen2:0.5b
```

## Running the Robot

Make sure Ollama is running in the background, then just start the main script:
```bash
python3 main.py
```

*Note: If you're running this in VMware and your webcam refuses to connect, don't worry! The script has a built-in fallback that will bypass the camera errors and still let you talk to the robot using your microphone.*
