# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`read-aloud.el` is an Emacs package that provides live speech-to-text transcription. It captures microphone audio, detects voice activity (start/stop based on silence), and sends transcribed text to Emacs for fuzzy search integration.

## Architecture

### Elisp Frontend (`read-aloud.el`)

- Communicates with the Python backend via `websocket-bridge`
- Key commands:
  - `read-alound-start` - Start the Python backend
  - `read-alound-stop` - Stop the backend
  - `read-alound-restart` - Restart and open log buffer
  - `read-alound-toggle` - Toggle recording state
- Configuration variables:
  - `read-alound-transcription-backend` - Backend choice: "parakeet-mlx", "deepgram", "vosk", "paraformer"
  - `read-alound-deepgram-api-key` - API key for Deepgram
  - `read-alound-paraformer-api-key` - API key for Paraformer (Alibaba)
  - `read-alound-vosk-model-directory` - Path to Vosk model directory
  - `read-alound-notify-command` - Optional shell command for notifications

### Python Backend (`read-alound.py`)

- Uses `sounddevice` for audio capture with callback-based streaming
- Voice activity detection: starts recording on energy > threshold, stops after 0.5s of silence
- Dynamically loads transcription backend based on Emacs config

### Transcription Backends

All backends implement the `Transcriber` abstract base class:

| Backend | File | Description |
|---------|------|-------------|
| `parakeet-mlx` | `transcriber_parakeet_mlx.py` | Local Apple Silicon (MLX) using Parakeet TDT model |
| `deepgram` | `transcriber_deepgram.py` | Cloud-based Deepgram API |
| `vosk` | `transcriber_vosk.py` | Local offline using Vosk/Kaldi |
| `paraformer` | `transcriber_paraformer.py` | Alibaba Paraformer real-time API |

## Commands

```bash
# Run tests (installs Elisp dependencies first)
make test

# Install Elisp dependencies manually
sh dependencies.sh
```

## Dependencies

### Elisp
Defined in `dependencies.txt` - cloned to `~/.emacs.d/lisp/`:
- `websocket` - WebSocket client
- `websocket-bridge` - Emacs-Python IPC
- `fuzzy-search` - Fuzzy search integration

### Python
Managed via `pyproject.toml`. Key dependencies:
- `parakeet-mlx` - Streaming ASR for Apple Silicon
- `sounddevice` - Audio I/O
- `websocket-bridge-python` - Python side of IPC bridge
- `sexpdata` - S-expression serialization

Python 3.13+ required.

## Notes

- The `.venv/` directory contains the Python virtual environment (not committed)
- Default backend is `parakeet-mlx` (Apple Silicon only)
- For other backends, set `read-alound-transcription-backend` and configure API keys/model paths
