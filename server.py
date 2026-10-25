"""
RadRobin TotalSegmentator server  (API version 1, see API.md)

Runs TotalSegmentator on your own machine for the RadRobin viewer.
The viewer sends a NIfTI volume to POST /segment and receives a
multilabel NIfTI mask back. Nothing is sent to RadRobin or anyone else.

Settings (environment variables, all optional):
  HOST             address to listen on            default 127.0.0.1 (this computer only)
  PORT             port                            default 8080
  ALLOWED_ORIGINS  comma-separated websites allowed to call this server
                   default https://radrobin.com,https://www.radrobin.com
  TS_BIN           path to the TotalSegmentator command   default: found on PATH
  TS_DEVICE        gpu | cpu | mps                 default: TotalSegmentator decides
  MAX_UPLOAD_MB    largest accepted upload         default 1024
"""
import os
import shutil
import subprocess
import tempfile
import threading
from importlib import metadata

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

API_VERSION = "1"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS", "https://radrobin.com,https://www.radrobin.com"
    ).split(",")
    if o.strip()
]
TS_BIN = os.environ.get("TS_BIN") or shutil.which("TotalSegmentator") or "TotalSegmentator"
TS_DEVICE = os.environ.get("TS_DEVICE")
MAX_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "1024")) * 1024 * 1024

try:
    TS_VERSION = metadata.version("TotalSegmentator")
except metadata.PackageNotFoundError:
    TS_VERSION = "unknown"

# One segmentation at a time, so two requests don't run the GPU out of memory.
GPU_LOCK = threading.Lock()

app = FastAPI(title="RadRobin TotalSegmentator server", version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.middleware("http")
async def allow_private_network(request: Request, call_next):
    # Chrome asks permission before a public website (radrobin.com) may call
    # localhost or a private-network address. This header answers yes.
    response = await call_next(request)
    if request.headers.get("access-control-request-private-network"):
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response


@app.get("/health")
def health():
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "engine": "TotalSegmentator",
        "engine_version": TS_VERSION,
        "task": "total",
        "device": TS_DEVICE or "auto",
        "busy": GPU_LOCK.locked(),
    }


@app.post("/segment")
def segment(file: UploadFile = File(...), fast_mode: str = Form("false")):
    # A sync endpoint: FastAPI runs it in a worker thread, so the long
    # TotalSegmentator run doesn't freeze the server.
    work_dir = tempfile.mkdtemp(prefix="radrobin_ts_")
    # The uploaded filename is never used in paths or commands.
    name = (file.filename or "").lower()
    in_ext = ".nii.gz" if name.endswith(".gz") else ".nii"
    input_path = os.path.join(work_dir, "input" + in_ext)
    output_path = os.path.join(work_dir, "mask.nii.gz")

    try:
        written = 0
        with open(input_path, "wb") as f:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_BYTES:
                    raise HTTPException(status_code=413, detail="File too large")
                f.write(chunk)

        cmd = [TS_BIN, "-i", input_path, "-o", output_path, "--ml"]
        fast = fast_mode.strip().lower() == "true"
        if fast:
            cmd.append("--fast")
        if TS_DEVICE:
            cmd += ["--device", TS_DEVICE]

        print(f"[INFO] Segmenting ({'fast 3 mm' if fast else 'standard 1.5 mm'})...", flush=True)
        with GPU_LOCK:
            proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0 or not os.path.exists(output_path):
            shutil.rmtree(work_dir, ignore_errors=True)
            print("[ERROR] TotalSegmentator failed", flush=True)
            return JSONResponse(
                status_code=500,
                content={"error": "TotalSegmentator failed", "detail": proc.stderr[-4000:]},
            )

        print("[OK] Done, sending mask back to the viewer", flush=True)
        # The temporary folder (input and mask) is deleted after the response is sent.
        return FileResponse(
            output_path,
            media_type="application/gzip",
            filename="mask.nii.gz",
            background=BackgroundTask(shutil.rmtree, work_dir, True),
        )
    except BaseException:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise


if __name__ == "__main__":
    import uvicorn

    print(f"RadRobin TotalSegmentator server (TotalSegmentator {TS_VERSION}) on http://{HOST}:{PORT}")
    print(f"Accepting requests from: {', '.join(ALLOWED_ORIGINS)}")
    uvicorn.run(app, host=HOST, port=PORT)
