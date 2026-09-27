"""Write a small valid PNG for the browser upload test (QA only)."""
import struct
import sys
import zlib


def chunk(tag: bytes, data: bytes) -> bytes:
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "qa-avatar.png"
    w = h = 24
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    rows = []
    for y in range(h):
        row = b"\x00"
        for x in range(w):
            row += bytes([(x * 10) % 256, (y * 10) % 256, 160])
        rows.append(row)
    raw = b"".join(rows)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    with open(out, "wb") as f:
        f.write(png)
    print(f"wrote {out} ({len(png)} bytes, {w}x{h})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
