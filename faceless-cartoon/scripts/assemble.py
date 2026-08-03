#!/usr/bin/env python3
"""Assemble the faceless cartoon pilot episode (v2 — text pre-rendered via Pillow)."""
import os, subprocess, re, glob, wave
import imageio_ffmpeg
from mutagen.mp3 import MP3

FF = imageio_ffmpeg.get_ffmpeg_exe()
BASE = "/home/user/faceless-cartoon"
IMG, VO, SEG = f"{BASE}/assets/img", f"{BASE}/assets/vo", f"{BASE}/assets/segments"
os.makedirs(SEG, exist_ok=True)

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print("CMD FAILED:", " ".join(map(str, cmd))[:400])
        print(p.stderr[-2500:])
        raise SystemExit(1)
    return p

def dur_mp3(path): return MP3(path).info.length
def dur_wav(path):
    with wave.open(path) as w: return w.getnframes() / w.getframerate()

def silences(path, noise="-32dB", d=0.30):
    p = subprocess.run([FF, "-i", path, "-af", f"silencedetect=noise={noise}:d={d}",
                        "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    ends   = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    return [(s, e) for s, e in zip(starts, ends) if e - s >= 0.30]

def split_clip(path, n_chunks, prefix):
    total = dur_mp3(path)
    wins = silences(path)
    need = max(0, n_chunks - 1)
    pts = []
    if need:
        wins.sort(key=lambda w: (w[1]-w[0]), reverse=True)
        pts = sorted(round((s+e)/2, 3) for s, e in wins[:need])
        pts = [p for p in pts if 1.0 < p < total - 1.0]
        if len(pts) < need:
            pts = sorted(round(total*(i+1)/n_chunks, 3) for i in range(need))
    bounds = [0.0] + pts + [total]
    outs = []
    for i in range(len(bounds)-1):
        s, e = bounds[i], bounds[i+1]
        if e - s < 1.2: continue
        o = f"{prefix}_c{i}.wav"
        run([FF, "-y", "-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", path,
             "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", o])
        outs.append(o)
    return outs

def build_segment(img, wav, idx, lead, tail, zoom_in):
    adur = dur_wav(wav)
    dur = lead + adur + tail
    frames = int(round(dur * 25))
    z = "min(zoom+0.0009,1.28)" if zoom_in else "if(lte(on,1),1.28,max(1.001,zoom-0.0009))"
    vf = (f"scale=2400:1350:force_original_aspect_ratio=increase,crop=2400:1350,"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=25")
    seg = f"{SEG}/seg{idx:02d}.mp4"
    run([FF, "-y", "-framerate", "25", "-i", img, "-vf", vf, "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", seg])
    return dur, seg

def build_audio(wav, idx, lead, tail):
    a = f"{SEG}/sil{idx}a.wav"; b = f"{SEG}/sil{idx}b.wav"
    run([FF, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{lead:.3f}", "-c:a", "pcm_s16le", a])
    run([FF, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{tail:.3f}", "-c:a", "pcm_s16le", b])
    lst = f"{SEG}/alist{idx}.txt"
    with open(lst, "w") as f:
        for p in (a, wav, b): f.write(f"file '{p}'\n")
    out = f"{SEG}/aseg{idx:02d}.wav"
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:a", "pcm_s16le", out])
    return out

# ---- plan: (vo clip, n_chunks, images for chunks, lead, tail, zoom_in) ----
plan = [
    ("vo1.mp3", 2, ["00_title_card.png",      "01_tortoise_grass.png"], 2.0, 1.0, False),
    ("vo2.mp3", 3, ["02_king_bird.png",       "03_feathers_wings.png", "04_flying.png"], 0.6, 1.0, True),
    ("vo3.mp3", 1, ["05_sky_feast.png"],                              0.6, 1.0, False),
    ("vo4.mp3", 1, ["06_eating_all.png"],                             0.6, 1.0, True),
    ("vo5.mp3", 2, ["07_feathers_back.png",   "08_falling.png"],      0.6, 1.0, False),
    ("vo6.mp3", 2, ["09_cracked_shell.png",   "00_end_card.png"],     0.8, 2.0, True),
]

seg_paths, durs, audio_parts = [], [], []
idx = 0
for vo, nch, imgs, lead, tail, zin in plan:
    chunks = split_clip(f"{VO}/{vo}", nch, f"{SEG}/{vo[:-4]}")
    if len(chunks) < len(imgs): imgs = imgs[:len(chunks)]
    else:
        while len(imgs) < len(chunks): imgs.append(imgs[-1])
    for wav, im in zip(chunks, imgs):
        d, seg = build_segment(f"{IMG}/{im}", wav, idx, lead, tail, zin)
        seg_paths.append(seg); durs.append(d)
        audio_parts.append(build_audio(wav, idx, lead, tail))
        print(f"seg{idx:02d}: {im:26s} {d:6.1f}s  ({os.path.basename(wav)})")
        idx += 1

# ---- concat video with crossfades ----
XF = 0.7
fc, prev, off = [], "0:v", 0.0
for i in range(1, len(seg_paths)):
    off += durs[i-1] - XF
    out = f"v{i}"
    fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[{out}]")
    prev = out
L = sum(durs) - XF * (len(seg_paths) - 1)
fc.append(f"[{prev}]fade=t=in:st=0:d=0.8,fade=t=out:st={max(0,L-1.1):.3f}:d=1.1,format=yuv420p[vout]")
inputs = [x for s in seg_paths for x in ("-i", s)]
run([FF, "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]", "-c:v", "libx264",
     "-preset", "medium", "-crf", "20", "-r", "25", f"{SEG}/video_concat.mp4"])

# ---- concat audio ----
lst = f"{SEG}/amaster.txt"
with open(lst, "w") as f:
    for a in audio_parts: f.write(f"file '{a}'\n")
run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:a", "pcm_s16le", f"{SEG}/audio_master.wav"])

# ---- mux ----
out = f"{BASE}/pilot-episode-01.mp4"
run([FF, "-y", "-i", f"{SEG}/video_concat.mp4", "-i", f"{SEG}/audio_master.wav",
     "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
     "-movflags", "+faststart", "-t", f"{L:.3f}", out])

print(f"\nDONE. Total length: {L:.1f}s = {int(L//60)}m {int(L%60)}s")
print("FINAL:", out, round(os.path.getsize(out)/1e6, 1), "MB")
