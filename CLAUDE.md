# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`read-aloud.el` is an Emacs package providing live speech-to-text transcription with automatic voice activity detection. It captures microphone audio, detects speech/silence boundaries, and sends transcribed text to Emacs for fuzzy search integration.

## Architecture

### Component Overview

```
┌─────────────────┐     WebSocket     ┌─────────────────┐
│  read-aloud.el  │ ◄──────────────► │ read-alound.py  │
│   (Elisp)       │                   │    (Python)     │
└─────────────────┘                   └────────┬────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │  Transcriber (ABC)  │
                                    └──────────┬──────────┘
         ┌─────────────┬─────────────┬─────────┴────────┬──────────────┐
         ▼             ▼             ▼                  ▼              ▼
┌────────────────┐ ┌──────────┐ ┌───────────┐ ┌────────────────┐ ┌───────────┐
│ parakeet-mlx   │ │ deepgram │ │  vosk     │ │  aliyun        │ │ (future)  │
│ (Apple Silicon)│ │ (Cloud)  │ │ (Offline) │ │ (Paraformer)   │ │           │
└────────────────┘ └──────────┘ └───────────┘ └────────────────┘ └───────────┘
```

### Elisp Frontend (`read-aloud.el`)

- Communicates with Python backend via `websocket-bridge`
- Key commands: `read-alound-start`, `read-alound-stop`, `read-alound-restart`, `read-alound-toggle`
- Configuration variables:
  - `read-alound-transcription-backend` - One of: `"parakeet-mlx"`, `"deepgram"`, `"vosk"`, `"aliyun"`
  - `read-alound-deepgram-api-key` - Deepgram API key
  - `read-alound-aliyun-api-key` - Alibaba Paraformer API key
  - `read-alound-aliyun-model` - Model identifier for Paraformer
  - `read-alound-vosk-model-directory` - Path to Vosk model directory
  - `read-alound-notify-command` - Optional shell command for notifications

### Python Backend (`read-alound.py`)

- Audio capture via `sounddevice` with callback-based streaming
- Voice Activity Detection (VAD):
  - Starts recording when energy > `SILENCE_THRESH` (1e-7)
  - Stops after `SILENCE_DURATION` (0.5s) of continuous silence
  - Audio chunks: 1.0 second at 16kHz sample rate
- Dynamically loads transcription backend based on Emacs config

### Transcriber Interface

All backends implement `transcriber.Transcriber` abstract base class:

| Backend | File | Platform | Notes |
|---------|------|----------|-------|
| `parakeet-mlx` | `transcriber_parakeet_mlx.py` | Apple Silicon | Default; uses MLX streaming ASR |
| `deepgram` | `transcriber_deepgram.py` | Cross-platform | Cloud API; uses `nova-3` model |
| `vosk` | `transcriber_vosk.py` | Cross-platform | Offline; requires model directory |
| `aliyun` | `transcriber_aliyun.py` | Cross-platform | Alibaba Paraformer; needs API key |

## Commands

```bash
# Install Elisp dependencies and run tests
make test

# Install Elisp dependencies only
make solve-dependencies

# Python: install with pip
pip install -e .

# Python: install with uv
uv sync
```

## Dependencies

### Elisp (`dependencies.txt`)
- `websocket` - WebSocket client
- `websocket-bridge` - Emacs-Python IPC
- `fuzzy-search` - Fuzzy search integration

Installed to `~/.emacs.d/lisp/` via `dependencies.sh`

### Python (`pyproject.toml`)
- `parakeet-mlx>=0.5.0` - Apple Silicon streaming ASR
- `sounddevice>=0.5.5` - Audio I/O
- `websocket-bridge-python>=0.0.2` - Python IPC bridge
- `sexpdata>=1.0.2` - S-expression serialization

Python 3.13+ required.

## Notes

- `.venv/` contains local virtual environment (not committed)
- Default backend `parakeet-mlx` requires Apple Silicon Mac
- For cloud/offline backends, configure `read-alound-transcription-backend` and set API keys/model paths
- Backend name in config: use `"aliyun"` (not `"paraformer"`) for Alibaba Paraformer
