#!/usr/bin/env python3
"""Verbatim word-level transcription of a take. Writes a list of words.

    python transcribe.py <media> <out.json> [--engine auto|mlx|groq|whisper|crisper|scribe] [--lang de]

Output (docs/CONTRACTS.md, Transcription):
    [{"text": "so", "start": 0.12, "end": 0.31, "type": "word"},
     {"text": " ", "start": 0.31, "end": 0.40, "type": "spacing"}, ...]

--lang defaults to AI_EDITOR_LANG, else "auto" (the engine detects it; verify_cut passes no --lang).

Engines:
  mlx      mlx-whisper large-v3-turbo on the Apple GPU, free and local (local patch: the
           Creator Engine's install, a python3 outside the venv; AI_EDITOR_MLX_PYTHON overrides,
           AI_EDITOR_MLX_MODEL the model). About 30 s for a 4-minute take.
  groq     Groq whisper-large-v3 (local patch). Sends the audio to Groq. Key in GROQ_API_KEY.
           Only when asked: auto never picks it.
  whisper  faster-whisper, free and local. Needs ~/.ai-video-editor/venv.
           Model from AI_EDITOR_WHISPER_MODEL (default "small").
  crisper  CrisperWhisper 2.0, free and local, verbatim: keeps ums, repeats and false
           starts, which plain Whisper tidies away. `setup.py crisper` installs it
           (about 1 GB). Model from AI_EDITOR_CRISPER_MODEL (default "small"). Its
           weights are licensed for NON-COMMERCIAL use only.
  scribe   ElevenLabs Scribe v2, verbatim. Needs a key in ELEVENLABS_API_KEY or
           ~/.config/creator-teardown/.env ($AI_EDITOR_HOME/.env when that is set).
           Keeps every filler and false start.
  auto     scribe when a key exists, else mlx when found, else crisper when installed,
           else whisper (default).

Audio is pulled out with ffmpeg first (16 kHz mono WAV), so a multi-GB 4K file
costs one fast audio demux, never a video decode.

Exit codes: 0 ok, 1 error, 2 usage or missing key, 3 HTTP error
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from ai_editor import keys, models  # noqa: E402

HOME = models.HOME
HERE = Path(__file__).resolve().parent
# Whisper tidies speech by default. A prompt full of hesitations makes it keep
# more of them, and the fillers are the evidence the cut acts on.
FILLER_PROMPT = "Umm, uh, so, like, you know, I mean, uh, so, um, wait, sorry, let me start again."
# One per language; a detected language with no prompt here gets none (an English prompt
# pushes German speech towards English spellings).
FILLER_PROMPTS = {"en": FILLER_PROMPT,
                  "de": "Ähm, äh, also, ja, halt, sozusagen, äh, warte, sorry, nochmal von vorne."}
MLX_MODEL = os.environ.get("AI_EDITOR_MLX_MODEL", "mlx-community/whisper-large-v3-turbo")
REDO_PAD_S = 0.3     # each side of a stretch heard again, so its first and last word are whole
GROQ_LANG = {"german": "de", "english": "en", "french": "fr", "spanish": "es", "italian": "it", "dutch": "nl"}
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def find_key():
    return keys.get("elevenlabs")[0]


def vocab():
    """Words Whisper does not know (a coined term, a brand): AI_EDITOR_TERMS (a file path), else
    ~/.ai-video-editor/terms.txt, one a line, plus the profile's names. The prompt is how Whisper
    learns a spelling (local patch)."""
    f = Path(os.environ["AI_EDITOR_TERMS"]).expanduser() if os.environ.get("AI_EDITOR_TERMS") else HOME / "terms.txt"
    p, terms = HOME / "profile.json", []
    if f.exists():
        terms += [t.strip() for t in f.read_text().splitlines() if t.strip() and not t.startswith("#")]
    try:
        terms += [n["name"] if isinstance(n, dict) else str(n)
                  for n in json.loads(p.read_text()).get("names", [])] if p.exists() else []
    except (ValueError, KeyError, TypeError, AttributeError):
        pass
    return list(dict.fromkeys(t for t in terms if t))


def prompt(lang):
    """The filler prompt for the language, then the vocabulary. None when there is neither."""
    text = " ".join(x for x in (FILLER_PROMPTS.get(lang), ", ".join(vocab())) if x)
    return text or None


def opt_in_prompt(lang):
    """mlx and groq get no prompt unless AI_EDITOR_PROMPT=1: on a raw take a prompt makes Whisper drop
    repeated lines, and repeated lines are the retakes (a German take, 2026-10-08: three takes of one
    line heard without a prompt, one with it). A misheard term is fixed with `retakes.py fix` instead."""
    return prompt(lang) if os.environ.get("AI_EDITOR_PROMPT") == "1" else None


def mlx_python():
    """A python3 outside the editor's venv that imports mlx_whisper, or None."""
    for p in (os.environ.get("AI_EDITOR_MLX_PYTHON"), "/opt/homebrew/bin/python3", "/usr/local/bin/python3",
              shutil.which("python3")):
        if p and Path(p).exists() and subprocess.run([p, "-c", "import mlx_whisper"],
                                                     capture_output=True).returncode == 0:
            return p
    return None


def groq_key():
    """GROQ_API_KEY from the environment."""
    return os.environ.get("GROQ_API_KEY", "").strip() or None


def extract_audio(src, dst):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1",
                        "-ar", "16000", "-c:a", "pcm_s16le", str(dst)])
    if r.returncode:
        sys.exit(f"ERROR: ffmpeg could not read audio from {src}")


def with_spacing(words):
    """Insert spacing tokens for the gaps, so both engines give the same shape."""
    out = []
    for w in words:
        if out and w["start"] - out[-1]["end"] > 0.001:
            out.append({"text": " ", "start": out[-1]["end"], "end": w["start"], "type": "spacing"})
        out.append(w)
    return out


def run_whisper(wav, lang):
    os.environ.setdefault("HF_HOME", str(HOME / "models"))
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("ERROR: faster-whisper missing. Run this with python3 <plugin>/lib/ai_editor/run.py, which uses "
                 "the editor's venv (the setup skill installs it).")
    name = os.environ.get("AI_EDITOR_WHISPER_MODEL", "small")
    print(f"whisper model {name} (cpu, int8)", flush=True)
    # The pinned model (setup.py model); a size with no pin downloads from the Hub as before.
    model = WhisperModel(str(models.whisper(name, check=False) or name), device="cpu", compute_type="int8",
                         download_root=str(HOME / "models"))
    # condition_on_previous_text=False: with it on, whisper tends to collapse a
    # repeated line into one, and repeated lines are exactly the retakes.
    # vad_filter=True: without it, word times drift after a long silence (a line
    # placed 8 s after where it was said, on a real take), and raw takes are full
    # of long silences.
    segs, _ = model.transcribe(str(wav), language=lang, word_timestamps=True,
                               initial_prompt=prompt(lang), beam_size=5,
                               condition_on_previous_text=False, vad_filter=True,
                               vad_parameters={"min_silence_duration_ms": 500})

    def words_of(segs):
        return [{"text": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3), "type": "word"}
                for s in segs for w in (s.words or []) if w.word.strip()]

    def again(start, end):
        """The words in one stretch, transcribed on their own (no VAD: the stretch is speech)."""
        segs, _ = model.transcribe(str(wav), language=lang, word_timestamps=True, initial_prompt=prompt(lang),
                                   beam_size=5, condition_on_previous_text=False, clip_timestamps=[start, end])
        return [w for w in words_of(segs) if w["start"] >= start - 0.05 and w["end"] <= end + 0.05]

    return recheck(wav, with_spacing(words_of(segs)), again)


def window_words(words, start, end, slack=0.1):
    """The words of a padded re-transcription that belong to [start, end] (midpoint inside)."""
    return [w for w in words if start - slack <= (w["start"] + w["end"]) / 2 <= end + slack]


def recheck(wav, words, again=None, again_many=None):
    """A label holding far more speech than its word (build_timeline.unheard) is transcribed again on
    its own; the new words replace it when there are more of them, one word means a drawn-out word.
    With no words back (or no re-transcription, CrisperWhisper) the label keeps "unheard_s" (the voiced seconds), which transcript.txt shows so the cut can see the gap.
    local patch: a gap between two words holding clear speech (build_timeline.unheard_gaps: a restart
    Whisper dropped outright) is heard again too, and its words are inserted. again(start, end) hears
    one stretch; again_many([(start, end), ...]) hears them all in one go (mlx loads its model once)."""
    import build_timeline as B
    lvl = B.window_rms_db(wav)
    noise, _ = B.derive_noise_db(lvl)
    toks = [w for w in words if w["type"] != "spacing"]
    found = B.unheard(toks, lvl, noise) if noise is not None else []
    gaps = B.unheard_gaps(toks, lvl, noise) if noise is not None and (again or again_many) else []
    if not found and not gaps:
        return words
    wins = [(toks[i]["start"], toks[i]["end"]) for i, _ in found] + [(s, e) for _, s, e, _ in gaps]
    heard = (again_many(wins) if again_many else
             [again(s, e) for s, e in wins] if again else [[] for _ in wins])
    jobs = [(i, 0, v, h) for (i, v), h in zip(found, heard)] + \
           [(i, 1, v, window_words(h, s, e, slack=0.0)) for (i, s, e, v), h in zip(gaps, heard[len(found):])]
    filled = marked = inserted = 0
    for i, gap, voiced, got in sorted(jobs, key=lambda j: (j[0], j[1]), reverse=True):
        if gap:    # after toks[i], before the label job at i so the index still points at it
            if got:
                toks[i + 1:i + 1] = got
                inserted += 1
            continue
        w = toks[i]
        if len(got) > 1:
            toks[i:i + 1] = got
            filled += 1
        elif not got:   # one word heard again: a drawn-out word, nothing hidden
            w["unheard_s"] = voiced
            marked += 1
    if found:
        print(f"{len(found)} place(s) where one word held more speech: {filled} heard again"
              + (f", {marked} marked in transcript.txt" if marked else ""))
    if gaps:
        print(f"{len(gaps)} pause(s) holding speech no word covered: {inserted} heard again")
    return with_spacing(toks)


def redo_windows(wav, wins, hear):
    """Each stretch padded by REDO_PAD_S, cut out of wav and heard by hear(part_wav) -> words in the
    part's seconds; returns the words in wav's seconds that belong to each stretch."""
    out = []
    for s, e in wins:
        a, b = max(0.0, s - REDO_PAD_S), e + REDO_PAD_S
        part = Path(wav).with_name(f"redo_{len(out):03d}.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(wav),
                        "-c:a", "pcm_s16le", str(part)])
        got = hear(part) if part.exists() else []
        out.append(window_words([dict(w, start=round(w["start"] + a, 3), end=round(w["end"] + a, 3))
                                 for w in got if w.get("type", "word") == "word"], s, e))
    return out


def has_crisper():
    import importlib.util
    return importlib.util.find_spec("crisperwhisper") is not None


def run_crisper(wav, lang):
    os.environ.setdefault("HF_HOME", str(HOME / "models"))
    try:
        from crisperwhisper import CrisperWhisperModel
    except ImportError:
        sys.exit("ERROR: CrisperWhisper missing. Install it with the setup skill: setup.py crisper")
    name = os.environ.get("AI_EDITOR_CRISPER_MODEL", "small")
    print(f"crisperwhisper {name} (verbatim; weights licensed for non-commercial use)", flush=True)
    r = CrisperWhisperModel(name).transcribe(str(wav), language=lang, word_timestamps=True)
    words = []
    for w in r.words or []:
        t = w.word.strip()
        if not t:
            continue
        # Verbatim mode writes fillers as [um] and sounds as [laughter].
        inner = t.strip("[]").strip()
        tag = t.startswith("[") and t.endswith("]")
        filler = inner.lower() in ("um", "uh", "umm", "uhh", "hmm", "mm", "er", "erm", "ah")
        words.append({"text": inner if tag and filler else t, "start": round(w.start, 3),
                      "end": round(w.end, 3), "type": "audio_event" if tag and not filler else "word"})
    return recheck(wav, with_spacing(words))


def run_scribe(wav, key, lang):
    fields = [("model_id", "scribe_v2"), ("timestamps_granularity", "word"),
              ("tag_audio_events", "true"), ("no_verbatim", "false"), ("diarize", "false"),
              ("temperature", "0"), ("seed", "0")]
    if lang:
        fields.append(("language_code", lang))
    b = "----cut" + os.urandom(12).hex()
    body = bytearray()
    for k, v in fields:
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\n'
             f"Content-Type: audio/wav\r\n\r\n").encode() + Path(wav).read_bytes() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=bytes(body),
                                 headers={"xi-api-key": key,
                                          "Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode(errors='replace')[:400]}", file=sys.stderr)
        sys.exit(3)
    except (urllib.error.URLError, OSError) as e:   # no network, DNS, a timeout
        print(f"ElevenLabs unreachable ({getattr(e, 'reason', e)}). Check the connection and run again, "
              "or use --engine whisper (free, on this computer).", file=sys.stderr)
        sys.exit(3)
    return [{"text": w["text"], "start": w["start"], "end": w["end"], "type": w["type"]}
            for w in payload.get("words", []) if w.get("type") in ("word", "spacing", "audio_event")]


def run_mlx(wav, lang):
    py = mlx_python()
    if not py:
        sys.exit("ERROR: mlx-whisper missing: pip3 install --user mlx-whisper, or set AI_EDITOR_MLX_PYTHON")
    print(f"mlx-whisper {MLX_MODEL} (Apple GPU)", flush=True)
    out = Path(wav).with_name("mlx.json")
    cmd = [py, str(HERE / "mlx_words.py"), str(wav), str(out), "--model", MLX_MODEL]
    if lang:
        cmd += ["--lang", lang]
    if opt_in_prompt(lang):
        cmd += ["--prompt", opt_in_prompt(lang)]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    print(r.stdout, end="", flush=True)
    if r.returncode:
        sys.exit("ERROR: mlx-whisper failed (output above). --engine whisper runs on the CPU instead.")
    said = lang or next((x.split()[1] for x in r.stdout.splitlines() if x.startswith("language ")
                         and len(x.split()) > 1 and x.split()[1] != "None"), None)

    def again_many(wins):
        """Every stretch heard alone (padded REDO_PAD_S), in the language the whole take was heard in:
        a 2 s stretch on its own can be taken for English."""
        f, o = Path(wav).with_name("mlx_windows.json"), Path(wav).with_name("mlx_redo.json")
        pads = [(max(0.0, s - REDO_PAD_S), e + REDO_PAD_S) for s, e in wins]
        f.write_text(json.dumps(pads))
        c = [py, str(HERE / "mlx_words.py"), str(wav), str(o), "--model", MLX_MODEL, "--windows", str(f)]
        if subprocess.run(c + (["--lang", said] if said else []), capture_output=True).returncode or not o.exists():
            return [[] for _ in wins]
        return [window_words(g, s, e) for g, (s, e) in zip(json.loads(o.read_text()), wins)]

    return recheck(wav, with_spacing(json.loads(out.read_text())), again_many=again_many)


def run_groq(wav, key, lang):
    words, said = groq_words(wav, key, lang)
    print(f"language {said}", flush=True)
    said = lang or GROQ_LANG.get(str(said).lower())
    return recheck(wav, with_spacing(words), again_many=lambda wins: redo_windows(
        wav, wins, lambda part: groq_words(part, key, said)[0]))


def groq_words(wav, key, lang):
    """(words, language) from one Groq request."""
    flac = Path(wav).with_suffix(".flac")   # half the size of the wav: Groq's free tier takes 25 MB
    if subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "flac", str(flac)]).returncode:
        sys.exit("ERROR: ffmpeg could not encode flac for Groq")
    fields = [("model", "whisper-large-v3"), ("response_format", "verbose_json"),
              ("timestamp_granularities[]", "word"), ("temperature", "0")]
    if lang:
        fields.append(("language", lang))
    if opt_in_prompt(lang):
        fields.append(("prompt", opt_in_prompt(lang)))
    b = "----cut" + os.urandom(12).hex()
    body = bytearray()
    for k, v in fields:
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.flac"\r\n'
             f"Content-Type: audio/flac\r\n\r\n").encode() + flac.read_bytes() + f"\r\n--{b}--\r\n".encode()
    # A browser User-Agent: Cloudflare in front of some APIs answers urllib's default with error 1010.
    req = urllib.request.Request(GROQ_URL, data=bytes(body), headers={
        "Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={b}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ai-editor"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode(errors='replace')[:400]}", file=sys.stderr)
        sys.exit(3)
    except (urllib.error.URLError, OSError) as e:
        print(f"Groq unreachable ({getattr(e, 'reason', e)}). Run again, or use --engine mlx (free, on this "
              "computer).", file=sys.stderr)
        sys.exit(3)
    words = [{"text": w["word"].strip(), "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3),
              "type": "word"} for w in payload.get("words", []) if w.get("word", "").strip()]
    return words, payload.get("language")


def pick_engine(name, key=None):
    return name if name != "auto" else (
        "scribe" if key else "mlx" if mlx_python() else "crisper" if has_crisper() else "whisper")


def hear_windows(wav, wins, engine="auto", lang=None):
    """Each stretch of wav heard on its own, unpadded (local patch, verify_cut's per-run check: a whole
    render heard at once collapses a line said twice into one). One word list per stretch, in wav's
    seconds. mlx hears them all with one model load; other engines run this script per stretch."""
    engine = pick_engine(engine, find_key())
    if engine == "mlx" and mlx_python():
        f, o = Path(wav).with_name("pieces_windows.json"), Path(wav).with_name("pieces_words.json")
        f.write_text(json.dumps([list(w) for w in wins]))
        c = [mlx_python(), str(HERE / "mlx_words.py"), str(wav), str(o), "--model", MLX_MODEL, "--windows", str(f)]
        if subprocess.run(c + (["--lang", lang] if lang else []), capture_output=True).returncode or not o.exists():
            sys.exit("ERROR: mlx-whisper failed on the per-run check")
        return json.loads(o.read_text())
    out = []
    for k, (s, e) in enumerate(wins):
        part, js = Path(wav).with_name(f"piece_{k:03d}.wav"), Path(wav).with_name(f"piece_{k:03d}.json")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", str(wav),
                        "-c:a", "pcm_s16le", str(part)])
        r = subprocess.run([sys.executable, str(HERE / "transcribe.py"), str(part), str(js), "--engine", engine]
                           + (["--lang", lang] if lang else []), capture_output=True)
        got = json.loads(js.read_text()) if not r.returncode and js.exists() else []
        out.append([dict(w, start=round(w["start"] + s, 3), end=round(w["end"] + s, 3))
                    for w in got if w.get("type") == "word"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media")
    ap.add_argument("out")
    ap.add_argument("--engine", choices=["auto", "mlx", "groq", "whisper", "crisper", "scribe"], default="auto")
    ap.add_argument("--lang", default=os.environ.get("AI_EDITOR_LANG", "auto"))
    a = ap.parse_args()
    lang = None if a.lang in ("", "auto") else a.lang

    if not Path(a.media).exists():
        sys.exit(f"ERROR: no such file: {a.media}")
    key = find_key()
    engine = pick_engine(a.engine, key)
    if engine == "scribe" and not key:
        print(f"ERROR: no ElevenLabs key (ELEVENLABS_API_KEY or {keys.key_file()})", file=sys.stderr)
        sys.exit(2)
    gkey = groq_key() if engine == "groq" else None
    if engine == "groq" and not gkey:
        print("ERROR: no Groq key (set GROQ_API_KEY in your own terminal)", file=sys.stderr)
        sys.exit(2)

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        extract_audio(a.media, wav)
        print(f"engine {engine}", flush=True)
        if engine == "groq":
            print("groq whisper-large-v3", flush=True)
        if engine == "scribe":
            words = run_scribe(wav, key, lang)
        elif engine == "groq":
            words = run_groq(wav, gkey, lang)
        else:
            words = {"mlx": run_mlx, "whisper": run_whisper, "crisper": run_crisper}[engine](wav, lang)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(words, indent=1))
    n = sum(1 for w in words if w["type"] == "word")
    print(f"{n} words -> {out}")


if __name__ == "__main__":
    main()
