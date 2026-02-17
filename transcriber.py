from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Transcriber(ABC):
    """Base transcriber interface."""

    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate

    @abstractmethod
    def send_audio(self, audio_chunk) -> None:
        """Receive one chunk of audio data."""
        raise NotImplementedError

    @abstractmethod
    def handle_transcription(self) -> Any:
        """Process queued audio and return transcription result."""
        raise NotImplementedError
