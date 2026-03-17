from transcriber import Transcriber
from queue import Queue
import numpy as np
import dashscope
from dashscope.audio.asr import *


aliyun_last_text = ""


# Real-time speech recognition callback
class Callback(RecognitionCallback):
    def on_open(self) -> None:
        print("RecognitionCallback open.")

    def on_close(self) -> None:
        print("RecognitionCallback close.")

    def on_complete(self) -> None:
        print("RecognitionCallback completed.")  # recognition completed

    def on_error(self, message) -> None:
        print("RecognitionCallback task_id: ", message.request_id)
        print("RecognitionCallback error: ", message.message)

    def on_event(self, result: RecognitionResult) -> None:
        global aliyun_last_text
        sentence = result.get_sentence()
        if "text" in sentence:
            print("RecognitionCallback text: ", sentence["text"])
            if RecognitionResult.is_sentence_end(sentence):
                aliyun_last_text += sentence["text"]
                print(
                    "RecognitionCallback sentence end, request_id:%s, usage:%s"
                    % (result.get_request_id(), result.get_usage(sentence))
                )


class AliyunTranscriber(Transcriber):
    def __init__(self, sample_rate: int, api_key: str, aliyun_model: str):
        super().__init__(sample_rate)
        dashscope.api_key = api_key
        self._audio_queue: Queue = Queue()
        callback = Callback()
        self.recognition = Recognition(
            model=aliyun_model,
            format="pcm",
            # 'pcm'、'wav'、'opus'、'speex'、'aac'、'amr', you can check the supported formats in the document
            sample_rate=sample_rate,
            # support 8000, 16000
            semantic_punctuation_enabled=False,
            callback=callback,
        )
        # Start recognition
        print("AliyunTranscriber Inited")

    def send_audio(self, audio_chunk) -> None:
        global aliyun_last_text
        if not getattr(self.recognition, "_running"):
            aliyun_last_text = ""
            self.recognition.start()
        audio_int16 = (audio_chunk * 32767).astype(np.int16)
        self.recognition.send_audio_frame(audio_int16)

    def handle_transcription(self) -> str:
        self.recognition.stop()
        print(aliyun_last_text)
        return aliyun_last_text
