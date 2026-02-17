from deepgram import DeepgramClient
from transcriber import Transcriber
from queue import Queue
import numpy as np
import io
import wave


class DeepgramTranscriber(Transcriber):
    def __init__(self, sample_rate: int, api_key: str):
        super().__init__(sample_rate)
        self.api_key = api_key
        self.client = DeepgramClient(api_key=api_key)
        self._audio_queue: Queue = Queue()
        print("DeepgramTranscriber Inited")

    def send_audio(self, audio_chunk) -> None:
        self._audio_queue.put(audio_chunk)

    def handle_transcription(self) -> str:
        chunks = []
        while not self._audio_queue.empty():
            chunks.append(self._audio_queue.get_nowait())
        if not chunks:
            return
        # Concatenate and convert to int16 (WAV standard format)
        audio_data = np.concatenate(chunks)
        audio_int16 = (audio_data * 32767).astype(np.int16)
        # Write to memory in WAV format.
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        response = self.client.listen.v1.media.transcribe_file(
            request=buf.getvalue(), model="nova-3"
        )
        text = response.results.channels[0].alternatives[0].transcript
        print(text)
        return text
