#!/usr/bin/env python3
"""Emotional score for 'The Boy Who Didn't Listen'.
Sections: warm intro -> playful -> tension -> dark rain (noise+thunder) -> emotional swell -> resolve.
Usage: python3 music_bed_lesson.py <out.wav> <total_sec> <warm_end> <playful_end> <tension_end> <dark_end> <swell_end>
"""
import numpy as np, wave, sys

SR = 44100
DUR = float(sys.argv[2]); OUT = sys.argv[1]
B = [0.0] + [float(x) for x in sys.argv[3:8]] + [DUR]   # 6 sections: warm, playful, tension, dark, swell, resolve
NAMES = ["warm", "playful", "tension", "dark", "swell", "resolve"]

N = int(SR * DUR)
t_all = np.arange(N) / SR
mix = np.zeros(N)
rng = np.random.default_rng(11)

def add(buf, t0):
    i0 = int(t0 * SR)
    if i0 >= N: return
    i1 = min(N, i0 + len(buf))
    mix[i0:i1] += buf[:i1 - i0]

def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = a * acc + (1 - a) * x[i]; y[i] = acc
    return y

def highpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x)
    prev_x = prev_y = 0.0
    for i in range(len(x)):
        y[i] = a * (prev_y + x[i] - prev_x); prev_x, prev_y = x[i], y[i]
    return y

BEAT = 60.0 / 90.0
PLUCK = [523.25, 659.25, 783.99, 880.0, 1046.5]   # C5 D5 G5 A5 C6
PADW = {"Am": [220.0, 261.63, 329.63], "F": [174.61, 220.0, 261.63],
        "C": [196.0, 261.63, 329.63], "G": [196.0, 220.0, 293.66],
        "Em": [164.81, 196.0, 246.94], "E": [164.81, 207.65, 246.94]}

def pads(t0, t1, chord, vol, attack=1.2, release=1.5):
    n = int((t1 - t0) * SR); tb = np.arange(n) / SR
    buf = np.zeros(n)
    for f in PADW[chord]:
        buf += np.sin(2*np.pi*f*tb) + 0.4*np.sin(2*np.pi*f*2*tb) + 0.35*np.sin(2*np.pi*f*1.005*tb)
    env = np.clip(tb/attack, 0, 1) * np.clip((n/SR - tb)/release, 0, 1)
    add(lowpass(buf*env, 900)*vol, t0)

def plucks(t0, t1, scale, step, vel0=0.6, vol=0.16, oct_on_beat=True):
    nsteps = int((t1 - t0) / step)
    for s in range(nsteps):
        st = t0 + s*step
        f = scale[(s) % len(scale)] * (2.0 if (oct_on_beat and s % 4 == 0) else 1.0)
        tp = np.arange(int(0.9*SR)) / SR
        sig = (np.sin(2*np.pi*f*tp) + 0.4*np.sin(2*np.pi*f*2.76*tp) + 0.15*np.sin(2*np.pi*f*5.4*tp))
        add(sig*np.exp(-tp/0.15)*vel0*vol, st)

def bass_pulse(t0, t1, vol=0.30):
    t = t0
    while t < t1:
        nk = int(0.25*SR); tk = np.arange(nk)/SR
        fs = 90*np.exp(-tk/0.05) + 38
        k = np.sin(2*np.pi*np.cumsum(fs)/SR)*np.exp(-tk/0.12)
        add(k*vol, t); t += BEAT*2

def shaker(t0, t1, vol=0.08):
    t = t0 + BEAT/2
    while t < t1:
        ns = int(0.04*SR); sh = np.diff(rng.standard_normal(ns), prepend=0)*np.exp(-np.arange(ns)/(0.012*SR))
        add(sh*vol, t); t += BEAT

def riser(t0, dur=3.0, vol=0.20):
    n = int(dur*SR); tr = np.arange(n)/SR
    add((rng.standard_normal(n)*(tr/dur)**3*vol + 0.1*np.sin(2*np.pi*(150+450*tr/dur)*tr)), t0)

def rain(t0, t1, vol=0.30):
    n = int((t1-t0)*SR)
    noise = rng.standard_normal(n)
    bp = highpass(lowpass(noise, 2600), 250)
    am = 0.7 + 0.3*np.sin(2*np.pi*0.5*t_all[:n] + rng.random()*6)
    add(bp*am*vol, t0)

def thunder(t0, vol=0.55):
    n = int(4.0*SR); tt = np.arange(n)/SR
    noise = rng.standard_normal(n)
    body = lowpass(noise, 220)*np.exp(-tt/0.9)
    boom = np.sin(2*np.pi*38*tt)*np.exp(-tt/1.4)
    add((body*0.8 + boom)*vol, t0)

# ---- build sections ----
s = 0
def sec(i):
    global s; s = i; return B[i], B[i+1]

t0, t1 = sec(0)   # warm intro (Am)
pads(t0, t1, "Am", 0.14); plucks(t0, t1, [261.63, 329.63, 392.0], BEAT/2, 0.5, 0.14, False)
shaker(t0, t1, 0.05)

t0, t1 = sec(1)   # playful
pads(t0, t1, "C", 0.11); plucks(t0, t1, PLUCK, BEAT/2, 0.6, 0.15)
bass_pulse(t0, t1, 0.22); shaker(t0, t1, 0.08)

t0, t1 = sec(2)   # tension (market/lost)
pads(t0, t1, "Em", 0.13); bass_pulse(t0, t1, 0.30)
plucks(t0, t1, [329.63, 392.0, 493.88, 587.33], BEAT, 0.4, 0.10)
riser(t1-3.0, 3.0, 0.22)

t0, t1 = sec(3)   # dark rain (Em drone + rain + thunder)
pads(t0, t1, "Em", 0.16, attack=3.0, release=3.0)
rain(t0, t1, 0.30)
thunder(t0+4.0, 0.5); thunder(t0+20.0, 0.45); thunder(t0+24.0, 0.4)
bass_pulse(t0, t1, 0.18)

t0, t1 = sec(4)   # emotional swell (F -> Am warm, wide, light rain fading)
pads(t0, t0+(t1-t0)*0.5, "F", 0.17, attack=2.5, release=2.0)
pads(t0+(t1-t0)*0.5, t1, "Am", 0.17, attack=2.5, release=2.0)
plucks(t0, t1, [261.63, 329.63, 440.0, 523.25], BEAT, 0.5, 0.10)
rain(t0, t1, 0.12)

t0, t1 = sec(5)   # resolve (C major bright, fade)
pads(t0, t1, "C", 0.15, attack=2.0, release=3.0)
plucks(t0, t1, PLUCK, BEAT/2, 0.6, 0.13)

# master
mix /= np.max(np.abs(mix)) + 1e-9
mix *= 0.85
nf = int(2.5*SR); mix[-nf:] *= np.linspace(1, 0, nf)
stereo = np.stack([mix, mix], 1)
pcm = (stereo*32767).astype(np.int16)
with wave.open(OUT, "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print(f"wrote {OUT} {DUR:.1f}s sections={NAMES}")
