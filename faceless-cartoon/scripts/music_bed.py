#!/usr/bin/env python3
"""Synthesize an original cinematic 'African folktale' music bed (100% royalty-free, code-made).
Layers: warm pads, kalimba-style plucks (A-minor pentatonic), soft shaker, kick, riser intro, fade outro.
Usage: python3 music_bed.py <out.wav> [seconds]
"""
import numpy as np
import wave, os, sys

SR = 44100
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
OUT = sys.argv[1] if len(sys.argv) > 1 else "music_bed.wav"
N = int(SR * DUR)
t_all = np.arange(N) / SR

BEAT = 60.0 / 92.0          # 92 BPM
STEP = BEAT / 2.0           # 8th notes
SCALE = [440.0, 523.25, 587.33, 659.25, 783.99]   # A4 C5 D5 E5 G5 (A-minor pentatonic)
CHORDS = [[220.0, 261.63, 329.63],                 # Am
          [174.61, 220.00, 261.63],                # F
          [196.00, 261.63, 329.63],                # C/G feel
          [196.00, 220.00, 293.66]]                # G(add9) feel
NBARS = int(np.ceil(DUR / (BEAT * 4)))
BARPAT = [0, 2, 4, 1, 3, 2, 1, 4]                  # pluck pattern (scale indices)

mix = np.zeros(N)

def add(buf, t0):
    i0 = int(t0 * SR)
    if i0 >= N: return
    i1 = min(N, i0 + len(buf))
    mix[i0:i1] += buf[:i1 - i0]

def lowpass(x, fc=1200.0):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = a * acc + (1 - a) * x[i]
        y[i] = acc
    return y

# ---------- pads ----------
for b in range(NBARS):
    t0 = b * BEAT * 4
    nbar = int(BEAT * 4 * SR)
    tb = np.arange(nbar) / SR
    bar = np.zeros(nbar)
    for f in CHORDS[b % 4]:
        # detuned sine pair for warmth
        bar += np.sin(2 * np.pi * f * tb)
        bar += 0.45 * np.sin(2 * np.pi * f * 2 * tb)
        bar += 0.30 * np.sin(2 * np.pi * f * (1 + 0.003) * tb)
    env = np.sin(np.pi * np.clip(tb / 0.9, 0, 1)) ** 2          # soft attack
    env *= np.clip((nbar / SR - tb) / 0.8, 0, 1)                # release into next bar
    bar = lowpass(bar * env, 1100.0) * 0.16
    add(bar, t0)

# ---------- kalimba plucks ----------
rng = np.random.default_rng(7)
for b in range(NBARS):
    for s in range(8):
        t0 = b * BEAT * 4 + s * STEP
        f = SCALE[BARPAT[(b + s) % 8]] * (1.0 if (s % 4) else 2.0)  # octave on downbeats
        dur = 0.85
        tp = np.arange(int(dur * SR)) / SR
        vel = 0.75 + 0.25 * rng.random()
        sig = (np.sin(2 * np.pi * f * tp)
               + 0.40 * np.sin(2 * np.pi * f * 2.76 * tp)
               + 0.18 * np.sin(2 * np.pi * f * 5.40 * tp)) * np.exp(-tp / 0.16) * vel
        pan = 0.5 + 0.5 * np.sin(s * 1.7)   # simple pan by step
        add(sig * (1 - pan) * 0.22, t0)
        add(sig * pan * 0.22, t0 + 0.0)

# ---------- shaker (off-beats) ----------
for b in range(NBARS):
    for s in (1, 3, 5, 7):
        t0 = b * BEAT * 4 + s * STEP
        ns = int(0.05 * SR)
        noise = rng.standard_normal(ns)
        sh = np.diff(noise, prepend=0) * np.exp(-np.arange(ns) / (0.012 * SR))
        add(sh * 0.10, t0)

# ---------- soft kick (beats 1 & 3) ----------
for b in range(NBARS):
    for s in (0, 4):
        t0 = b * BEAT * 4 + s * STEP
        nk = int(0.18 * SR)
        tk = np.arange(nk) / SR
        f_sweep = 100 * np.exp(-tk / 0.05) + 44
        ph = 2 * np.pi * np.cumsum(f_sweep) / SR
        k = np.sin(ph) * np.exp(-tk / 0.09)
        add(k * 0.5, t0)

# ---------- cinematic riser (0-2.5s) ----------
nr = int(2.5 * SR)
tr = np.arange(nr) / SR
riser = (rng.standard_normal(nr) * (tr / 2.5) ** 3 * 0.22
         + 0.12 * np.sin(2 * np.pi * (200 + 600 * tr / 2.5) * tr))
add(riser, 0.0)

# ---------- master ----------
mix /= np.max(np.abs(mix)) + 1e-9
mix *= 0.85
# fade out last 2s
nf = int(2.0 * SR)
mix[-nf:] *= np.linspace(1, 0, nf)

stereo = np.stack([mix, mix], axis=1)
pcm = (stereo * 32767).astype(np.int16)
with wave.open(OUT, "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f"wrote {OUT}  {DUR}s  stereo 16-bit {SR}Hz")
