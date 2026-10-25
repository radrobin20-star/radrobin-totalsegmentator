# RadRobin segmentation server API, version 1

The RadRobin viewer talks to a segmentation server over HTTP. Any server that follows this page works with the viewer. `server.py` in this repository is the reference implementation, running [TotalSegmentator](https://github.com/wasserth/TotalSegmentator).

All examples use `http://127.0.0.1:8080`, the default address.

## GET /health

Tells the viewer the server is running and which engine it uses. The viewer calls it before sending any data.

**Response** `200 OK`, JSON:

```json
{
  "status": "ok",
  "api_version": "1",
  "engine": "TotalSegmentator",
  "engine_version": "2.4.0",
  "task": "total",
  "device": "auto",
  "busy": false
}
```

| Field | Meaning |
|---|---|
| `status` | Always `"ok"` when the server can accept work. |
| `api_version` | Version of this API. This page describes `"1"`. |
| `engine`, `engine_version` | The segmentation software and its version. RadRobin needs TotalSegmentator **2.x**: version 1 used different label numbers, and the viewer would show wrong structure names. |
| `task` | The TotalSegmentator task. Version 1 of this API supports only `"total"` (117 structures, CT). |
| `device` | `gpu`, `cpu`, `mps` or `auto`. |
| `busy` | `true` while a segmentation is running. New requests wait their turn. |

```
curl http://127.0.0.1:8080/health
```

## POST /segment

Segments one volume and returns the label mask.

**Request** `multipart/form-data`:

| Field | Required | Value |
|---|---|---|
| `file` | yes | The volume as NIfTI, gzip-compressed (`.nii.gz`) or not (`.nii`). The server detects which from the file's content. CT only. |
| `fast_mode` | no | `"true"` for fast mode (3 mm, quicker, less detailed) or `"false"` for standard mode (1.5 mm). Default `"false"`. |

**Response** `200 OK`, `application/octet-stream`: a NIfTI mask in the same format as the upload, `mask.nii.gz` for a compressed upload or `mask.nii` for an uncompressed one.

- Same grid as the input: same dimensions, voxel spacing and orientation.
- One integer value per voxel: `0` is background, and `1` to `117` are TotalSegmentator v2 `total` structures, numbered as in TotalSegmentator's own class map. Standard and fast mode use the same numbering.

```
curl -F "file=@ct.nii.gz" -F "fast_mode=true" http://127.0.0.1:8080/segment -o mask.nii.gz
```

**Errors**, JSON:

| Status | When | Body |
|---|---|---|
| `413` | The upload is larger than the server's limit, if one is set (`MAX_UPLOAD_MB`; no limit by default). | `{"detail": "File too large"}` |
| `422` | The `file` field is missing. | FastAPI validation details |
| `500` | TotalSegmentator failed, for example an unreadable file or out of GPU memory. | `{"error": "TotalSegmentator failed", "detail": "<last lines of its output>"}` |

Segmentation can take from under a minute (GPU, fast mode) to many minutes (CPU, standard mode). Clients should not time out quickly.

## Browser requirements

The viewer runs in the browser at `https://radrobin.com`, so the server must:

- **Allow the viewer's site (CORS).** Send `Access-Control-Allow-Origin` for `https://radrobin.com` on every response, including the `OPTIONS` preflight.
- **Answer Chrome's private-network check.** When a preflight carries `Access-Control-Request-Private-Network: true`, reply with `Access-Control-Allow-Private-Network: true`.
- **Be reachable at `http://localhost:8080`.** The beta viewer always connects there. Browsers allow an `https` site to call `http://localhost`. A server on another machine is reached through an SSH tunnel; see [docs/remote-gpu-server.md](docs/remote-gpu-server.md).

`server.py` does all three by default.

## Changes to this API

New fields may be added to `/health` and new optional fields to `/segment` without changing the version. Anything that would break existing servers or viewers gets a new `api_version`.
