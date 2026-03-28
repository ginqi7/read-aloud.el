import mlx.core as mx
from parakeet_mlx import from_pretrained
from transcriber import Transcriber


class ParakeetMlxTranscriber(Transcriber):
    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self.model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")
        self.sample_rate = self.model.preprocessor_config.sample_rate
        self.client = self.model.transcribe_stream(context_size=(256, 256))
        self.last_text = ""
        self.count = 0

    def send_audio(self, audio_chunk: bytes) -> str:
        audio_mlx = mx.array(audio_chunk.flatten())
        self.client.add_audio(audio_mlx)
        result = self.client.result
        if result.text != self.last_text:
            self.count += 1
            print(f"\rTranscription: {result.text}\n", end="", flush=True)
            self.last_text = result.text
            if self.count == 3:
                self.count = 0
                return self.last_text

    def handle_transcription(self) -> str:
        result = self.client.result
        if result.text.strip():
            print(result.text)
            self.reset_session()
            return result.text

    def reset_session(self) -> None:
        """清除上一段识别上下文与结果"""
        self.client = self.model.transcribe_stream(context_size=(256, 256))
        self.last_text = ""
