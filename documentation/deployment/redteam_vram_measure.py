"""VRAM + latency measurement for the 'local 7B in the Rx parse path' question.

Replaces four estimated numbers with measured ones:
  1. what the sidecar actually holds at rest, and during a real pill analysis
  2. what qwen2.5:7b-instruct holds, and how that scales with num_ctx
  3. whether keep_alive=0 really frees it, and what the reload costs
  4. whether a pill analysis still works with the 7B resident

Run with the sidecar already up on 127.0.0.1:8100 and Ollama on 11434.
"""
import json
import mimetypes
import os
import subprocess
import threading
import time
import urllib.request
import uuid

SIDECAR = "http://127.0.0.1:8100"
OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen2.5:7b-instruct"
PILL_IMAGE = r"D:\Projects\PillSafe\Brainstorm\OTC_Images\Raw\DIN00013803_DarkGrey_ColourRef_Front_DL.jpg"


def vram_used_mib() -> int:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    ).stdout.strip()
    return int(out.splitlines()[0])


class Peak:
    """Samples VRAM every 200 ms while a step runs."""

    def __init__(self) -> None:
        self.peak = 0
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.peak = max(self.peak, vram_used_mib())
            except Exception:
                pass
            time.sleep(0.2)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join(timeout=2)


def post_json(url: str, payload: dict, timeout: int = 600) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def post_file(url: str, path: str, fields: dict | None = None, timeout: int = 900) -> dict:
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path)[0] or "image/jpeg"
    body = b""
    for k, v in (fields or {}).items():
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n"
        ).encode()
    with open(path, "rb") as fh:
        data = fh.read()
    body += (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
        f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: {ctype}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ollama_ps() -> list[dict]:
    with urllib.request.urlopen(f"{OLLAMA}/api/ps", timeout=30) as r:
        return json.loads(r.read()).get("models", [])


def unload(model: str = MODEL) -> None:
    try:
        post_json(f"{OLLAMA}/api/generate", {"model": model, "prompt": "", "keep_alive": 0}, timeout=120)
    except Exception as exc:
        print(f"   (unload call: {exc})")
    for _ in range(40):
        if not ollama_ps():
            return
        time.sleep(0.5)


def load_7b(num_ctx: int, keep_alive: str | int = "5m") -> tuple[float, dict]:
    t0 = time.perf_counter()
    resp = post_json(
        f"{OLLAMA}/api/generate",
        {
            "model": MODEL,
            "prompt": "Reply with the single word: ready",
            "stream": False,
            "keep_alive": keep_alive,
            "options": {"num_ctx": num_ctx, "num_predict": 4},
        },
        timeout=900,
    )
    return time.perf_counter() - t0, resp


def report(label: str, before: int, peak: int, after: int, seconds: float | None = None) -> None:
    extra = f"  elapsed={seconds:6.1f}s" if seconds is not None else ""
    print(f"{label:<46} before={before:5d}  peak={peak:5d}  after={after:5d} MiB{extra}")


def main() -> None:
    total = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    ).stdout.strip().splitlines()[0]
    print(f"GPU total: {total} MiB\n")
    print("=" * 100)
    print("STEP 1 - sidecar at rest, then one real pill analysis (IMB1 + SB2)")
    print("=" * 100)
    unload()
    base = vram_used_mib()
    with Peak() as p:
        t0 = time.perf_counter()
        result = post_file(
            f"{SIDECAR}/pill/analyze", PILL_IMAGE, {"profile_dins": json.dumps(["DIN13803"])}
        )
        dt = time.perf_counter() - t0
    time.sleep(2)
    report("sidecar idle -> pill analyze", base, p.peak, vram_used_mib(), dt)
    print(f"   decision={result.get('decision')}  score={result.get('score')}")

    print()
    print("=" * 100)
    print("STEP 2 - qwen2.5:7b-instruct resident VRAM vs num_ctx")
    print("=" * 100)
    for ctx in (4096, 16384):
        unload()
        time.sleep(2)
        before = vram_used_mib()
        with Peak() as p:
            secs, _ = load_7b(ctx)
        time.sleep(2)
        after = vram_used_mib()
        report(f"load 7B num_ctx={ctx}", before, p.peak, after, secs)
        for m in ollama_ps():
            size_mb = m.get("size", 0) / 1e6
            vram_mb = m.get("size_vram", 0) / 1e6
            pct = (vram_mb / size_mb * 100) if size_mb else 0
            print(
                f"   ollama ps: size={size_mb:7.0f} MB  size_vram={vram_mb:7.0f} MB "
                f"({pct:.0f}% on GPU)  ctx={m.get('context_length')}"
            )

    print()
    print("=" * 100)
    print("STEP 3 - does keep_alive=0 actually free it, and what does a reload cost?")
    print("=" * 100)
    t0 = time.perf_counter()
    unload()
    time.sleep(2)
    print(f"   unload -> {vram_used_mib()} MiB in {time.perf_counter() - t0:.1f}s "
          f"(models still loaded: {len(ollama_ps())})")
    secs_cold, _ = load_7b(8192)
    print(f"   COLD reload (num_ctx=8192): {secs_cold:.1f}s to first response")
    secs_warm, _ = load_7b(8192)
    print(f"   WARM call (already resident): {secs_warm:.1f}s")

    print()
    print("=" * 100)
    print("STEP 4 - pill analysis WITH the 7B resident (the contention case)")
    print("=" * 100)
    before = vram_used_mib()
    with Peak() as p:
        t0 = time.perf_counter()
        try:
            result2 = post_file(
                f"{SIDECAR}/pill/analyze", PILL_IMAGE, {"profile_dins": json.dumps(["DIN13803"])}
            )
            dt2 = time.perf_counter() - t0
            ok = f"decision={result2.get('decision')} score={result2.get('score')}"
        except Exception as exc:
            dt2 = time.perf_counter() - t0
            ok = f"FAILED: {type(exc).__name__}: {exc}"
    report("7B resident -> pill analyze", before, p.peak, vram_used_mib(), dt2)
    print(f"   {ok}")
    for m in ollama_ps():
        print(f"   7B after contention: size_vram={m.get('size_vram', 0) / 1e6:.0f} MB")

    print()
    print("=" * 100)
    print("CLEANUP - unloading the 7B")
    print("=" * 100)
    unload()
    print(f"   final VRAM: {vram_used_mib()} MiB")


if __name__ == "__main__":
    main()
