#!/usr/bin/env python3
"""Frame-by-frame 2D cartoon animation demo: Ajapa walk cycle + flying birds + falling feathers."""
import math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

try:
    import imageio_ffmpeg
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "imageio-ffmpeg"])
    import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
BASE = os.path.dirname(os.path.abspath(__file__))
FR = os.path.join(BASE, "frames")
os.makedirs(FR, exist_ok=True)

W, H, FPS, DUR = 1280, 720, 25, 15
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
C_TURTLE = (146, 94, 48); C_TURTLE_DARK = (90, 58, 26)
C_TURTLE_PAT = (176, 124, 70)
C_LEG = (96, 128, 56); C_LEG_DARK = (70, 95, 42)
C_HEAD = (100, 134, 60)
FEATHER_COLORS = [(220, 60, 60), (60, 110, 220), (240, 200, 50), (90, 170, 90)]

def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def make_sky():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    top, bot = (120, 190, 235), (240, 218, 168)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=lerp(top, bot, y / H))
    return im

def draw_cloud(d, x, y, s):
    d.ellipse([x, y, x + 220 * s, y + 70 * s], fill=(255, 255, 255))
    d.ellipse([x + 40 * s, y - 22 * s, x + 150 * s, y + 40 * s], fill=(255, 255, 255))
    d.ellipse([x + 90 * s, y - 30 * s, x + 190 * s, y + 30 * s], fill=(255, 255, 255))

def draw_hills(d):
    d.ellipse([-300, 360, 700, 620], fill=(116, 152, 82))
    d.ellipse([500, 380, 1500, 640], fill=(116, 152, 82))
    d.ellipse([-400, 440, 900, 720], fill=(82, 132, 60))
    d.ellipse([600, 460, 1700, 740], fill=(82, 132, 60))
    d.rectangle([0, 620, W, H], fill=(60, 108, 50))
    # grass tufts
    for gx in range(20, W, 46):
        hgt = 14 + (gx * 7) % 18
        d.polygon([(gx, 718), (gx - 6, 700 - hgt), (gx + 6, 700 - hgt)], fill=(48, 92, 42))
        d.polygon([(gx + 20, 720), (gx + 14, 704 - hgt // 2), (gx + 26, 704 - hgt // 2)], fill=(48, 92, 42))

def draw_baobab(d):
    tx = 1090
    # trunk
    for i, (dy, wd) in enumerate([(560, 70), (590, 92), (625, 118), (655, 138), (690, 150)]):
        d.ellipse([tx - wd, dy - 30, tx + wd, dy + 30], fill=(122, 82, 44), outline=(86, 56, 28), width=4)
    for (bx, by, ang, ln, wd) in [(tx + 60, 585, -25, 110, 18), (tx - 55, 585, 200, 120, 18),
                                  (tx + 20, 560, -60, 80, 14), (tx - 30, 570, 55, 90, 14)]:
        ex = bx + ln * math.cos(math.radians(ang)); ey = by + ln * math.sin(math.radians(ang))
        d.line([(bx, by), (ex, ey)], fill=(110, 74, 40), width=wd)
        d.ellipse([ex - 20, ey - 16, ex + 20, ey + 16], fill=(96, 150, 70))

def draw_tortoise(phase, tilt):
    layer = Image.new("RGBA", (280, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = 140, 105
    swing = math.sin(phase) * 9
    leg_off = [(cx - 52, swing), (cx - 28, -swing), (cx + 30, -swing), (cx + 54, swing)]
    for lx, sw in leg_off:
        d.ellipse([lx + sw - 10, cy + 6, lx + sw + 10, cy + 36], fill=C_LEG, outline=C_LEG_DARK, width=3)
    d.polygon([(cx - 58, cy + 4), (cx - 78, cy - 2), (cx - 58, cy - 14)], fill=C_LEG_DARK)
    d.ellipse([cx - 62, cy - 54, cx + 62, cy + 26], fill=C_TURTLE, outline=C_TURTLE_DARK, width=5)
    for px in (-34, -6, 22):
        d.polygon([(cx + px, cy - 34), (cx + px + 14, cy - 22), (cx + px, cy - 10), (cx + px - 14, cy - 22)],
                  fill=C_TURTLE_PAT, outline=C_TURTLE_DARK, width=2)
    d.rounded_rectangle([cx - 64, cy + 8, cx + 64, cy + 26], radius=10, fill=(110, 70, 32), outline=(80, 50, 20), width=3)
    d.ellipse([cx + 44, cy - 42, cx + 96, cy - 2], fill=C_HEAD, outline=C_LEG_DARK, width=3)
    d.ellipse([cx + 72, cy - 28, cx + 82, cy - 18], fill=(255, 255, 255))
    d.ellipse([cx + 76, cy - 26, cx + 81, cy - 21], fill=(30, 30, 30))
    d.arc([cx + 62, cy - 22, cx + 84, cy - 6], start=20, end=120, fill=(30, 30, 30), width=3)
    return layer.rotate(tilt, expand=True, resample=Image.BICUBIC)

def draw_bird(c, wing_deg, mirror=False):
    layer = Image.new("RGBA", (130, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([36, 34, 92, 62], fill=c, outline=(40, 40, 40), width=2)
    d.polygon([(30, 46), (4, 38), (26, 58)], fill=c, outline=(40, 40, 40), width=2)
    d.ellipse([86, 24, 108, 46], fill=c, outline=(40, 40, 40), width=2)
    d.polygon([(104, 32), (124, 38), (104, 46)], fill=(255, 160, 40), outline=(40, 40, 40))
    d.ellipse([94, 30, 98, 34], fill=(30, 30, 30))
    wl = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wl)
    wd.ellipse([6, 26, 58, 52], fill=lerp(c, (20, 20, 20), 0.25), outline=(40, 40, 40), width=2)
    wl = wl.rotate(wing_deg, resample=Image.BICUBIC)
    layer.alpha_composite(wl, (34, 30))
    if mirror:
        layer = layer.transpose(Image.FLIP_LEFT_RIGHT)
    return layer

def draw_feather(x, y, ang, color):
    lay = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([4, 4, 36, 18], fill=color, outline=(30, 30, 30), width=2)
    d.line([(8, 11), (32, 11)], fill=(30, 30, 30), width=2)
    return lay.rotate(ang, resample=Image.BICUBIC)

font = ImageFont.truetype(FONT, 26)
frame_i = 0
for f in range(int(DUR * FPS)):
    t = f / FPS
    im = make_sky().convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # sun + glow
    for r, a in ((95, 40), (72, 70), (52, 255)):
        d.ellipse([1050 - r, 110 - r, 1050 + r, 110 + r], fill=(255, 222, 90, a))
    # clouds drift
    draw_cloud(d, (t * 22) % (W + 100) - 120, 80, 1.0)
    draw_cloud(d, (t * 14 + 500) % (W + 100) - 120, 150, 0.7)
    draw_cloud(d, (t * 9 + 900) % (W + 100) - 120, 55, 0.6)
    draw_hills(d)
    draw_baobab(d)
    im.alpha_composite(ov)
    # birds (flapping wings)
    b1x = -80 + (W + 200) * (t / DUR); b1y = 165 + 22 * math.sin(t * 0.9)
    b1 = draw_bird((230, 90, 90), math.sin(t * 11) * 55)
    im.alpha_composite(b1, (int(b1x), int(b1y)))
    b2x = W + 60 - (W + 220) * (t / DUR); b2y = 300 + 18 * math.sin(t * 1.2 + 2)
    b2 = draw_bird((70, 120, 220), math.sin(t * 9 + 1) * 55, mirror=True)
    im.alpha_composite(b2, (int(b2x), int(b2y)))
    # tortoise walks across
    px = 60 + (W - 360) * (t / DUR)
    ttl = draw_tortoise(phase=t * 4.5, tilt=math.sin(t * 4.5) * 4)
    im.alpha_composite(ttl, (int(px), 430))
    # falling feathers
    for i in range(8):
        fx = (i * 173 + t * 34) % (W - 60) + 30
        fy = (t * 46 + i * 82) % (H - 320) + 40
        sw = math.sin(t * 1.4 + i) * 22
        fth = draw_feather(fx + sw, fy, t * 80 + i * 45, FEATHER_COLORS[i % 4])
        im.alpha_composite(fth, (int(fx + sw) - 20, int(fy) - 10))
    im = im.convert("RGB")
    d2 = ImageDraw.Draw(im)
    d2.text((14, H - 44), "2D MOTION DEMO - Ajapa walk cycle | 25 fps | frame animation",
            font=font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(30, 30, 30))
    im.save(os.path.join(FR, f"f{f:04d}.jpg"), quality=90)
    frame_i += 1
    if frame_i % 75 == 0:
        print(f"frames {frame_i}/{int(DUR*FPS)}")

# encode
raw = os.path.join(BASE, "motion_raw.mp4")
subprocess.run([FF, "-y", "-framerate", str(FPS), "-i", os.path.join(FR, "f%04d.jpg"),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", raw],
               check=True, capture_output=True)
vo = os.path.join(BASE, "vo_demo.mp3")
out = os.path.join(BASE, "motion-demo.mp4")
if os.path.exists(vo):
    subprocess.run([FF, "-y", "-i", raw, "-i", vo,
                    "-filter_complex", "[1:a]adelay=600|600,apad[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-t", str(DUR), out], check=True, capture_output=True)
else:
    subprocess.run([FF, "-y", "-i", raw, "-c", "copy", out], check=True, capture_output=True)
print("DONE", out)
