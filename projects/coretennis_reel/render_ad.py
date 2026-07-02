#!/usr/bin/env python3
"""CORE Tennis Camp — Reels/Stories ad (1080x1920). Frame-by-frame motion graphics.
No external assets: sky, sun, mountains, palms, court and ball are drawn; text is kinetic.
Outputs a PNG sequence to /tmp/frames_ad/."""
import os, math, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
DUR = 14.5
N = int(DUR * FPS)
OUT = "/tmp/frames_ad"
os.makedirs(OUT, exist_ok=True)

FREG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FBLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ---------- palette ----------
NEON = (198, 255, 0)      # tennis ball / accent
NEON_D = (150, 200, 0)
WHITE = (255, 255, 255)
GOLD = (255, 214, 150)
INK = (14, 22, 30)

def font(sz, bold=True):
    return ImageFont.truetype(FBLD if bold else FREG, sz)

def ease(t):  # smoothstep 0..1
    t = max(0.0, min(1.0, t)); return t*t*(3-2*t)

def lerp(a, b, t): return a + (b - a) * t

# ---------- static sky (numpy, sunset -> teal) ----------
def make_sky():
    top = np.array([255, 138, 76], float)     # warm orange
    mid = np.array([255, 175, 120], float)    # peach
    bot = np.array([28, 78, 96], float)       # teal ocean
    ys = np.linspace(0, 1, H)[:, None]
    # two-stop gradient with horizon around 0.62
    hz = 0.60
    col = np.zeros((H, 3))
    upper = ys[:, 0] < hz
    tu = (ys[:, 0] / hz)[:, None]
    col_up = top * (1 - tu) + mid * tu
    tl = ((ys[:, 0] - hz) / (1 - hz))[:, None]
    col_lo = mid * (1 - tl) + bot * tl
    col = np.where(upper[:, None], col_up, col_lo)
    img = np.repeat(col[:, None, :], W, axis=1)
    return img  # HxWx3 float

SKY = make_sky()

def radial_sun(cx, cy, r_core, r_glow, core, glow):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    g = np.clip(1 - d / r_glow, 0, 1) ** 2
    c = np.clip(1 - d / r_core, 0, 1)
    layer = np.zeros((H, W, 3))
    for i in range(3):
        layer[..., i] = g * glow[i] + c * core[i]
    return layer, np.clip(g + c, 0, 1)

def mountain_mask(base_y, amp, seed, sharp=1.0):
    xs = np.linspace(0, 1, W)
    prof = (np.sin(xs * 6 + seed) * 0.5 + np.sin(xs * 13 + seed * 2) * 0.3 +
            np.sin(xs * 2 + seed) * 0.4)
    prof = prof / np.max(np.abs(prof))
    ridge = base_y - (prof * amp)
    yy = np.arange(H)[:, None]
    m = (yy >= ridge[None, :]).astype(float)
    return m

def palm_layer():
    """Draw two palm silhouettes (bottom corners) as RGBA."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def palm(x0, y0, s, flip=1):
        # trunk
        pts = []
        for t in np.linspace(0, 1, 24):
            x = x0 + flip * (math.sin(t * 1.1) * 40 * s)
            y = y0 - t * 620 * s
            pts.append((x, y))
        for i in range(len(pts) - 1):
            w = int(28 * s * (1 - i / len(pts) * 0.6))
            d.line([pts[i], pts[i + 1]], fill=INK + (255,), width=max(3, w))
        tx, ty = pts[-1]
        # fronds
        for a in range(-4, 5):
            ang = math.radians(a * 22 - 90)
            fr = []
            for t in np.linspace(0, 1, 16):
                rr = t * 300 * s
                droop = (t ** 2) * 120 * s
                x = tx + flip * math.cos(ang) * rr
                y = ty + math.sin(ang) * rr + droop
                fr.append((x, y))
            for i in range(len(fr) - 1):
                w = max(2, int(14 * s * (1 - i / len(fr))))
                d.line([fr[i], fr[i + 1]], fill=INK + (255,), width=w)
    palm(150, H - 40, 1.15, flip=1)
    palm(W - 120, H + 10, 1.35, flip=-1)
    return im

# Pre-rendered background pieces (RGBA / arrays)
PALMS = palm_layer()
MTN_FAR = mountain_mask(H * 0.62, 150, 1.7)
MTN_NEAR = mountain_mask(H * 0.66, 240, 4.2)
MTN_FAR_COL = np.array([70, 96, 110], float)
MTN_NEAR_COL = np.array([34, 54, 66], float)
OCEAN_Y = int(H * 0.66)

def court_layer(alpha=200):
    """Neon perspective court baseline near bottom."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cy = int(H * 0.80)
    vanish = (W // 2, int(H * 0.66))
    # side lines converging
    for sx in (W * 0.16, W * 0.84):
        d.line([(sx, H), vanish], fill=NEON + (90,), width=5)
    # horizontal baselines
    for k, yy in enumerate(np.linspace(cy, H - 20, 4)):
        t = (yy - cy) / (H - 20 - cy)
        x0 = lerp(vanish[0], W * 0.16, t); x1 = lerp(vanish[0], W * 0.84, t)
        d.line([(x0, yy), (x1, yy)], fill=NEON + (int(60 + 90 * t),), width=4)
    return im.filter(ImageFilter.GaussianBlur(0.4))

COURT = court_layer()

def draw_ball(size):
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, s - 1, s - 1], fill=NEON, outline=NEON_D, width=max(1, s // 22))
    # classic tennis seam: a single S-curve sweeping across the ball
    wl = max(2, s // 11)
    pts = []
    for i in range(41):
        tt = i / 40.0
        x = s * (0.06 + 0.88 * tt)
        y = s * 0.5 - math.sin(tt * 2 * math.pi) * s * 0.28
        pts.append((x, y))
    d.line(pts, fill=(255, 255, 255, 235), width=wl, joint="curve")
    # subtle top-left highlight
    d.ellipse([int(s*0.22), int(s*0.16), int(s*0.44), int(s*0.38)], fill=(255, 255, 255, 55))
    return im

def compose_background(f):
    t = f / N
    sky = SKY.copy()
    # sun rising slightly + gentle horizontal sway
    sun_cx = W * 0.5 + math.sin(t * 1.4) * 30
    sun_cy = H * 0.34 - t * 50
    slayer, _ = radial_sun(sun_cx, sun_cy, 70, 300,
                           np.array([255, 226, 165]), np.array([255, 158, 80]))
    sky = np.clip(sky + slayer * 255 * 0.5, 0, 255)
    # mountains (parallax sway via small roll)
    def blend(mask, col, a):
        m = (mask * a)[..., None]
        return sky * (1 - m) + col[None, None, :] * m
    sky = blend(MTN_FAR, MTN_FAR_COL, 0.85)
    sky = blend(MTN_NEAR, MTN_NEAR_COL, 1.0)
    # ocean shimmer band
    yy = np.arange(H)[:, None]
    ocean = (yy >= OCEAN_Y).astype(float)
    shim = (np.sin((yy / 12.0) + t * 20) * 0.5 + 0.5) * ocean * 18
    sky = np.clip(sky + shim[..., None], 0, 255)
    img = Image.fromarray(sky.astype("uint8"), "RGB").convert("RGBA")
    # court + palms
    img.alpha_composite(COURT)
    img.alpha_composite(PALMS)
    return img

# ---------- text sprites ----------
def text_sprite(lines, sizes, colors, bold=True, spacing=18, shadow=True, lsp=0, halo=True):
    fnts = [font(s, bold) for s in sizes]
    widths, heights = [], []
    tmp = Image.new("RGBA", (10, 10)); td = ImageDraw.Draw(tmp)
    for ln, fn in zip(lines, fnts):
        bb = td.textbbox((0, 0), ln, font=fn)
        widths.append(bb[2] - bb[0] + lsp * max(0, len(ln) - 1)); heights.append(bb[3] - bb[1] + 8)
    PAD = 60
    Wt = max(widths) + PAD * 2
    Ht = sum(heights) + spacing * (len(lines) - 1) + PAD * 2
    # draw text on its own layer
    txt = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)
    y = PAD
    for ln, fn, col, w, h in zip(lines, fnts, colors, widths, heights):
        x = (Wt - w) // 2
        if lsp == 0:
            d.text((x, y), ln, font=fn, fill=col + (255,))
        else:
            cx = x
            for ch in ln:
                d.text((cx, y), ch, font=fn, fill=col + (255,))
                cx += td.textbbox((0, 0), ch, font=fn)[2] + lsp
        y += h + spacing
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    if halo:
        a = txt.split()[3]
        dark = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
        dark.putalpha(a)
        # heavy soft dark glow so light text reads on any background
        glow = dark.filter(ImageFilter.GaussianBlur(14))
        im.alpha_composite(glow); im.alpha_composite(glow)
    elif shadow:
        a = txt.split()[3]
        sh = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0)); sh.putalpha(a)
        sh = sh.filter(ImageFilter.GaussianBlur(4))
        im.alpha_composite(sh, (3, 5))
    im.alpha_composite(txt)
    return im

def pill(text, sz, fg, bg, pad=(46, 26)):
    fn = font(sz, True)
    tmp = Image.new("RGBA", (10, 10)); td = ImageDraw.Draw(tmp)
    bb = td.textbbox((0, 0), text, font=fn); tw, th = bb[2]-bb[0], bb[3]-bb[1]
    Wt, Ht = tw + pad[0]*2, th + pad[1]*2
    im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, Wt-1, Ht-1], radius=Ht//2, fill=bg + (255,))
    d.text((pad[0]-bb[0], pad[1]-bb[1]), text, font=fn, fill=fg + (255,))
    return im

# Build sprites once
S = {}
S['kick_top'] = text_sprite(["TENNIS CAMP  ·  FOR ADULTS"], [38], [WHITE], bold=True, lsp=5)
S['h1'] = text_sprite(["PLAY WHERE", "OTHERS VACATION"], [86, 74], [WHITE, NEON])
S['loc'] = text_sprite(["TENERIFE", "& PORTUGAL"], [108, 100], [WHITE, NEON])
S['loc_sub'] = text_sprite(["Sun · Ocean · Mountains"], [44], [GOLD], bold=False, lsp=2, halo=False)
S['lvl'] = text_sprite(["BEGINNER TO", "HOTSHOT"], [80, 116], [WHITE, NEON])
S['lvl_sub'] = text_sprite(["Every level. Every day."], [44], [GOLD], bold=False, halo=False)
S['b1'] = pill("Pro coaching", 46, INK, NEON)
S['b2'] = pill("Small groups", 46, WHITE, (34, 54, 66))
S['b3'] = pill("Play all year round", 46, INK, GOLD)
S['cta_name'] = text_sprite(["CORE", "TENNIS CAMP"], [122, 72], [WHITE, NEON])
S['cta_btn'] = pill("BOOK YOUR SPOT", 52, INK, NEON, pad=(60, 30))
S['cta_url'] = text_sprite(["coretenniscamp.com"], [46], [WHITE], bold=False, lsp=2, halo=False)

# soft vignette + top/bottom scrim for legibility (built once)
def make_vignette():
    v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    yy = np.arange(H)
    top = np.clip(1 - yy / (H * 0.22), 0, 1) * 60      # darken very top
    bot = np.clip((yy - H * 0.72) / (H * 0.28), 0, 1) * 90  # darken bottom
    col = (top + bot).astype("uint8")
    arr = np.zeros((H, W, 4), "uint8"); arr[..., 3] = col[:, None]
    v = Image.fromarray(arr, "RGBA")
    # edge vignette
    yy2, xx2 = np.mgrid[0:H, 0:W]
    dx = (xx2 - W / 2) / (W / 2); dy = (yy2 - H / 2) / (H / 2)
    r = np.sqrt(dx ** 2 + dy ** 2)
    edge = np.clip((r - 0.8) / 0.6, 0, 1) * 70
    e = np.zeros((H, W, 4), "uint8"); e[..., 3] = edge.astype("uint8")
    v.alpha_composite(Image.fromarray(e, "RGBA"))
    return v

VIGNETTE = make_vignette()
BALL = draw_ball(120)
BALL_S = draw_ball(70)

def paste_c(base, sprite, cx, cy, alpha=1.0, scale=1.0, rot=0):
    sp = sprite
    if scale != 1.0:
        sp = sp.resize((max(1, int(sp.width*scale)), max(1, int(sp.height*scale))), Image.LANCZOS)
    if rot:
        sp = sp.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 1.0:
        a = sp.split()[3].point(lambda p: int(p * alpha))
        sp = sp.copy(); sp.putalpha(a)
    base.alpha_composite(sp, (int(cx - sp.width/2), int(cy - sp.height/2)))

def entrance(local_t, dur=0.5, dy=60):
    """returns (alpha, y_offset) sliding up + fading in over dur, out at end handled by caller."""
    a = ease(local_t / dur)
    off = (1 - a) * dy
    return a, off

# scene windows (start,end) seconds
SC = {
    's1': (0.0, 3.2), 's2': (3.2, 6.2), 's3': (6.2, 9.2),
    's4': (9.2, 12.0), 's5': (12.0, 14.5),
}

def ball_arc(f):
    """Recurring ball motif crossing scenes with bounce."""
    t = f / N
    x = lerp(-80, W + 80, (t * 1.15) % 1.0)
    base = H * 0.5
    y = base - abs(math.sin(t * math.pi * 4)) * 260
    rot = (t * 1440) % 360
    return x, y, rot

for f in range(N):
    tsec = f / FPS
    img = compose_background(f)

    # recurring small ball motif (subtle, behind text) during transitions
    bx, by, br = ball_arc(f)
    paste_c(img, BALL_S, bx, by, alpha=0.4, rot=-br)
    # legibility scrim / vignette
    img.alpha_composite(VIGNETTE)

    def in_scene(name):
        s, e = SC[name]; return s <= tsec < e, tsec - s, e - s

    # S1 hook
    act, lt, ln = in_scene('s1')
    if act:
        a, off = entrance(lt, 0.5, 70)
        outa = 1 - ease((lt - (ln - 0.4)) / 0.4) if lt > ln - 0.4 else 1
        A = a * outa
        paste_c(img, S['kick_top'], W/2, H*0.30 - off, alpha=A)
        # pop scale on hook
        pop = lerp(0.86, 1.0, ease(lt / 0.55))
        paste_c(img, S['h1'], W/2, H*0.46 + off*0.4, alpha=A, scale=pop)
        paste_c(img, BALL, W*0.5, H*0.60, alpha=A, scale=lerp(0.5,1.0,ease(lt/0.6)),
                rot=-(lt*400))

    # S2 locations
    act, lt, ln = in_scene('s2')
    if act:
        a, off = entrance(lt, 0.5, 80)
        outa = 1 - ease((lt - (ln - 0.4)) / 0.4) if lt > ln - 0.4 else 1
        A = a * outa
        paste_c(img, S['loc'], W/2, H*0.44 - off, alpha=A, scale=lerp(0.92,1.0,ease(lt/0.5)))
        a2, off2 = entrance(max(0, lt-0.25), 0.5, 50)
        paste_c(img, S['loc_sub'], W/2, H*0.56 - off2, alpha=min(A, a2))

    # S3 levels
    act, lt, ln = in_scene('s3')
    if act:
        a, off = entrance(lt, 0.5, 80)
        outa = 1 - ease((lt - (ln - 0.4)) / 0.4) if lt > ln - 0.4 else 1
        A = a * outa
        paste_c(img, S['lvl'], W/2, H*0.45 - off, alpha=A)
        a2, off2 = entrance(max(0, lt-0.3), 0.5, 50)
        paste_c(img, S['lvl_sub'], W/2, H*0.57 - off2, alpha=min(A, a2))

    # S4 benefits (staggered pills)
    act, lt, ln = in_scene('s4')
    if act:
        outa = 1 - ease((lt - (ln - 0.4)) / 0.4) if lt > ln - 0.4 else 1
        ys = [H*0.40, H*0.50, H*0.60]
        for i, key in enumerate(['b1', 'b2', 'b3']):
            a, off = entrance(max(0, lt - i*0.28), 0.45, 60)
            paste_c(img, S[key], W/2, ys[i] - off, alpha=a*outa)

    # S5 CTA
    act, lt, ln = in_scene('s5')
    if act:
        a, off = entrance(lt, 0.5, 70)
        paste_c(img, S['cta_name'], W/2, H*0.40 - off, alpha=a,
                scale=lerp(0.9,1.0,ease(lt/0.5)))
        a2, _ = entrance(max(0, lt-0.35), 0.4, 0)
        # pulsing button
        pulse = 1.0 + 0.04*math.sin((lt)*8)
        paste_c(img, S['cta_btn'], W/2, H*0.56, alpha=a2, scale=pulse)
        a3, off3 = entrance(max(0, lt-0.6), 0.4, 30)
        paste_c(img, S['cta_url'], W/2, H*0.64 - off3, alpha=a3)

    # global fades
    if tsec < 0.5:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, int(255*(1-ease(tsec/0.5)))))
        img.alpha_composite(ov)
    if tsec > DUR - 0.5:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, int(255*ease((tsec-(DUR-0.5))/0.5))))
        img.alpha_composite(ov)

    img.convert("RGB").save(f"{OUT}/f{f:04d}.png")

print(f"rendered {N} frames to {OUT}")
