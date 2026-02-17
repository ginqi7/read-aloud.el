from vosk import Model, KaldiRecognizer
from transcriber import Transcriber
import numpy as np
import json


class VoskTranscriber(Transcriber):
    def __init__(self, sample_rate: int, vosk_model_directory: str):
        super().__init__(sample_rate)
        model = Model(vosk_model_directory)
        self.client = KaldiRecognizer(model, sample_rate)

    def send_audio(self, audio_chunk: bytes) -> None:
        audio_data = np.concatenate(audio_chunk)
        audio_int16 = (audio_data * 32767).astype(np.int16)
        self.client.AcceptWaveform(audio_int16.tobytes())
        print(self.client.PartialResult())

    def handle_transcription(self) -> str:
        result = json.loads(self.client.Result())
        text = result.get("text", "").strip()
        if text:
            return text
        else:
            partial = json.loads(self.client.PartialResult()).get("partial", "").strip()
            if partial:
                return text
