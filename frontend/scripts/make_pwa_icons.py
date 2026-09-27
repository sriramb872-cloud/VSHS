"""Generate SCHOLARIS PWA icons (QA/build tooling, not part of the app).

The repository had no brand artwork - `public/` was empty and `src/assets` only
held the Vite starter images - so the icon is generated here from the colours and
motif the app already uses, read from `src/styles/variables.css` and
`src/layouts/AuthLayout.tsx`:

  * background : slate-900 -> indigo-950 -> slate-900 gradient (AuthLayout)
  * glyph      : white graduation cap (lucide `GraduationCap`, used in the
                 AuthLayout brand header and the AppShell sidebar)
  * wordmark   : "SCHOLARIS" in the extrabold/tracking-wide style of the
                 AuthLayout `<h1>`

Files are written to `frontend/public/` so Vite serves them at the site root in
both dev and the production build, which is what the manifest needs.

Run:  python scripts/make_pwa_icons.py
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.abspath(os.path.join(HERE, "..", "public", "icons"))

# Matches the app's own palette (tailwind indigo-950/900/600 + slate-900).
SLATE_900 = (15, 23, 42)
INDIGO_950 = (30, 27, 75)
INDIGO_600 = (79, 70, 229)
WHITE = (255, 255, 255)


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _diagonal_gradient(size, c0, c1):
    """Smooth diagonal gradient, the same shape as AuthLayout's
    `bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900`."""
    img = Image.new("RGB", (size, size), c0)
    px = img.load()
    denom = float((size - 1) * 2) or 1.0
    for y in range(size):
        for x in range(size):
            t = (x + y) / denom
            px[x, y] = _lerp(c0, c1, t)
    return img


def _rounded_mask(size, radius_ratio=0.22, ss=4):
    """Anti-aliased rounded-square mask."""
    s = size * ss
    r = int(s * radius_ratio)
    mask = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def _graduation_cap(draw, cx, cy, w, color):
    """A mortarboard: crown, board, tassel. Reads as a graduation cap at
    32px as well as 512px, which the previous diamond+chord attempt did not."""
    # 1. Crown: the part of the cap that sits under the board. Drawn first so
    #    the board overlaps its top edge and hides the seam.
    cw = w * 0.30           # half-width of the crown
    top = cy - w * 0.02
    bot = cy + w * 0.34
    draw.rounded_rectangle(
        [cx - cw, top, cx + cw, bot],
        radius=w * 0.10,
        fill=color,
    )

    # 2. Board: a wide flat diamond, the dominant silhouette.
    bh = w * 0.20           # half-height of the diamond
    draw.polygon(
        [(cx, cy - bh), (cx + w * 0.5, cy), (cx, cy + bh), (cx - w * 0.5, cy)],
        fill=color,
    )

    # 3. Tassel: a thin cord from the board's right vertex to a small ball,
    #    kept short so it does not dominate the mark.
    tx = cx + w * 0.5
    cord_len = w * 0.26
    cord_w = max(1, int(round(w * 0.028)))
    draw.line([(tx, cy), (tx, cy + cord_len)], fill=color, width=cord_w)
    r = w * 0.062
    draw.ellipse(
        [tx - r, cy + cord_len - r * 0.2, tx + r, cy + cord_len + r * 1.8],
        fill=color,
    )


def _load_font(size, bold=True):
    """Prefer a bold sans; fall back to PIL's bundled DejaVuSans."""
    names = [
        "segoeuib.ttf" if bold else "segoeui.ttf",   # Windows
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "Helvetica.ttc",
    ]
    for name in names:
        for base in (
            r"C:\Windows\Fonts",
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ):
            p = os.path.join(base, name)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except OSError:
                    continue
    return ImageFont.load_default(size)


def _text_width(draw, text, font, tracking):
    total = 0
    for ch in text:
        total += draw.textlength(ch, font=font) + tracking
    return total - tracking if text else 0


def _draw_wordmark(draw, text, cx, y, size, color, tracking_ratio=0.14):
    font = _load_font(size, bold=True)
    tracking = size * tracking_ratio
    x = cx - _text_width(draw, text, font, tracking) / 2
    for ch in text:
        draw.text((x, y), ch, font=font, fill=color)
        x += draw.textlength(ch, font=font) + tracking


def build_icon(size, *, maskable=False, with_wordmark=True, wordmark_ratio=0.155):
    """Return an RGBA icon.

    maskable=True produces the safe-zone variant: the artwork is inset to the
    inner 80% circle that Android/iOS may crop to, and the background is a full
    bleed square so no transparent corners show.
    """
    # Full-bleed background.
    bg = _diagonal_gradient(size, SLATE_900, INDIGO_950).convert("RGBA")

    # Artwork safe area.
    inset = 0.20 if maskable else 0.0
    art = int(size * (1 - 2 * inset))

    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    center_x = size / 2
    if with_wordmark:
        cap_w = art * 0.60
        cap_cy = size / 2 - art * 0.13
        wm_size = max(8, int(art * wordmark_ratio))
        _graduation_cap(d, center_x, cap_cy, cap_w, WHITE)
        _draw_wordmark(d, "SCHOLARIS", center_x, cap_cy + cap_w * 0.44, wm_size, WHITE)
    else:
        _graduation_cap(d, center_x, size / 2 - art * 0.04, art * 0.74, WHITE)

    layer = layer.resize((size, size), Image.LANCZOS)
    img = Image.alpha_composite(bg, layer)

    if maskable:
        # Maskable icons must be square with no transparency: the platform
        # applies its own mask, so no rounding here.
        return img

    img.putalpha(_rounded_mask(size))
    return img


def build_apple_touch(size=180):
    """iOS ignores the manifest icon and uses apple-touch-icon.

    iOS does NOT round the corners itself, and it composites the icon on an
    opaque background, so this one is a square, full-bleed image with the
    wordmark dropped (iOS already displays the app name under the icon).
    """
    return build_icon(size, maskable=True, with_wordmark=False)


def build_favicon(size=32):
    img = build_icon(size, maskable=True, with_wordmark=False)
    return img


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    written = []

    targets = [
        ("icon-192.png", 192, dict(maskable=False, with_wordmark=False)),
        ("icon-512.png", 512, dict(maskable=False, with_wordmark=False)),
        ("icon-192-maskable.png", 192, dict(maskable=True, with_wordmark=False)),
        ("icon-512-maskable.png", 512, dict(maskable=True, with_wordmark=False)),
    ]
    for name, size, kwargs in targets:
        path = os.path.join(OUT_DIR, name)
        build_icon(size, **kwargs).save(path, "PNG", optimize=True)
        written.append((name, size))

    apple = os.path.join(OUT_DIR, "apple-touch-icon.png")
    build_apple_touch(180).save(apple, "PNG", optimize=True)
    written.append(("apple-touch-icon.png", 180))

    # Favicon: rounded like the app icons so the mark is consistent wherever it
    # appears. Browsers show it at 16-32px, where the cap still reads.
    fav = os.path.join(OUT_DIR, "favicon.png")
    build_icon(32, maskable=False, with_wordmark=False).save(fav, "PNG", optimize=True)
    written.append(("favicon.png", 32))

    # Large "any" icon, used by some install UIs and store listings.
    big = os.path.join(OUT_DIR, "icon-1024.png")
    build_icon(1024, maskable=False, with_wordmark=False).save(big, "PNG", optimize=True)
    written.append(("icon-1024.png", 1024))

    for name, size in written:
        p = os.path.join(OUT_DIR, name)
        with Image.open(p) as im:
            actual = im.size
            mode = im.mode
        status = "OK " if actual == (size, size) else "BAD"
        print(f"  {status} {name:26} {actual[0]}x{actual[1]} {mode} {os.path.getsize(p)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
