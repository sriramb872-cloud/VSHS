"""Profile-photo upload flow verification (QA only).

Covers: authorization, valid image accepted, non-image rejected, unsupported
format rejected, oversize rejected, on-disk storage, the `uploads` metadata row
and cross-tenant metadata isolation.

Read-mostly: it uploads a generated 1x1 PNG to the QA student account and
leaves it there (that is the point - the flow must work end to end).
"""
import io
import json
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = "http://localhost:8000/api/v1"
RESULTS = []


class Res:
    def __init__(self, status, body, headers=None):
        self.status_code = status
        self.text = body
        self.headers = headers or {}

    def json(self):
        return json.loads(self.text)


def call(method, path, token=None, params=None, json_body=None, body=None, content_type=None):
    url = f"{BASE}{path}"
    if params:
        url = f"{url}?{params}"
    headers = {}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    elif body is not None:
        data = body
        if content_type:
            headers["Content-Type"] = content_type
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=60) as r:
            return Res(r.status, r.read().decode(), dict(r.headers))
    except HTTPError as e:
        return Res(e.code, e.read().decode(), dict(e.headers))


def login(mobile, password):
    for _ in range(6):
        r = call("POST", "/auth/login", json_body={"mobile": mobile, "password": password})
        if r.status_code == 200:
            return r.json()["access_token"]
        time.sleep(12)
    raise SystemExit(f"login failed: {r.status_code} {r.text}")


def check(label, got, want):
    ok = got in want
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got}, expected {sorted(want)}")


def png_bytes(size=(1, 1)):
    """Minimal valid PNG built by hand (no Pillow dependency)."""
    import struct
    import zlib

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    w, h = size
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b"".join(b"\x00" + bytes([200, 120, 60] * w) for _ in range(h))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def multipart(field, filename, content, content_type):
    boundary = "----qaBoundary9f2c"
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        content,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    return body, f"multipart/form-data; boundary={boundary}"


def main():
    student = login("9000001001", "QaStu#2026")
    pr7 = login("9000000009", "QaTestB#2026")
    sa = login("8019302351", "super")

    print("== authorization ==")
    body, ct = multipart("file", "x.png", png_bytes(), "image/png")
    check("no token upload", call("POST", "/files/profile-photo", None, body=body, content_type=ct).status_code, {401})

    print("\n== invalid input ==")
    body, ct = multipart("file", "notes.txt", b"this is definitely not an image", "text/plain")
    check("text file rejected", call("POST", "/files/profile-photo", student, body=body, content_type=ct).status_code, {400})

    body, ct = multipart("file", "payload.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 8, "image/png")
    check("corrupt png rejected", call("POST", "/files/profile-photo", student, body=body, content_type=ct).status_code, {400})

    # A real GIF: PIL verifies it, but the endpoint only allows jpg/png/webp.
    gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    body, ct = multipart("file", "anim.gif", gif, "image/gif")
    check("unsupported image format rejected", call("POST", "/files/profile-photo", student, body=body, content_type=ct).status_code, {400})

    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (6 * 1024 * 1024)
    body, ct = multipart("file", "big.png", big, "image/png")
    check("oversize (>5MB) rejected", call("POST", "/files/profile-photo", student, body=body, content_type=ct).status_code, {413})

    print("\n== valid upload ==")
    body, ct = multipart("file", "qa-avatar.png", png_bytes((2, 2)), "image/png")
    r = call("POST", "/files/profile-photo", student, body=body, content_type=ct)
    check("valid png accepted", r.status_code, {200})
    if r.status_code != 200:
        print("       body:", r.text[:300])
        return 1
    payload = r.json()
    print(f"       photo_url={payload['photo_url']} file_id={payload.get('file_id')} size={payload.get('file_size')}")
    check("photo_url is under /media", str(payload["photo_url"]).startswith("/media/profile_photos/"), {True})
    check("upload returns a file id", isinstance(payload.get("file_id"), int), {True})

    me = call("GET", "/users/me", student)
    check("profile_photo persisted on the user", me.json().get("profile_photo") == payload["photo_url"], {True})

    print("\n== metadata retrieval ==")
    fid = payload["file_id"]
    r = call("GET", f"/files/metadata/{fid}", student)
    check("owner can read metadata", r.status_code, {200})
    if r.status_code == 200:
        m = r.json()
        print(f"       {m['original_filename']} {m['content_type']} {m['file_size']}B exists={m['exists_on_disk']} entity={m['entity_type']}")
        check("metadata reports the file on disk", m["exists_on_disk"], {True})
        check("metadata size matches the upload", m["file_size"] == payload["file_size"], {True})

    r = call("GET", f"/files/metadata/{fid}", pr7)
    check("another tenant cannot read the metadata", r.status_code, {403})
    r = call("GET", f"/files/metadata/{fid}", sa)
    check("super admin can read the metadata", r.status_code, {200})
    r = call("GET", "/files/metadata/999999", sa)
    check("unknown id is 404", r.status_code, {404})

    r = call("GET", "/files/metadata", pr7)
    check("principal 7 sees no school 6 uploads", r.status_code, {200})
    if r.status_code == 200:
        check("principal 7 upload list is empty", r.json() == [], {True})

    print(f"\n==== {sum(RESULTS)} passed, {len(RESULTS) - sum(RESULTS)} failed ====")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
