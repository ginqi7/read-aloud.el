#!/usr/bin/env python3

import numpy as np
import asyncio
import json
import sexpdata
import websocket_bridge_python

import queue
import sys
import time
import mlx.core as mx
import sounddevice as sd
from parakeet_mlx import from_pretrained

MODEL_NAME = "mlx-community/parakeet-tdt-0.6b-v3"
CHUNK_DURATION = 1.0
SILENCE_DURATION = 0.5
SILENCE_THRESH = 1e-7  # 音量阈值

silent_since = None  # 开始静音的时间戳
recording = False
audio_queue = queue.Queue()


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


async def transcription_loop(model, sample_rate):
    global recording
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

            with model.transcribe_stream(context_size=(256, 256)) as transcriber:
                while not audio_queue.empty():
                    audio_queue.get()  # 丢弃所有旧数据

                last_text = ""
                while recording:
                    try:
                        audio_chunk = audio_queue.get_nowait()

                        audio_mlx = mx.array(audio_chunk.flatten())
                        transcriber.add_audio(audio_mlx)

                        result = transcriber.result
                        if result.text != last_text:
                            print(
                                f"\rTranscription: {result.text}\n", end="", flush=True
                            )
                            last_text = result.text
                        await eval_in_emacs("message", ["Listening..."])
                    except queue.Empty:
                        await asyncio.sleep(0.01)
                        continue

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


async def init():
    print("=" * 60)
    print("Live Speech-to-Text with parakeet-mlx")
    print("=" * 60)
    print("\nLoading model...")

    model = from_pretrained(MODEL_NAME)
    sample_rate = model.preprocessor_config.sample_rate

    print(f"Model loaded: {MODEL_NAME}")
    print(f"Sample rate: {sample_rate} Hz")
    print("\n" + "=" * 60)
    print("=" * 60 + "\n")

    asyncio.create_task(transcription_loop(model, sample_rate))
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
