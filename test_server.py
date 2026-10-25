#!/usr/bin/env python3
"""
Check a RadRobin segmentation server against API.md, without the viewer.

    python test_server.py                              tests http://127.0.0.1:8080
    python test_server.py --url http://lab-gpu:8080    tests another server
    python test_server.py --standard                   uses standard (1.5 mm) mode instead of fast

Needs nibabel and numpy, which are installed with TotalSegmentator.
"""
import argparse
import json
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

FAILS = 0


def report(status, name, detail=""):
    global FAILS
    if status == "FAIL":
        FAILS += 1
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""), flush=True)


def check_health(base, origin):
    req = urllib.request.Request(base + "/health", headers={"Origin": origin})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read().decode())
            allow = r.headers.get("Access-Control-Allow-Origin")
    except Exception as e:
        report("FAIL", "GET /health", f"no answer from {base} ({e}). Is the server running?")
        return False
    report("PASS", "GET /health", json.dumps(body))

    version = str(body.get("engine_version", ""))
    if version.startswith("2."):
        report("PASS", "TotalSegmentator version", version)
    else:
        report("FAIL", "TotalSegmentator version", f"{version or 'missing'}; RadRobin needs 2.x for correct label names")

    if allow in (origin, "*"):
        report("PASS", "Browser access (CORS)", f"{origin} is allowed")
    else:
        report("FAIL", "Browser access (CORS)",
               f"{origin} is not allowed; the viewer will be blocked. Add it to ALLOWED_ORIGINS.")
    return True


def make_test_volume(path):
    import nibabel as nib
    import numpy as np

    vol = np.full((96, 96, 96), -1000, dtype=np.int16)   # air
    vol[24:72, 24:72, 24:72] = 40                        # soft-tissue block
    nib.save(nib.Nifti1Image(vol, np.diag([2.0, 2.0, 2.0, 1.0])), str(path))
    return vol.shape


def post_segment(base, nifti_path, fast, timeout):
    boundary = uuid.uuid4().hex
    data = Path(nifti_path).read_bytes()
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"fast_mode\"\r\n\r\n"
        f"{'true' if fast else 'false'}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"test.nii.gz\"\r\n"
        "Content-Type: application/gzip\r\n\r\n".encode(),
        data,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    req = urllib.request.Request(
        base + "/segment",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def check_segment(base, fast, timeout):
    import nibabel as nib

    with tempfile.TemporaryDirectory() as tmp:
        inp, out = Path(tmp) / "test.nii.gz", Path(tmp) / "mask.nii.gz"
        shape = make_test_volume(inp)
        print(f"Sending a small synthetic volume ({'fast' if fast else 'standard'} mode). "
              "The first run can take several minutes while the server downloads model weights...",
              flush=True)
        t0 = time.time()
        try:
            out.write_bytes(post_segment(base, inp, fast, timeout))
        except urllib.error.HTTPError as e:
            report("FAIL", "POST /segment", f"HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
            return
        except Exception as e:
            report("FAIL", "POST /segment", str(e))
            return
        secs = time.time() - t0
        try:
            mask = nib.load(str(out))
        except Exception as e:
            report("FAIL", "POST /segment", f"answer is not a readable NIfTI file ({e})")
            return
        if tuple(mask.shape[:3]) == tuple(shape):
            report("PASS", "POST /segment", f"mask {mask.shape}, {mask.get_data_dtype()}, {secs:.0f} s")
        else:
            report("FAIL", "POST /segment", f"mask shape {mask.shape} does not match input {shape}")
        print("       (The test volume is not a real scan, so the mask is expected to be mostly empty.)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://127.0.0.1:8080", help="server address")
    p.add_argument("--origin", default="https://radrobin.com", help="website the viewer runs on")
    p.add_argument("--standard", action="store_true", help="standard 1.5 mm mode instead of fast")
    p.add_argument("--timeout", type=int, default=1800, help="seconds to wait for segmentation")
    a = p.parse_args()
    base = a.url.rstrip("/")

    print(f"Testing {base}\n")
    if check_health(base, a.origin):
        check_segment(base, not a.standard, a.timeout)
    print()
    print("All checks passed." if not FAILS else f"{FAILS} check(s) failed.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
