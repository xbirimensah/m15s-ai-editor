#!/usr/bin/env python3
"""Word timings from mlx-whisper on the Apple GPU, in transcribe.py's word shape.

    python3 mlx_words.py <audio.wav> <out.json> [--model REPO] [--lang de] [--prompt "..."]
    python3 mlx_words.py <audio.wav> <out.json> --windows <windows.json>   one word list per stretch

Runs under a python3 that has mlx-whisper (the Creator Engine's install, outside the editor's
venv). transcribe.py --engine mlx calls it; never run it with -I, mlx-whisper lives in the user
site-packages.
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--windows", default=None,
                    help="JSON [[start, end], ...]: each stretch transcribed on its own, the model loaded once; "
                         "out is one word list per stretch, in the audio's seconds")
    a = ap.parse_args()
    try:
        import mlx_whisper
    except ImportError:
        sys.exit("ERROR: mlx-whisper missing: pip3 install --user mlx-whisper")
    # condition_on_previous_text=False keeps repeated lines apart (they are the retakes). No
    # hallucination_silence_threshold: it skipped whole retakes that follow a pause.
    def words_of(audio, off=0.0):
        r = mlx_whisper.transcribe(audio, path_or_hf_repo=a.model, language=a.lang or None,
                                   word_timestamps=True, initial_prompt=a.prompt or None,
                                   condition_on_previous_text=False)
        return r, [{"text": w["word"].strip(), "start": round(float(w["start"]) + off, 3),
                    "end": round(float(w["end"]) + off, 3), "type": "word"}
                   for s in r.get("segments", []) for w in s.get("words", []) if w.get("word", "").strip()]

    if a.windows:
        from mlx_whisper.audio import SAMPLE_RATE, load_audio
        audio = load_audio(a.audio)
        out = [words_of(audio[int(s * SAMPLE_RATE):int(e * SAMPLE_RATE)], s)[1]
               for s, e in json.load(open(a.windows))]
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
        return
    r, words = words_of(a.audio)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False)
    print(f"language {r.get('language')}", flush=True)


if __name__ == "__main__":
    main()
