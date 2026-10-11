#!/usr/bin/env python3
"""Frame-accurate cut from a plan.json.

Usage:
    python3 cut.py plan.json [--out-dir DIR]

plan.json:
{
  "name":    "my-video",              // output name (forced to lowercase)
  "source":  "/path/to/raw.mp4",
  "format":  "916",                   // "916" (1080x1920), "169" (1920x1080), "916_4k", "169_4k"
  "fps":     30,
  "speed":   1.0,                     // default 1.0: neutral engine, no speed-up
  "fit":     "pad",                   // "pad" (bars) or "cover" (fill by cropping)
  "crop_x":  null,                    // fit=cover only: fixed x position of the crop
                                      //   (person not centred → set it by hand)
  "segments": [[12.4, 18.2], [21.0, 30.5]],  // keep segments in seconds
  "xfade":   {"0": 0.25}              // optional: cross-fade (s) between segment i and i+1,
                                      //   picture dissolve + audio cross-fade (soft hook → body)
}

Steps:
  1. Round segment bounds to the frame grid. Per segment, cut video (exactly N frames, CRF 18,
     yuv420p, fps from the plan) and audio (PCM, exactly N/fps seconds, 12 ms fade in/out
     against clicks at the joins) SEPARATELY.
  2. Video via the concat demuxer (stream copy), audio as PCM back to back, mux once.
     Previously AAC per segment: every segment brought ~21 ms of encoder priming, after
     22 segments the audio ran 0.5 s behind the picture and fell off at the end
     (the last word was cut off).
  3. If speed != 1.0: setpts/atempo AFTER the concat (one re-encode).
  4. Finally a gentle one-pass loudness pass (loudnorm I=-16, video stream copy).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

FF = shutil.which("ffmpeg")

FORMATS = {
    "916": (1080, 1920),
    "169": (1920, 1080),
    "916_4k": (2160, 3840),   # 4K portrait (DJI/iPhone 4K), the source stays 4K
    "169_4k": (3840, 2160),
    "916_1440": (1440, 2560),  # 1440p portrait (green-screen app export), the source stays 1440p
    "916_3k": (1728, 3072),    # DJI Osmo Pocket 3K portrait, the source stays 3K (room for punch-ins)
    "split_bottom": (1080, 960),  # bottom half of a split reel (b-roll on top, speaker below)
    "split_face": (1080, 1060),   # camera layer behind a panel layout (visible from y 920, behind the panel corners from 860)
}


def fail(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def vf_for(fmt, fit, crop_x, fps):
    w, h = FORMATS[fmt]
    if fit == "cover" and crop_x is not None:
        # Fixed crop position in source pixels: a 9:16 or 16:9 window at full height/width.
        if fmt.startswith("916") or fmt.startswith("split_"):
            vf = f"crop='min(iw,ih*{w}/{h})':ih:{int(crop_x)}:0,scale={w}:{h}"
        else:
            vf = f"crop=iw:'min(ih,iw*{h}/{w})':0:{int(crop_x)},scale={w}:{h}"
    elif fit == "cover":
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    else:  # pad
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
        )
    return f"{vf},setsar=1,fps={fps},setpts=N/({fps}*TB)"   # gapless frame timestamps from 0 (otherwise jumps at the joins)


def frame_grid(start, end, fps):
    """Start and duration in whole frames, so picture and sound are exactly the same length per segment."""
    f0, f1 = round(start * fps), round(end * fps)
    if f1 - f0 < 3:
        fail(f"Segment [{start}, {end}] is too short or negative.")
    return f0 / fps, f1 - f0


def decode_audio(src, dst):
    """The whole soundtrack once, as 48 kHz stereo PCM. Segments are cut from this file: seeking in PCM is
    sample-exact, while an audio seek inside the camera file can land on the next keyframe (DJI files under
    ffmpeg 8+ came back 0.2-1.0 s late, dropping the first words of a segment)."""
    run([FF, "-y", "-i", src, "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", dst])


def cut_segment(src, pcm, start, frames, fps, vdst, adst, vf):
    dur = frames / fps
    fade_out = max(0.0, dur - 0.012)
    # asetpts first: afade's st= is a timestamp, so the segment's timestamps must start at 0.
    af = (f"asetpts=PTS-STARTPTS,atrim=duration={dur:.6f},apad=whole_dur={dur:.6f},"
          f"afade=t=in:st=0:d=0.012,afade=t=out:st={fade_out:.6f}:d=0.012")
    run([
        FF, "-y", "-ss", f"{start:.6f}", "-i", src, "-frames:v", str(frames), "-an",
        "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", vdst,
    ])
    run([
        FF, "-y", "-ss", f"{start:.6f}", "-i", pcm, "-af", af,
        "-ac", "2", "-c:a", "pcm_s16le", adst,
    ])


def xfade_pair(v0, a0, d0, v1, a1, x, vout, aout):
    """Segment 1 dissolves into segment 2: duration d0 + d1 - x (x sits on the frame grid)."""
    run([FF, "-y", "-i", v0, "-i", v1, "-filter_complex",
         f"[0:v][1:v]xfade=transition=fade:duration={x:.6f}:offset={d0 - x:.6f},format=yuv420p",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", vout])
    run([FF, "-y", "-i", a0, "-i", a1, "-filter_complex", f"acrossfade=d={x:.6f}:c1=tri:c2=tri",
         "-c:a", "pcm_s16le", aout])


def concat(parts, dst, tmp, tag):
    if len(parts) == 1:
        shutil.copy(parts[0], dst)
        return
    listf = os.path.join(tmp, f"list_{tag}.txt")
    with open(listf, "w") as fh:
        for p in parts:
            fh.write(f"file '{p}'\n")
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", listf, "-c", "copy", dst])


def main():
    ap = argparse.ArgumentParser(description="plan.json → frame-accurate cut")
    ap.add_argument("plan", help="Path to the plan.json")
    ap.add_argument("--out-dir", default=None, help="Target folder (default: next to the plan.json)")
    args = ap.parse_args()

    if FF is None:
        fail("ffmpeg not found: run setup/install.sh.")

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)

    name = plan["name"]
    if name != name.lower():
        print(f"⚠ Name '{name}' forced to lowercase (macOS is case-insensitive).")
        name = name.lower()

    src = plan["source"]
    if not os.path.exists(src):
        fail(f"Source not found: {src}")

    fmt = str(plan.get("format", "916"))
    if fmt not in FORMATS:
        fail(f"Unknown format '{fmt}'. Allowed: {', '.join(FORMATS)}.")

    fps = int(plan.get("fps", 30))
    speed = float(plan.get("speed", 1.0))
    fit = plan.get("fit", "pad")
    crop_x = plan.get("crop_x")
    segments = plan["segments"]
    xfades = {str(k): float(v) for k, v in (plan.get("xfade") or {}).items()}
    if not segments:
        fail("No segments in the plan.")
    if speed != 1.0 and not (0.5 <= speed <= 2.0):
        fail("speed must be between 0.5 and 2.0.")

    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.plan))
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, f"{name}.mp4")

    vf = vf_for(fmt, fit, crop_x, fps)
    tmp = tempfile.mkdtemp(prefix=f"cut_{name}_")
    try:
        # 1. Segments one by one: video exactly N frames, audio as PCM exactly N/fps seconds
        pcm = os.path.join(tmp, "source.wav")
        decode_audio(src, pcm)
        vparts, aparts, durs = [], [], []
        for i, (s, e) in enumerate(segments):
            start, frames = frame_grid(float(s), float(e), fps)
            vp, apart = os.path.join(tmp, f"seg{i:02d}.mp4"), os.path.join(tmp, f"seg{i:02d}.wav")
            print(f"→ Segment {i + 1}/{len(segments)}: {float(s):.2f}s – {float(e):.2f}s")
            cut_segment(src, pcm, start, frames, fps, vp, apart, vf)
            x = round(xfades.get(str(i - 1), 0) * fps) / fps
            if i and x:
                vm, am = os.path.join(tmp, f"xf{i:02d}.mp4"), os.path.join(tmp, f"xf{i:02d}.wav")
                print(f"  ↳ Cross-fade {x:.3f}s from segment {i}")
                xfade_pair(vparts[-1], aparts[-1], durs[-1], vp, apart, x, vm, am)
                vparts[-1], aparts[-1], durs[-1] = vm, am, durs[-1] + frames / fps - x
                continue
            vparts.append(vp)
            aparts.append(apart)
            durs.append(frames / fps)

        # 2. Concat separately (video stream copy, audio PCM, sample-accurate), then mux
        jv, ja = os.path.join(tmp, "joined_v.mp4"), os.path.join(tmp, "joined_a.wav")
        concat(vparts, jv, tmp, "v")
        concat(aparts, ja, tmp, "a")
        joined = os.path.join(tmp, "joined.mov")
        run([FF, "-y", "-i", jv, "-i", ja, "-map", "0:v", "-map", "1:a", "-c", "copy", joined])

        # 3. Optional: speed AFTER the concat
        staged = joined
        if speed != 1.0:
            sped = os.path.join(tmp, "sped.mp4")
            print(f"→ Speed {speed}× (setpts/atempo)")
            run([
                FF, "-y", "-i", staged,
                "-vf", f"setpts=PTS/{speed},fps={fps}",
                "-af", f"atempo={speed}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2",
                "-movflags", "+faststart", sped,
            ])
            staged = sped

        # 4. Gentle loudness (one-pass), the video stays untouched
        print("→ Loudness normalisation (loudnorm, one-pass, gentle)")
        run([
            FF, "-y", "-i", staged,
            "-c:v", "copy",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", dst,
        ])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    kept = (sum(float(e) - float(s) for s, e in segments) - sum(xfades.values())) / speed
    w, h = FORMATS[fmt]
    print(f"✓ {os.path.basename(dst)}  ({kept:.1f}s, {len(segments)} segments, {w}x{h}@{fps})")
    print(f"  → now check: tools/verify_head.sh {dst}")


if __name__ == "__main__":
    main()
