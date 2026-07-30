"""Live end-to-end proof of the multi-medication splitter.

Logs in as a seeded test patient, uploads the REAL synthetic prescription
image through the real backend -> real sidecar (PaddleOCR) -> parser, and
prints every prescription record created plus its DIN suggestions.

Before this session's change the same upload produced ONE record named
"1. Tylenol Extra Strength (Acetaminophen 500 mg)".
"""
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
import uuid

BACKEND = "http://127.0.0.1:8000"
EMAIL = "margaret@test.com"
PASSWORD = "PillSafe1"
IMAGE = r"D:\Projects\PillSafe\archive\docs\Synthetic_Prescription_Test1.png"


def call(url, data=None, headers=None, method=None, timeout=600):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def login() -> str:
    for path, payload in (
        ("/api/v1/auth/login", {"email": EMAIL, "password": PASSWORD}),
        ("/api/v1/auth/token", {"email": EMAIL, "password": PASSWORD}),
    ):
        status, body = call(
            BACKEND + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        if status == 200 and isinstance(body, dict):
            tok = body.get("access_token") or body.get("token")
            if tok:
                print(f"login via {path}: 200")
                return tok
        print(f"login via {path}: {status} {str(body)[:200]}")
    raise SystemExit("could not log in")


def upload(token: str):
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(IMAGE)[0] or "image/png"
    with open(IMAGE, "rb") as fh:
        data = fh.read()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
        f"filename=\"{os.path.basename(IMAGE)}\"\r\nContent-Type: {ctype}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    t0 = time.perf_counter()
    status, resp = call(
        BACKEND + "/api/v1/prescriptions",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
        },
        timeout=900,
    )
    return status, resp, time.perf_counter() - t0


def main() -> None:
    print(f"image: {IMAGE}  ({os.path.getsize(IMAGE)} bytes)")
    token = login()
    status, resp, secs = upload(token)
    print(f"\nPOST /api/v1/prescriptions -> {status} in {secs:.1f}s")
    if status != 201:
        print(str(resp)[:2000])
        return
    print(f"records created: {len(resp)}\n")
    for i, p in enumerate(resp, 1):
        sugg = p.get("din_suggestions") or []
        top = f"{sugg[0].get('din')} {sugg[0].get('name', '')[:38]} @{sugg[0].get('score')}" if sugg else "(none)"
        print(f"{i}. drug_name   = {p.get('drug_name')!r}")
        print(f"   dosage      = {p.get('dosage')!r}")
        print(f"   freq_type   = {p.get('frequency_type')}  slots={p.get('time_slots')} times={p.get('specific_times')}")
        print(f"   freq_text   = {(p.get('frequency_text') or '')[:100]!r} (len={len(p.get('frequency_text') or '')})")
        print(f"   top DIN     = {top}")
        print()


if __name__ == "__main__":
    main()
