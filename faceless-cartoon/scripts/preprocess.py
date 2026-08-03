#!/usr/bin/env python3
"""Render title/end-card text onto images with Pillow (ffmpeg build lacks drawtext)."""
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

BASE = "/home/user/faceless-cartoon"
IMG = f"{BASE}/assets/img"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def text_img(src, dst, lines, y_fracs, sizes, fills):
    """lines: list of strings; sizes/fills per line; y_fracs: vertical center fraction of canvas."""
    im = Image.open(src).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    for line, yf, size, fill in zip(lines, y_fracs, sizes, fills):
        f = ImageFont.truetype(FONT, size)
        stroke = max(4, int(W * 0.005))
        bbox = d.textbbox((0, 0), line, font=f, stroke_width=stroke)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (W - tw) / 2 - bbox[0]
        y = H * yf - th / 2 - bbox[1]
        d.text((x, y), line, font=f, fill=fill, stroke_width=stroke, stroke_fill=(20, 20, 20))
    im.save(dst, quality=92)
    print("wrote", dst, im.size)

# --- Title card (from savanna bg) ---
text_img(f"{IMG}/00_title_bg.png", f"{IMG}/00_title_card.png",
         ["Why the Tortoise Has a Cracked Shell", "An African Folktale"],
         [0.42, 0.42], [int(1376*0.062), int(1376*0.038)], ["white", (255, 205, 40)])

# --- End card ---
text_img(f"{IMG}/00_title_bg.png", f"{IMG}/00_end_card.png",
         ["The End", "Subscribe for more African Folktales"],
         [0.44, 0.44], [int(1376*0.085), int(1376*0.038)], ["white", (255, 205, 40)])

# --- Thumbnail 1280x720 ---
im = Image.open(f"{IMG}/04_flying.png").convert("RGB")
im = ImageOps.fit(im, (1280, 720), Image.LANCZOS)
d = ImageDraw.Draw(im)
for line, yf, size, fill in [("WHY IS HIS SHELL", 0.30, 84, "white"),
                             ("CRACKED?", 0.30, 84, (255, 205, 40)),
                             ("African Folktale for Kids", 0.62, 34, "white")]:
    f = ImageFont.truetype(FONT, size)
    bbox = d.textbbox((0, 0), line, font=f, stroke_width=7)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (1280 - tw) / 2 - bbox[0]
    y = 720 * yf - th / 2 - bbox[1]
    d.text((x, y), line, font=f, fill=fill, stroke_width=7, stroke_fill=(20, 20, 20))
im.save(f"{BASE}/thumbnail.jpg", quality=92)
print("wrote thumbnail.jpg 1280x720")
