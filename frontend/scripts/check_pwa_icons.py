"""Inspect the generated PWA icons (QA/build tooling, not part of the app).

Reports real file dimensions, mode, byte size, corner alpha (so rounded icons
are genuinely transparent and maskable icons are genuinely opaque) and the
contrast of the glyph against the background, so a stretched or unreadable
icon is caught rather than shipped.
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.abspath(os.path.join(HERE, "..", "public", "icons"))


def _luma(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def main() -> int:
    if not os.path.isdir(ICON_DIR):
        print(f"no icon directory at {ICON_DIR}")
        return 1

    problems = []
    names = sorted(n for n in os.listdir(ICON_DIR) if n.endswith(".png"))
    for name in names:
        path = os.path.join(ICON_DIR, name)
        with Image.open(path) as im:
            im.load()
            w, h = im.size
            mode = im.mode
            rgba = im.convert("RGBA")
            corners = [
                rgba.getpixel((0, 0))[3],
                rgba.getpixel((w - 1, 0))[3],
                rgba.getpixel((0, h - 1))[3],
                rgba.getpixel((w - 1, h - 1))[3],
            ]
            centre = rgba.getpixel((w // 2, h // 2))

        alpha_note = "opaque" if min(corners) == 255 else f"alpha corners {corners}"
        print(f"\n{name}: {w}x{h} {mode} {os.path.getsize(path)}B")
        print(f"  corners: {alpha_note}")
        print(f"  centre px: {centre[:3]}")

        if w != h:
            problems.append(f"{name}: not square ({w}x{h})")
        expected = name.split("-")[-1].replace(".png", "")
        if expected.isdigit() and int(expected) != w:
            problems.append(f"{name}: filename says {expected} but is {w}px wide")

        is_maskable = "maskable" in name
        is_apple = "apple" in name
        if is_maskable or is_apple:
            if min(corners) != 255:
                problems.append(
                    f"{name}: maskable/apple icon must be fully opaque, corners={corners}"
                )
        else:
            if min(corners) == 255:
                problems.append(
                    f"{name}: expected transparent rounded corners for a non-maskable icon"
                )

        # Glyph contrast: the cap is white, the background is dark navy. Verify
        # there is real separation so the mark is not a flat silhouette.
        with Image.open(path) as im:
            rgba = im.convert("RGBA")
            px = rgba.load()
            lumas = []
            for y in range(0, h, max(1, h // 40)):
                for x in range(0, w, max(1, w // 40)):
                    r, g, b, a = px[x, y]
                    if a > 200:
                        lumas.append(_luma((r, g, b)))
            if lumas:
                spread = max(lumas) - min(lumas)
                print(f"  luma spread across glyph area: {spread:.1f}")
                if spread < 40:
                    problems.append(f"{name}: glyph has too little contrast (spread {spread:.1f})")

    print("\n" + "=" * 60)
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("All icons OK: square, correct sizes, alpha/maskable as expected, legible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
