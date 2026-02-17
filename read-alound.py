#!/usr/bin/env python3
import numpy as np
import asyncio
import json
import sexpdata
import websocket_bridge_python

import queue
import sys
import time
import sounddevice as sd

from transcriber import Transcriber


CHUNK_DURATION = 1.0
SILENCE_DURATION = 0.5
SILENCE_THRESH = 1e-7  # Volume Threshold

transcriber: Transcriber = None
silent_since = None  # Timestamp for Start of Mute
recording = False
audio_queue = queue.Queue()


async def handle_transcription():
    """Handle transcription by posting a progress message, retrieving the latest transcription result, and if present, sending it to Emacs for display and fuzzy search."""
    await eval_in_emacs("message", ["transcript..."])
    result = transcriber.handle_transcription()
    if result:
        await eval_in_emacs("message", [result])
        await eval_in_emacs("fuzzy-search", [result])


async def toggle_recording():
    """Toggle the recording state, notify Emacs when listening starts or stops, and print the corresponding recording status message."""
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
    """Process incoming audio frames during recording, detect sustained silence to stop recording automatically, reset silence timing on non-silent input, and enqueue audio data for later processing."""
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
                    # Minimum quiet time has been consistently achieved.
                    silent_since = None
                    print("Continuous silence detected.")
                    if recording:
                        recording = False
        else:
            # Non-silent, reset continuous silence timer.
            silent_since = None
        audio_queue.put(indata.copy())


async def transcription_loop(sample_rate):
    """Continuously manage the audio input stream, wait for recording to start, clear stale buffered audio, stream live audio chunks to the transcriber while recording, and process transcription after recording stops."""
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

            while not audio_queue.empty():
                audio_queue.get()  # Discard all old data

            while recording:
                try:
                    audio_chunk = audio_queue.get_nowait()
                    transcriber.send_audio(audio_chunk)
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue

            await handle_transcription()


async def get_emacs_var(var_name: str):
    """Fetch an Emacs variable value by name, normalize quoted string results, log the resolved value, and return None when the value is null."""
    var_value = await bridge.get_emacs_var(var_name)
    if isinstance(var_value, str):
        var_value = var_value.strip('"')
    print(f"{var_name} : {var_value}")
    if var_value == "null":
        return None
    return var_value


async def init():
    """Initialize transcription settings from Emacs variables, select and instantiate the configured transcription backend, display startup status information, and launch the asynchronous transcription loop."""
    global transcriber
    transcription_backend = await get_emacs_var("read-alound-transcription-backend")
    deepgram_api_key = await get_emacs_var("read-alound-deepgram-api-key")
    vosk_model_directory = await get_emacs_var("read-alound-vosk-model-directory")
    print("=" * 60)
    print(f"Live Speech-to-Text with {transcription_backend}")
    print("=" * 60)
    print("\nLoading model...")

    sample_rate = 16000
    if transcription_backend == "deepgram":
        from transcriber_deepgram import DeepgramTranscriber

        transcriber = DeepgramTranscriber(sample_rate, deepgram_api_key)
    elif transcription_backend == "parakeet-mlx":
        from transcriber_parakeet_mlx import ParakeetMlxTranscriber

        transcriber = ParakeetMlxTranscriber(sample_rate)
    elif transcription_backend == "vosk":
        from transcriber_vosk import VoskTranscriber

        transcriber = VoskTranscriber(sample_rate, vosk_model_directory)

    print("Model loaded:")
    print(f"Sample rate: {sample_rate} Hz")
    print("\n" + "=" * 60)
    print("=" * 60 + "\n")

    asyncio.create_task(transcription_loop(sample_rate))
    # await toggle_recording()


def handle_arg_types(arg):
    """Convert Lisp-style quoted string arguments into symbols when needed and return the argument wrapped as a quoted S-expression."""
    if isinstance(arg, str) and arg.startswith("'"):
        arg = sexpdata.Symbol(arg.partition("'")[2])

    return sexpdata.Quoted(arg)


async def eval_in_emacs(method_name, args):
    """Build an Emacs Lisp S-expression from the method name and processed arguments, serialize it, and asynchronously evaluate it in Emacs through the bridge."""
    args = [sexpdata.Symbol(method_name)] + list(map(handle_arg_types, args))  # type: ignore
    sexp = sexpdata.dumps(args)
    # print(sexp)
    await bridge.eval_in_emacs(sexp)


async def on_message(message):
    """Parse an incoming message payload, dispatch the toggle command to recording control when requested, report unknown commands, and print a traceback if processing fails."""
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
    """Register the message handler with the websocket bridge, initialize transcription services, and run initialization and bridge startup concurrently."""
    global bridge
    bridge = websocket_bridge_python.bridge_app_regist(on_message)
    await asyncio.gather(init(), bridge.start())


if __name__ == "__main__":
    asyncio.run(main())
