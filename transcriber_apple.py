import ctypes

import Speech
import AVFoundation
from Foundation import NSLocale, NSDate, NSRunLoop

from transcriber import Transcriber


class AppleTranscriber(Transcriber):
    def __init__(self, sample_rate: int, locale_str: str = "en-US"):
        super().__init__(sample_rate)

        self.sample_rate = sample_rate
        self.locale = NSLocale.alloc().initWithLocaleIdentifier_(locale_str)
        self.recognizer = Speech.SFSpeechRecognizer.alloc().initWithLocale_(self.locale)
        if self.recognizer is None:
            raise RuntimeError("failed to create SFSpeechRecognizer")

        self._authorize()

        self.last_text = ""
        self.final_text = ""
        self.count = 0
        self.done = False

        self.audio_format = AVFoundation.AVAudioFormat.alloc().initWithCommonFormat_sampleRate_channels_interleaved_(
            AVFoundation.AVAudioPCMFormatFloat32,
            float(self.sample_rate),
            1,
            False,
        )

        self.reset_session()

    def _authorize(self):
        authorized = {"done": False, "ok": False}

        def auth_handler(status):
            # SFSpeechRecognizerAuthorizationStatusAuthorized == 3
            authorized["ok"] = status == 3
            authorized["done"] = True

        Speech.SFSpeechRecognizer.requestAuthorization_(auth_handler)

        while not authorized["done"]:
            NSRunLoop.currentRunLoop().runUntilDate_(
                NSDate.dateWithTimeIntervalSinceNow_(0.05)
            )

        if not authorized["ok"]:
            raise RuntimeError("speech recognition not authorized")

    def _create_request(self):
        request = Speech.SFSpeechAudioBufferRecognitionRequest.alloc().init()
        request.setShouldReportPartialResults_(True)
        return request

    def _create_task(self):
        def result_handler(result, error):
            if error is not None:
                print("error:", error)
                self.done = True
                return

            if result is not None:
                text = result.bestTranscription().formattedString()
                self.last_text = text
                if result.isFinal():
                    self.final_text = text
                    self.done = True

        return self.recognizer.recognitionTaskWithRequest_resultHandler_(
            self.recognition_request,
            result_handler,
        )

    def _float32_chunk_to_pcm_buffer(self, audio_chunk):
        import numpy as np
        flat_chunk = audio_chunk.flatten().astype("float32", copy=False)
        frame_count = len(flat_chunk)

        pcm_buffer = (
            AVFoundation.AVAudioPCMBuffer.alloc().initWithPCMFormat_frameCapacity_(
                self.audio_format,
                frame_count,
            )
        )
        pcm_buffer.setFrameLength_(frame_count)

        # floatChannelData() returns a tuple of (float*,) — channel_ptr[0] is the
        # objc.varlist for channel 0. Use as_buffer() to get a memoryview we can
        # view as a NumPy float32 array, then copy audio data into it.
        channel_ptr = pcm_buffer.floatChannelData()
        dst = np.frombuffer(channel_ptr[0].as_buffer(frame_count), dtype=np.float32)
        np.copyto(dst, flat_chunk)
        return pcm_buffer

    def send_audio(self, audio_chunk) -> str:
        pcm_buffer = self._float32_chunk_to_pcm_buffer(audio_chunk)
        self.recognition_request.appendAudioPCMBuffer_(pcm_buffer)

        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.01)
        )

        if self.last_text and self.last_text != self._previous_emitted_text:
            self.count += 1
            print(f"\rTranscription: {self.last_text}\n", end="", flush=True)
            self._previous_emitted_text = self.last_text
            if self.count == 3:
                self.count = 0
                return self.last_text

    def handle_transcription(self) -> str:
        self.recognition_request.endAudio()

        while not self.done:
            NSRunLoop.currentRunLoop().runUntilDate_(
                NSDate.dateWithTimeIntervalSinceNow_(0.05)
            )

        text = self.final_text.strip() or self.last_text.strip()
        if text:
            print(text)
            self.reset_session()
            return text

        self.reset_session()
        return ""

    def reset_session(self) -> None:
        if hasattr(self, "task") and self.task is not None:
            self.task.cancel()

        self.recognition_request = self._create_request()
        self.task = self._create_task()

        self.last_text = ""
        self.final_text = ""
        self.done = False
        self.count = 0
        self._previous_emitted_text = ""
