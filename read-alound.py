#!/usr/bin/env python3
import threading
import io
import wave
import numpy as np
import asyncio
import json
import sexpdata
import websocket_bridge_python

import queue
import sys
import time
import sounddevice as sd


MODEL_NAME = "mlx-community/parakeet-tdt-0.6b-v3"
CHUNK_DURATION = 1.0
SILENCE_DURATION = 0.5
SILENCE_THRESH = 1e-7  # 音量阈值

transcription_backend = ""
deepgram_api_key = ""

transcriber = None
sample_rate = 0

silent_since = None  # 开始静音的时间戳
recording = False
audio_queue = queue.Queue()
deepgram_audio_queue = queue.Queue()
last_text = ""


def init_parakeet_mlx():
    import mlx.core as mx
    from parakeet_mlx import from_pretrained

    global transcriber, sample_rate
    model = from_pretrained(MODEL_NAME)
    sample_rate = model.preprocessor_config.sample_rate
    transcriber = model.transcribe_stream(context_size=(256, 256))


def init_deepgram():
    from deepgram import DeepgramClient

    global transcriber, sample_rate
    transcriber = DeepgramClient(api_key=deepgram_api_key)
    sample_rate = 16000


def init_transcriber():
    if transcription_backend == "deepgram":
        init_deepgram()
    elif transcription_backend == "parakeet-mlx":
        init_parakeet_mlx()


def send_audio(audio_chunk):
    global last_text
    if transcription_backend == "deepgram":
        deepgram_audio_queue.put(audio_chunk)

    elif transcription_backend == "parakeet-mlx":
        audio_mlx = mx.array(audio_chunk.flatten())
        transcriber.add_audio(audio_mlx)
        result = transcriber.result
        if result.text != last_text:
            print(f"\rTranscription: {result.text}\n", end="", flush=True)
            last_text = result.text


async def handle_transcription():
    if transcription_backend == "deepgram":
        chunks = []
        while not deepgram_audio_queue.empty():
            chunks.append(deepgram_audio_queue.get_nowait())
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
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())

        response = transcriber.listen.v1.media.transcribe_file(
            request=buf.getvalue(), model="nova-3"
        )
        text = response.results.channels[0].alternatives[0].transcript
        print(text)
        await eval_in_emacs("message", [text])
        await eval_in_emacs("fuzzy-search", [text])

    elif transcription_backend == "parakeet-mlx":
        result = transcriber.result
        print(f"\n\nFinal transcription:\n{result.text}\n")
        if result.sentences:
            print("Timestamps:")
            for sentence in result.sentences:
                await eval_in_emacs("message", [result.text])
                await eval_in_emacs("fuzzy-search", [result.text])
                print()
        if result.text.strip():
            print(result.text)


async def toggle_recording():
    global recording

    if not recording:
        recording = True
        await eval_in_emacs("read-alound-notify", ["Listening..."])
        print("\nRecording started \n")
    else:
        recording = False
        await eval_in_emacs("read-alound-notify", ["Stopped..."])
        print("\nRecording stopped. Processing transcription...\n")


def audio_callback(indata, frames, the_time, status):
    global silent_since, recording
    if status:
        print(f"Audio status: {status}", file=sys.stderr)
    if recording:
        energy = float(np.mean(indata**2))
        if energy < SILENCE_THRESH:
            if silent_since is None:
                silent_since = time.time()
            else:
                if time.time() - silent_since >= SILENCE_DURATION:
                    # 已持续达到最小静音时间
                    silent_since = None
                    print("已检测到持续静音")
                    if recording:
                        recording = False
        else:
            # 非静音，重置持续静音计时
            silent_since = None
        audio_queue.put(indata.copy())


async def transcription_loop(sample_rate):
    global recording, last_text
    chunk_size = int(sample_rate * CHUNK_DURATION)

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=chunk_size,
        callback=audio_callback,
    ):
        while True:
            if not recording:
                await asyncio.sleep(1)
                continue

            while not audio_queue.empty():
                audio_queue.get()  # 丢弃所有旧数据

            last_text = ""
            while recording:
                try:
                    audio_chunk = audio_queue.get_nowait()
                    send_audio(audio_chunk)
                    await eval_in_emacs("message", ["Listening..."])
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue

            await handle_transcription()


async def get_emacs_var(var_name: str):
    "Get Emacs variable and format it."
    var_value = await bridge.get_emacs_var(var_name)
    if isinstance(var_value, str):
        var_value = var_value.strip('"')
    print(f"{var_name} : {var_value}")
    if var_value == "null":
        return None
    return var_value


async def init():
    global transcription_backend, sample_rate, deepgram_api_key
    transcription_backend = await get_emacs_var("read-alound-transcription-backend")
    deepgram_api_key = await get_emacs_var("read-alound-deepgram-api-key")
    print("=" * 60)
    print(f"Live Speech-to-Text with {transcription_backend}")
    print("=" * 60)
    print("\nLoading model...")

    # model = from_pretrained(MODEL_NAME)
    # sample_rate = model.preprocessor_config.sample_rate
    init_transcriber()

    print(f"Model loaded: {MODEL_NAME}")
    print(f"Sample rate: {sample_rate} Hz")
    print("\n" + "=" * 60)
    print("=" * 60 + "\n")

    asyncio.create_task(transcription_loop(sample_rate))
    # await toggle_recording()


def handle_arg_types(arg):
    if isinstance(arg, str) and arg.startswith("'"):
        arg = sexpdata.Symbol(arg.partition("'")[2])

    return sexpdata.Quoted(arg)


async def eval_in_emacs(method_name, args):
    args = [sexpdata.Symbol(method_name)] + list(map(handle_arg_types, args))  # type: ignore
    sexp = sexpdata.dumps(args)
    # print(sexp)
    await bridge.eval_in_emacs(sexp)


async def on_message(message):
    try:
        info = json.loads(message)
        print(info)
        cmd = info[1][0].strip()
        if cmd == "toggle":
            await toggle_recording()
        else:
            print(f"not fount handler for {cmd}", flush=True)

    except Exception as _:
        import traceback

        print(traceback.format_exc())


async def main():
    global bridge
    bridge = websocket_bridge_python.bridge_app_regist(on_message)
    await asyncio.gather(init(), bridge.start())


if __name__ == "__main__":
    asyncio.run(main())
