#!/usr/bin/env python3
"""Re-transcribe cut.mp4 and diff it against the words the cut meant to keep.

    python verify_cut.py <edit_dir> [--engine auto|whisper|scribe]
    python verify_cut.py demo        self-check (offline)

Run it with the venv python (it calls transcribe.py). Use the same engine as the
raw transcript, or the diff fills with spelling noise.

  MISSING   a kept word is not in the render: a boundary landed too tight.
            Fix: raise --pad, or narrow the span that ate it, rebuild, re-render.
  SURVIVED  a removed word is still audible, including a fragment ("open" left
            from a sliced "opening"): a boundary landed too loose. Each line gives
            its time in the cut, its time in the source and the span to add.
  REPEAT    (local patch) each run of the render (the kept spans between two removals) is heard
            again ON ITS OWN, and a phrase said twice inside one run, or across a join, is listed.
            Heard whole, the render hides it: Whisper collapses a line said twice into one, so
            three takes of "Alles was du brauchst" passed as one (2026-10-11). Each line gives the
            run's source time: add a span for the extra take.

Fillers ("um", "uh") that come and go between two passes are transcriber
variance and are listed separately, not as errors. So is a kept word the second pass
spelled differently at the same time in the cut ("Jev" heard as "Jeff"): HEARD
DIFFERENTLY, matched by time (textnorm.pair_by_time), never MISSING.

Writes <edit_dir>/cut.transcript.json and cut.runs.json (reused while newer than cut.mp4). Exit 0 clean,
1 missing, survived or repeated words.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_timeline import is_kept, load_fitted, retime  # noqa: E402
from textnorm import load_words, pair_by_time, timed_words, transcript_words  # noqa: E402

FILLERS = {"um", "uh", "umm", "uhh", "hmm", "mm", "ah", "er", "erm"}
RUN_GAP_S = 1.0   # kept spans this close in the source are one run that the pause cuts split
REPEAT_N = 3      # words in a row that make a repeated phrase


def runs_of(spans):
    """[(cut_start, cut_end, src_start, src_end)]: kept spans joined into runs, in play order."""
    out, t = [], 0.0
    for s in spans:
        n = s["end"] - s["start"]
        if out and 0 <= s["start"] - out[-1][3] <= RUN_GAP_S:
            out[-1] = (out[-1][0], round(t + n, 6), out[-1][2], s["end"])
        else:
            out.append((round(t, 6), round(t + n, 6), s["start"], s["end"]))
        t += n
    return out


def repeats(texts, n=REPEAT_N):
    """[(i, phrase)]: n words said twice inside run i (not overlapping), or at the end of run i and
    again at the start of run i + 1."""
    out = []
    for i, ws in enumerate(texts):
        seen = {}
        for k in range(len(ws) - n + 1):
            g = tuple(ws[k:k + n])
            if g in seen and k - seen[g] >= n:
                out.append((i, " ".join(g)))
                break
            seen.setdefault(g, k)
        if i + 1 < len(texts):
            tail, head = ws[-2 * n:], texts[i + 1][:2 * n]
            hg = {tuple(head[k:k + n]) for k in range(len(head) - n + 1)}
            hit = next((g for g in (tuple(tail[k:k + n]) for k in range(len(tail) - n + 1)) if g in hg), None)
            if hit:
                out.append((i, " ".join(hit) + " (again after the join)"))
    return out


def check_runs(d, spans, engine):
    """Hear every run of cut.mp4 on its own and list repeated phrases. Returns the REPEAT count."""
    import tempfile
    import transcribe as T
    from textnorm import nwords
    rs = runs_of(spans)
    fr = d / "cut.runs.json"
    if fr.exists() and fr.stat().st_mtime > (d / "cut.mp4").stat().st_mtime:
        heard = json.loads(fr.read_text())
    else:
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "cut.wav"
            T.extract_audio(d / "cut.mp4", wav)
            heard = T.hear_windows(wav, [(a, b) for a, b, _, _ in rs], engine)
        fr.write_text(json.dumps(heard, ensure_ascii=False))
    texts = [[x for w in ws for x in nwords(w["text"])] for ws in heard]
    reps = repeats(texts)
    print(f"\nRUNS ({len(rs)}), each heard on its own:")
    for i, ((a, b, sa, sb), ws) in enumerate(zip(rs, heard)):
        flag = "  <- REPEAT" if any(k == i for k, _ in reps) else ""
        print(f"  {i + 1:2}. cut {a:6.2f}-{b:6.2f}s source {sa:7.2f}-{sb:7.2f}s  {' '.join(w['text'] for w in ws)}{flag}")
    if reps:
        print(f"\nREPEAT ({len(reps)}): a phrase said twice. Add a span for the extra take:")
        for i, g in reps:
            print(f"  run {i + 1} (source {rs[i][2]:.2f}-{rs[i][3]:.2f}s): {g!r}")
    return len(reps)


def to_source(t, spans):
    """A time on the cut -> the same moment in the source (decisions.json spans are the kept parts)."""
    off = 0.0
    for s in spans:
        n = s["end"] - s["start"]
        if t <= off + n:
            return round(s["start"] + max(0.0, t - off), 2)
        off += n
    return round(spans[-1]["end"], 2) if spans else round(t, 2)


def span_to_add(raw, a, b):
    """The spans.json entry for the source words heard between a and b (source seconds), or None."""
    ws = [w for w in raw if a - 0.1 <= (w["start"] + w["end"]) / 2 <= b + 0.1]
    if not ws:
        return None
    return {"text": " ".join(w["text"].strip() for w in ws), "kind": "retake", "after": round(max(0.0, ws[0]["start"] - 0.05), 2)}


def main():
    if sys.argv[1:] == ["demo"]:
        return demo()
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir")
    ap.add_argument("--engine", default="auto")
    ap.add_argument("--no-runs", dest="runs", action="store_false", help="skip hearing each run on its own")
    a = ap.parse_args()
    d = Path(a.edit_dir)

    spans = json.loads((d / "decisions.json").read_text())
    raw = [w for w in load_fitted(d) if w.get("type") == "word"]
    exp = timed_words(retime(raw, spans))      # the kept words, timed on the cut
    expected = [t for t, _, _ in exp]
    removed = set(transcript_words([w for w in raw if not is_kept(w, spans)]))

    ft = d / "cut.transcript.json"
    fresh = ft.exists() and ft.stat().st_mtime > (d / "cut.mp4").stat().st_mtime
    r = subprocess.CompletedProcess([], 0) if fresh else subprocess.run([sys.executable, str(HERE / "transcribe.py"), str(d / "cut.mp4"), str(ft),
                        "--engine", a.engine])
    if r.returncode:
        sys.exit(1)
    act = timed_words(load_words(ft))
    actual = [t for t, _, _ in act]
    rc = report(d, expected, actual, removed, *pair_by_time(exp, act), act=act, spans=spans, raw=raw)
    if a.runs and check_runs(d, spans, a.engine):
        print("\nNOT OK: the render repeats a phrase (REPEAT above).")
        return 1
    return rc


def report(d, expected, actual, removed, same, differ, gone, new, act=None, spans=None, raw=None):
    missing = [(i, expected[i]) for i in gone]
    extra = [actual[j] for j in new]
    runs = []
    for j in sorted(new):          # runs of consecutive heard-only tokens, for the context lines
        if runs and runs[-1][1] == j:
            runs[-1][1] = j + 1
        else:
            runs.append([j, j + 1])
    heard = {}
    for i, js in differ:
        key = f"{expected[i]} -> {' '.join(actual[j] for j in js)}"
        heard[key] = heard.get(key, 0) + 1

    def fragment(tok):
        return tok in removed or any(len(tok) >= 2 and len(r) >= 2 and
                                     (r.startswith(tok) or tok.startswith(r)) for r in removed)

    noise = [t for _, t in missing if t in FILLERS] + [t for t in extra if t in FILLERS]
    missing = [(i, t) for i, t in missing if t not in FILLERS]
    survived = [t for t in extra if t not in FILLERS and fragment(t)]

    print(f"expected {len(expected)} words, heard {len(actual)}, match {len(same) / max(1, len(expected)) * 100:.1f}%")
    if missing:
        print(f"\nMISSING ({len(missing)}), with the kept words around each:")
        for i, t in missing[:30]:
            print(f"  {t!r:14} ... {' '.join(expected[max(0, i - 4):i + 5])} ...")
    if survived:
        print(f"\nSURVIVED ({len(survived)}), heard in the render where nothing was expected [in brackets].")
        print("A real survivor is a repeat or a stumble. Clean speech here means the raw transcript misheard it:")
        for j1, j2 in runs:
            if any(fragment(t) for t in actual[j1:j2] if t not in FILLERS):
                print(f"  ... {' '.join(actual[max(0, j1 - 4):j1])} [{' '.join(actual[j1:j2])}] "
                      f"{' '.join(actual[j2:j2 + 4])} ...")
                if act and spans:
                    a, b = act[j1][1], act[j2 - 1][2]
                    sa, sb = to_source(a, spans), to_source(b, spans)
                    print(f"    cut {a:.2f}-{b:.2f}s = source {sa:.2f}-{sb:.2f}s")
                    add = span_to_add(raw or [], sa, sb)
                    if add:
                        print(f"    span to add, if it is a real repeat: {json.dumps(add)}")
    if heard:
        print(f"\nHEARD DIFFERENTLY ({sum(heard.values())}), the same time in the cut spelled another way by the second "
              "pass (a misheard name, not a cut error; captions take the cut's spelling):")
        print("  " + ", ".join(f"{k} x{n}" if n > 1 else k for k, n in heard.items()))
    other = [t for t in extra if t not in FILLERS and not fragment(t)]
    if other:
        print(f"\nnote: {len(other)} other token(s) differ (transcriber variance): {' '.join(other[:15])}")
    if noise:
        print(f"note: fillers that differ between passes: {len(noise)}")

    rep = json.loads((d / "report.json").read_text()) if (d / "report.json").exists() else {"model_cuts": []}
    check = [c for c in rep["model_cuts"] if c["confidence"] == "low" or c["kind"] == "redundant"]
    if check:
        print(f"\nSPOT-CHECK {len(check)} judgement call(s):")
        for c in check:
            print(f"  {c['start']:7.2f}s [{c['kind']}] {c['evidence'][:60]!r}")
    print("\nOK: the render matches the intended cut." if not (missing or survived) else "")
    return 1 if (missing or survived) else 0


def demo():
    import contextlib
    import io
    spans = [{"start": 0.0, "end": 2.0}, {"start": 5.0, "end": 8.0}]
    assert to_source(1.0, spans) == 1.0 and to_source(2.5, spans) == 5.5 and to_source(9, spans) == 8.0
    raw = [{"text": t, "start": s, "end": s + 0.3, "type": "word"} for t, s in
           (("less", 0.8), ("than", 1.2), ("cents", 1.6), ("and", 4.6), ("and", 5.05), ("to", 5.4))]
    act = [("less", 0.8, 1.1), ("than", 1.2, 1.5), ("cents", 1.6, 1.9), ("and", 2.0, 2.2), ("and", 2.05, 2.35),
           ("to", 2.4, 2.7)]
    expected = ["less", "than", "cents", "and", "to"]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = report(Path("."), expected, [t for t, _, _ in act], {"and"}, [0, 1, 2, 3, 5], [], [], [4],
                    act=act, spans=spans, raw=raw)
    txt = out.getvalue()
    assert rc == 1 and "SURVIVED (1)" in txt, txt
    assert "cut 2.05-2.35s = source 5.05-5.35s" in txt, txt
    assert '"text": "and", "kind": "retake", "after": 5.0' in txt, txt
    # runs: a pause cut splits one run (5.0-6.0 + 6.3-7.0); a move plays an earlier line after it
    sp = [{"start": 5.0, "end": 6.0}, {"start": 6.3, "end": 7.0}, {"start": 1.0, "end": 2.0}, {"start": 9.5, "end": 10.0}]
    assert runs_of(sp) == [(0.0, 1.7, 5.0, 7.0), (1.7, 2.7, 1.0, 2.0), (2.7, 3.2, 9.5, 10.0)], runs_of(sp)
    w = str.split
    assert repeats([w("alles was du brauchst ist alles was du brauchst ist das framework")]) == [(0, "alles was du")]
    assert repeats([w("5 hooks 5 bodys und 3 ctas"), w("dann schneidest du")]) == []
    assert repeats([w("und das geilste ist du musst"), w("das geilste ist du musst dafür")]) == \
        [(0, "das geilste ist (again after the join)")]
    print("verify_cut ok")


if __name__ == "__main__":
    sys.exit(main())
