#!/usr/bin/env python3
"""Build 'The Boy Who Didn't Listen' — cinematic animatic episode."""
import os, subprocess, re, wave, sys, math
import numpy as np
import imageio_ffmpeg
from mutagen.mp3 import MP3
from PIL import Image, ImageDraw, ImageFont, ImageOps

FF = imageio_ffmpeg.get_ffmpeg_exe()
BASE = "/home/user/ep2"
IMG, VO, SEG = f"{BASE}/assets/img", f"{BASE}/assets/vo", f"{BASE}/assets/segments"
os.makedirs(SEG, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def run(cmd, tag, stdin_data=None):
    with open(f"{SEG}/log_{tag}.txt", "w") as f:
        p = subprocess.run(cmd, stdin=subprocess.PIPE if stdin_data is not None else None,
                           input=stdin_data, stdout=f, stderr=f, text=False)
    if p.returncode != 0:
        print(f"FAILED [{tag}]"); print(open(f"{SEG}/log_{tag}.txt").read()[-1500:]); sys.exit(1)

def dur_mp3(p): return MP3(p).info.length
def dur_any(p):
    if p.endswith(".mp3"): return MP3(p).info.length
    with wave.open(p) as w: return w.getnframes()/w.getframerate()
def probe_dur(p):
    r = subprocess.run([FF, "-i", p], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3)) if m else None

def text_on(img_path, out_path, lines, yfs, sizes, fills, stroke=6):
    im = Image.open(img_path).convert("RGB"); W, H = im.size
    d = ImageDraw.Draw(im)
    for line, yf, size, fill in zip(lines, yfs, sizes, fills):
        f = ImageFont.truetype(FONT, size)
        bb = d.textbbox((0,0), line, font=f, stroke_width=stroke)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        d.text(((W-tw)/2-bb[0], H*yf-th/2-bb[1]), line, font=f, fill=fill,
               stroke_width=stroke, stroke_fill=(18,18,18))
    im.save(out_path, quality=93); print("text ->", out_path)

# ---------- pre-render titles ----------
text_on(f"{IMG}/s1.png", f"{IMG}/s1_title.png",
        ["THE BOY WHO", "DIDN'T LISTEN", "A life lesson every child must watch"],
        [0.38, 0.465, 0.555], [int(1376*0.075), int(1376*0.075), int(1376*0.032)],
        ["white", "white", (255,205,40)])
text_on(f"{IMG}/s9.png", f"{IMG}/s9_end.png",
        ["LISTEN. BECAUSE THEY LOVE YOU.", "❤  SUBSCRIBE FOR MORE STORIES"],
        [0.85, 0.925], [int(1376*0.045), int(1376*0.032)], ["white", (255,205,40)])

th = Image.open(f"{IMG}/thumbnail.png").convert("RGB")
th = ImageOps.fit(th, (1280,720), Image.LANCZOS)
d = ImageDraw.Draw(th)
for line, yf, size, fill, st in [("THE BOY WHO", 0.14, 88, "white", 8),
                                  ("DIDN'T LISTEN", 0.24, 88, (255,205,40), 8),
                                  ("A LIFE LESSON ❤", 0.87, 40, "white", 6)]:
    f = ImageFont.truetype(FONT, size)
    bb = d.textbbox((0,0), line, font=f, stroke_width=st)
    tw, thh = bb[2]-bb[0], bb[3]-bb[1]
    d.text(((1280-tw)/2-bb[0], 720*yf-thh/2-bb[1]), line, font=f, fill=fill,
           stroke_width=st, stroke_fill=(18,18,18))
th.save(f"{BASE}/thumbnail-episode-02.jpg", quality=92)
print("thumbnail done")

# ---------- rain video generator ----------
def make_rain(dur, heavy, lightning_offsets, tag):
    frames = int(dur*25); fps = 25
    lightning_offsets = [o for o in lightning_offsets if 0.5 < o < dur - 1.5]
    rng = np.random.default_rng(42)
    nstreaks = 420 if heavy else 160
    out = f"{SEG}/rain_{tag}.mp4"
    cmd = [FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "ultrafast",
           "-crf", "26", "-pix_fmt", "yuv420p", out]
    with open(f"{SEG}/log_rain_{tag}.txt", "w") as f:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=f, stderr=f)
        for i in range(frames):
            arr = np.zeros((1080, 1920, 3), dtype=np.uint8)
            if any(abs(i - int(o*25)) <= 1 for o in lightning_offsets):
                arr[:] = 255
            else:
                for _ in range(nstreaks):
                    x = int(rng.integers(0, 1920)); y = int(rng.integers(-200, 1080))
                    ln = int(rng.integers(30, 90)); wd = int(rng.integers(1, 3))
                    gr = int(rng.integers(120, 190))
                    y0, y1 = max(0,y), min(1080, y+ln+4)
                    x0, x1 = max(0,x), min(1920, x+wd)
                    if y1 > y0 and x1 > x0:
                        arr[y0:y1, x0:x1, :] = np.maximum(
                            arr[y0:y1, x0:x1, :],
                            np.array([gr, gr, gr+15], dtype=np.uint8).reshape(1,1,3))
            p.stdin.write(arr.tobytes())
        p.stdin.close()
        p.wait()
    if p.returncode != 0:
        print(f"FAILED [rain_{tag}]"); print(open(f"{SEG}/log_rain_{tag}.txt").read()[-1200:]); sys.exit(1)
    return out

# ---------- segment builder ----------
def build_segment(img, wavs, idx, lead, tail, mode, rain_info=None):
    tot_vo = sum(dur_any(w) for w in wavs)
    gap = 0.6 if len(wavs) > 1 else 0.0
    dur = lead + tot_vo + gap*(len(wavs)-1) + tail
    frames = int(round(dur*25))
    x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    if mode == "pushin":  z = "min(zoom+0.0011,1.35)"
    elif mode == "pullout": z = "if(lte(on,1),1.35,max(1.001,zoom-0.0011))"
    elif mode == "slowzoom": z = "min(zoom+0.0005,1.25)"
    elif mode == "panright":
        z = "1.18"; x = f"(iw-iw/zoom)*on/{frames-1}"
    elif mode == "panleft":
        z = "1.18"; x = f"(iw-iw/zoom)*(1-on/{frames-1})"
    else: z = "1.10"
    vf = (f"scale=2400:1350:force_original_aspect_ratio=increase,crop=2400:1350,"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1920x1080:fps=25")
    seg = f"{SEG}/seg{idx:02d}.mp4"
    run([FF, "-y", "-framerate", "25", "-i", img, "-vf", vf, "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-pix_fmt", "yuv420p", seg], f"seg{idx}")
    if rain_info:
        heavy, lgt = rain_info
        rv = make_rain(dur, heavy, lgt, f"{idx:02d}")
        out = f"{SEG}/seg{idx:02d}_r.mp4"
        run([FF, "-y", "-i", seg, "-i", rv,
             "-filter_complex", "[0:v][1:v]blend=all_mode=screen,format=yuv420p[v]",
             "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", out], f"seg{idx}r")
        os.replace(out, seg)
    # audio
    parts = []
    a = f"{SEG}/lead{idx}.wav"
    run([FF, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{lead:.3f}", "-c:a", "pcm_s16le", a], f"lead{idx}")
    parts.append(a)
    for j, w in enumerate(wavs):
        wv = f"{SEG}/vo_{idx}_{j}.wav"
        run([FF, "-y", "-i", w, "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", wv], f"voconv{idx}_{j}")
        parts.append(wv)
        if j < len(wavs)-1:
            g = f"{SEG}/gap{idx}_{j}.wav"
            run([FF, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{gap:.3f}", "-c:a", "pcm_s16le", g], f"gap{idx}_{j}")
            parts.append(g)
    b = f"{SEG}/tail{idx}.wav"
    run([FF, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{tail:.3f}", "-c:a", "pcm_s16le", b], f"tail{idx}")
    parts.append(b)
    lst = f"{SEG}/alist{idx}.txt"
    with open(lst, "w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    aseg = f"{SEG}/aseg{idx:02d}.wav"
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:a", "pcm_s16le", aseg], f"aseg{idx}")
    return dur, seg, aseg

# ---------- plan ----------
XF = 0.7
plan = [
    ("s1_title.png", ["N1.mp3"],  1.5, 1.2, "pullout",  None),
    ("s2.png",       ["N2a.mp3"], 0.8, 0.8, "pushin",   None),
    ("s3.png",       ["N2b.mp3"], 0.8, 0.8, "panright", None),
    ("s4.png",       ["N3.mp3"],  0.8, 1.0, "pushin",   None),
    ("s5.png",       ["N4.mp3"],  0.8, 1.2, "slowzoom", None),
    ("s6.png",       ["N5.mp3"],  1.0, 1.0, "pushin",   (True,  [2.0, 15.5])),
    ("s7.png",       ["M1.mp3"],  1.0, 1.0, "panright", (True,  [2.0])),
    ("s8.png",       ["N6.mp3", "M2.mp3"], 0.8, 1.2, "pushin", (False, [12.0, 16.0])),
    ("s9_end.png",   ["N7.mp3"],  1.0, 2.5, "pullout",  None),
]

seg_paths, durs, asegs, starts = [], [], [], []
idx = 0; cum = 0.0
for i, (img, vos, lead, tail, mode, rain) in enumerate(plan):
    tail_eff = tail if i == len(plan)-1 else max(0.2, tail - XF)
    d, seg, asg = build_segment(f"{IMG}/{img}", [f"{VO}/{v}" for v in vos], idx, lead, tail_eff, mode, rain)
    seg_paths.append(seg); durs.append(d); asegs.append(asg); starts.append(cum)
    print(f"seg{idx:02d}: {img:16s} {d:6.1f}s  start={cum:6.1f}")
    cum += d; idx += 1
def concat_group(idxs, tag):
    fc, prev, off = [], "0:v", 0.0
    for k in range(1, len(idxs)):
        off += durs[idxs[k-1]] - XF
        o = f"g{k}"
        fc.append(f"[{prev}][{k}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[{o}]")
        prev = o
    inputs = [x for i in idxs for x in ("-i", seg_paths[i])]
    run([FF, "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{prev}]",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-pix_fmt", "yuv420p",
         "-r", "25", f"{SEG}/{tag}.mp4"], tag)
    return probe_dur(f"{SEG}/{tag}.mp4")

n = len(seg_paths)
da = concat_group(list(range(n//2)), "partA")
db = concat_group(list(range(n//2, n)), "partB")
L = da + db - XF
fc = (f"[0:v][1:v]xfade=transition=fade:duration={XF}:offset={da-XF:.3f}"
      f"[vx];[vx]fade=t=in:st=0:d=0.8,fade=t=out:st={max(0,L-1.2):.3f}:d=1.2,format=yuv420p[vout]")
run([FF, "-y", "-i", f"{SEG}/partA.mp4", "-i", f"{SEG}/partB.mp4", "-filter_complex", fc,
     "-map", "[vout]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
     "-r", "25", f"{SEG}/final_video.mp4"], "final_video")
print(f"video done {probe_dur(f'{SEG}/final_video.mp4'):.1f}s")

lst = f"{SEG}/amaster.txt"
with open(lst, "w") as f:
    for a in asegs: f.write(f"file '{a}'\n")
run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:a", "pcm_s16le", f"{SEG}/amaster.wav"], "audio")
print(f"audio done {probe_dur(f'{SEG}/amaster.wav'):.1f}s")

# music with real boundaries (5: playful_end, tension_end, dark_end, swell_end, resolve_start)
b1 = starts[2] - 2*XF; b2 = starts[3] - 3*XF; b3 = starts[4] - 4*XF
b4 = starts[6] - 6*XF; b5 = starts[8] - 8*XF
run([sys.executable, f"{BASE}/music_bed_lesson.py", f"{SEG}/music.wav",
     f"{L:.2f}", f"{b1:.2f}", f"{b2:.2f}", f"{b3:.2f}", f"{b4:.2f}", f"{b5:.2f}"], "music")
print(f"music done {probe_dur(f'{SEG}/music.wav'):.1f}s")

# freeze-pad video so audio outro isn't clipped (xfade shrinks video vs audio)
apad = max(0.0, probe_dur(f"{SEG}/amaster.wav") - probe_dur(f"{SEG}/final_video.mp4"))
run([FF, "-y", "-i", f"{SEG}/final_video.mp4",
     "-vf", f"tpad=stop_mode=clone:stop_duration={apad:.2f}",
     "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-r", "25",
     f"{SEG}/padded.mp4"], "pad")
L = probe_dur(f"{SEG}/amaster.wav")

out = f"{BASE}/episode-02-the-boy-who-didnt-listen.mp4"
run([FF, "-y", "-i", f"{SEG}/padded.mp4", "-i", f"{SEG}/amaster.wav", "-i", f"{SEG}/music.wav",
     "-filter_complex",
     "[1:a]aresample=44100,asplit=2[v1][v2];[2:a]aresample=44100,volume=0.85[mus];"
     "[mus][v1]sidechaincompress=threshold=0.02:ratio=8:attack=25:release=500[duck];"
     "[duck][v2]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]",
     "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
     "-movflags", "+faststart", "-t", f"{L:.3f}", out], "mux")
print(f"DONE {L:.1f}s = {int(L//60)}m {int(L%60)}s -> {out} {round(os.path.getsize(out)/1e6,1)} MB")
