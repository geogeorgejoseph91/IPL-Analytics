import os, math, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1920, 1080
FPS           = 30
DURATION      = 2
TOTAL_FRAMES  = FPS * DURATION

FFMPEG       = r"C:\Users\HP\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
DIR          = r"C:\Users\HP\works\Learning\Luminar\powerbi\projects2\Geo George_Jan_2026 - Copy"
FRAMES_DIR   = os.path.join(DIR, "loader_frames")
LOADER_PATH  = os.path.join(DIR, "loader.mp4")
LOADER_AUDIO = os.path.join(DIR, "loader_audio.mp4")
FINAL        = os.path.join(DIR, "Geo_George_PowerBI_Presentation.mp4")
PRESENTATION = os.path.join(DIR, "presentation.mp4")
IPL          = os.path.join(DIR, "IPL_dashboard.mp4")
LOGO_PATH    = os.path.join(DIR, "powerbi_logo.png")

os.makedirs(FRAMES_DIR, exist_ok=True)

GOLD     = (210, 155,   0)
GOLD_DIM = (235, 205, 110)
GRAY     = ( 75,  75,  75)
GRAY_LT  = (210, 210, 210)
BG       = (255, 255, 255)

def load_font(candidates, size):
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

font_sub = load_font([
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
], 34)

# ── Split logo into text half and icon half ──────────────────────────────────
# Gap detected at x=181-199 in the 320x320 original → split at x=190
_raw_logo   = Image.open(LOGO_PATH).convert("RGBA")
ORIG_W      = _raw_logo.width          # 320
ORIG_SPLIT  = 190                      # gap midpoint in original pixels

LOGO_W      = 400
LOGO_H      = int(LOGO_W * _raw_logo.height / ORIG_W)
_logo_full  = _raw_logo.resize((LOGO_W, LOGO_H), Image.LANCZOS)

LOGO_SPLIT  = int(ORIG_SPLIT * LOGO_W / ORIG_W)   # ≈ 237 in scaled logo

_logo_text  = _logo_full.crop((0,          0, LOGO_SPLIT, LOGO_H))   # "Power BI" text
_logo_icon  = _logo_full.crop((LOGO_SPLIT, 0, LOGO_W,     LOGO_H))   # bar chart icon


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3

def ease_out_quart(x):
    return 1 - (1 - x) ** 4

def apply_alpha(img_rgba, a):
    r, g, b, ch = img_rgba.split()
    ch = ch.point(lambda p: int(p * a / 255))
    return Image.merge("RGBA", (r, g, b, ch))

def paste_part(base_rgb, part_rgba, x, y):
    """Paste RGBA part onto RGB base using part's alpha as mask."""
    base_rgb.paste(part_rgba.convert("RGB"), (x, y), part_rgba.split()[3])


def draw_circles(draw, cx, y, t):
    """5 circle indicators that fill bottom-up, left to right."""
    n       = 5
    r       = 18             # radius
    dia     = r * 2
    gap     = 20
    total_w = n * dia + (n - 1) * gap
    x0      = cx - total_w // 2
    wave    = t / DURATION

    for i in range(n):
        fill_start = i / n
        local      = (wave - fill_start) / (1.0 / n)
        fill       = ease_out_quart(max(0.0, min(1.0, local)))
        sx         = x0 + i * (dia + gap)
        sy         = y
        fill_h     = int(dia * fill)

        if fill_h > 0:
            # gold filled circle (full)
            r_val = int(GOLD[0] + (GOLD_DIM[0] - GOLD[0]) * fill)
            g_val = int(GOLD[1] + (GOLD_DIM[1] - GOLD[1]) * fill)
            b_val = int(GOLD[2] + (GOLD_DIM[2] - GOLD[2]) * fill)
            draw.ellipse([sx, sy, sx + dia, sy + dia],
                         fill=(r_val, g_val, b_val))
            # white rectangle erases the unfilled top portion
            unfill_bot = sy + dia - fill_h
            if unfill_bot > sy:
                draw.rectangle([sx - 1, sy - 1, sx + dia + 1, unfill_bot],
                               fill=BG)
        else:
            # empty circle interior
            draw.ellipse([sx + 2, sy + 2, sx + dia - 2, sy + dia - 2],
                         fill=(248, 248, 248))

        # circle outline always on top (restores crisp edge)
        draw.ellipse([sx, sy, sx + dia, sy + dia],
                     outline=GRAY_LT, width=2)


def make_frame(i):
    t   = i / FPS
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)

    cx       = WIDTH  // 2
    logo_y   = HEIGHT // 2 - LOGO_H // 2 - 50   # logo top-edge y
    sub_y    = HEIGHT // 2 + LOGO_H // 2 + 20
    sq_y     = sub_y + 55

    # Logo left-edge x so the full logo is centered
    logo_x   = cx - LOGO_W // 2

    # ── Text part: fades in first (0 → 0.28 s) ───────────────────────────
    T_END   = 0.28
    t_ease  = ease_out_cubic(min(t / T_END, 1.0))
    t_alpha = int(255 * t_ease)

    if t_alpha > 0:
        tw, th   = _logo_text.size
        part     = apply_alpha(_logo_text, t_alpha)
        paste_part(img, part, logo_x, logo_y)

    # ── Icon part: fades in after text (0.22 → 0.50 s) ───────────────────
    I_START, I_END = 0.22, 0.50
    i_progress = max(0.0, (t - I_START) / (I_END - I_START))
    i_ease     = ease_out_cubic(min(i_progress, 1.0))
    i_alpha    = int(255 * i_ease)

    if i_alpha > 0:
        iw, ih   = _logo_icon.size
        # slight scale-in: 0.75 → 1.0
        i_scale  = 0.75 + 0.25 * i_ease
        niw      = max(1, int(iw * i_scale))
        nih      = max(1, int(ih * i_scale))
        icon_res = _logo_icon.resize((niw, nih), Image.LANCZOS)
        part     = apply_alpha(icon_res, i_alpha)
        # keep icon right-aligned to where it normally sits
        ix = logo_x + LOGO_SPLIT + (iw - niw) // 2
        iy = logo_y + (ih - nih) // 2
        paste_part(img, part, ix, iy)

    # ── "Loading IPL Analytics..." ────────────────────────────────────────
    draw    = ImageDraw.Draw(img)
    dot_cnt = int(t * 3) % 4
    sub     = "Loading IPL Analytics" + "." * dot_cnt + " " * (3 - dot_cnt)
    bb      = draw.textbbox((0, 0), sub, font=font_sub)
    tw2     = bb[2] - bb[0]
    sub_a   = int(255 * i_ease)
    draw.text((cx - tw2 // 2 - bb[0], sub_y - bb[1]),
              sub, font=font_sub, fill=(*GRAY, sub_a))

    # ── 5 circle indicators ───────────────────────────────────────────────
    draw_circles(draw, cx, sq_y, t)

    return img


# ── 1. Generate frames ──────────────────────────────────────────────────────
existing = len([f for f in os.listdir(FRAMES_DIR) if f.endswith(".png")])
if existing == TOTAL_FRAMES:
    print("Frames exist — delete loader_frames/ to regenerate.")
else:
    print(f"Generating {TOTAL_FRAMES} frames...")
    for i in range(TOTAL_FRAMES):
        make_frame(i).save(os.path.join(FRAMES_DIR, f"frame_{i:04d}.png"))
        if i % 10 == 0:
            print(f"  {i}/{TOTAL_FRAMES}")
    print("Done.")

# ── 2. Encode loader + silent audio ─────────────────────────────────────────
if not os.path.exists(LOADER_AUDIO):
    print("Encoding loader video...")
    subprocess.run([
        FFMPEG, "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(FRAMES_DIR, "frame_%04d.png"),
        "-c:v", "libx264", "-crf", "16", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        LOADER_PATH,
    ], check=True)

    print("Adding silent audio...")
    subprocess.run([
        FFMPEG, "-y",
        "-i", LOADER_PATH,
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        LOADER_AUDIO,
    ], check=True)
else:
    print("Loader audio exists — skipping encode.")

# ── 3. Combine: presentation → fadewhite → loader → fadewhite → IPL ─────────
print("Combining videos...")
PRES_DUR  = 21.973333
LOAD_DUR  = float(DURATION)
TRANS_DUR = 0.6

off1 = PRES_DUR - TRANS_DUR
off2 = off1 + LOAD_DUR - TRANS_DUR

scale_f = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
           "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
           "fps=fps=30,settb=1/30000")

fc = (
    f"[0:v]{scale_f}[v0];"
    f"[1:v]{scale_f}[v1];"
    f"[2:v]{scale_f}[v2];"
    f"[v0][v1]xfade=transition=fadewhite:duration={TRANS_DUR}:offset={off1}[v01];"
    f"[v01][v2]xfade=transition=fadewhite:duration={TRANS_DUR}:offset={off2}[v];"
    f"[0:a][1:a]acrossfade=d={TRANS_DUR}[a01];"
    f"[a01][2:a]acrossfade=d={TRANS_DUR}[a]"
)

subprocess.run([
    FFMPEG, "-y",
    "-i", PRESENTATION,
    "-i", LOADER_AUDIO,
    "-i", IPL,
    "-filter_complex", fc,
    "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-crf", "18", "-preset", "slow",
    "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart",
    FINAL,
], check=True)

# ── 4. Cleanup ───────────────────────────────────────────────────────────────
shutil.rmtree(FRAMES_DIR, ignore_errors=True)
for f in (LOADER_PATH, LOADER_AUDIO):
    if os.path.exists(f):
        os.remove(f)

print(f"Done! Output: {FINAL}")
