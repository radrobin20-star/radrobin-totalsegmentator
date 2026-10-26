# RadRobin + TotalSegmentator

Run [TotalSegmentator](https://github.com/wasserth/TotalSegmentator) on your own GPU and see the results in the [RadRobin](https://radrobin.com) browser viewer: select a CT series, press **f**, and get 117 named structures you can review, edit in 2D and 3D, and save as DICOM SEG.

- **Private by design.** The viewer runs in your browser and sends the scan only to the server you choose, normally your own computer. Nothing goes to RadRobin.
- **No install for the viewer.** Open the [RadRobin beta viewer](https://radrobin.com/viewer/beta.html) and load DICOM from a folder or a DICOMweb server.
- **A small, documented API.** `server.py` is about 150 lines, and [API.md](API.md) describes everything the viewer expects.

https://github.com/user-attachments/assets/b2851f1c-3e51-4787-9910-f2bc0d3839d5

## Try it without installing anything

Two abdominal CT scans with ready-made TotalSegmentator segmentations are attached to the [sample-data-v1 release](../../releases/tag/sample-data-v1).

| File | Scan | Slices |
|---|---|---|
| `kits_case_1.zip` | C4KC-KiTS `002` | `261` |
| `kits_case_2.zip` | C4KC-KiTS `003` | `270` |

1. Download a zip and unzip it. It contains the DICOM series and the DICOM SEG.
2. Open the [RadRobin viewer](https://radrobin.com/viewer/index.html), click **Select Folder** and choose the case folder.

**Sample data license:** CT images from the C4KC-KiTS collection, The Cancer Imaging Archive, licensed [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), unchanged. Please cite Heller N, et al. *Data from C4KC-KiTS*, TCIA, 2019, https://doi.org/10.7937/TCIA.2019.IX49E8NX, and Clark K, et al. *The Cancer Imaging Archive (TCIA)*, J Digit Imaging 2013, https://doi.org/10.1007/s10278-013-9622-7. Follow the [TCIA Data Usage Policy](https://wiki.cancerimagingarchive.net/x/c4hF) and do not attempt to identify the patients. Segmentations were created with TotalSegmentator `VERSION 2.13.0` (`total` task, `standard` mode) in RadRobin, are shared under CC BY 3.0, and have not been reviewed by a radiologist.

## Run the server

You need a working Python 3.10+ environment, and ideally an NVIDIA GPU with a recent driver. **Installing TotalSegmentator, PyTorch and GPU drivers is up to you;** see the [TotalSegmentator installation guide](https://github.com/wasserth/TotalSegmentator#installation). If you already run TotalSegmentator, you only need three more packages.

```
pip install -r requirements.txt
python server.py
```

The server listens on `http://127.0.0.1:8080`, this computer only. It accepts requests only from `https://radrobin.com`.

Then check it:

```
python test_server.py
```

`test_server.py` checks the server answers, that TotalSegmentator is version 2.x, that the browser will be allowed to connect, and runs a small test segmentation. The first segmentation downloads the model weights, about 1-2 GB, so it can take several minutes.

## Use it from the viewer

1. Start `server.py` on the same computer as your browser.
2. Open the [RadRobin beta viewer](https://radrobin.com/viewer/beta.html) and load a CT.
3. In review mode, select a series and press **F**. The viewer sends it to `http://localhost:8080`, and the structures appear as a segmentation you can review, edit and save as DICOM SEG.

The beta viewer always connects to `localhost:8080`. To use a GPU on another machine, see [A server on another machine](#a-server-on-another-machine).

## Settings

Environment variables, all optional:

| Variable | Default | What it does |
|---|---|---|
| HOST | 127.0.0.1 (0.0.0.0 inside WSL) | Address to listen on. Set 0.0.0.0 elsewhere only behind a firewall. |
| `PORT` | `8080` | Port. Keep 8080: the viewer connects to this port. |
| `ALLOWED_ORIGINS` | `https://radrobin.com,https://www.radrobin.com` | Websites allowed to call the server from a browser, comma-separated. |
| `TS_DEVICE` | auto | `gpu`, `cpu` or `mps`. |
| `TS_BIN` | next to the Python running the server, else on PATH | Path to the `TotalSegmentator` command. |
| `MAX_UPLOAD_MB` | `0 (no limit)` | Largest accepted upload. |

Example: `PORT=8080 TS_DEVICE=gpu python server.py`

### Windows with WSL

If TotalSegmentator runs in Ubuntu under WSL, start the server inside Ubuntu as usual. It detects WSL and listens on `0.0.0.0`, so the Windows browser can reach it at `http://localhost:8080`. WSL's network is reachable only from your own Windows computer.

You don't need to activate your Python environment first: running it as `~/your_env/bin/python server.py` is enough, and the server finds TotalSegmentator in the same environment.

On some Ubuntu versions `/tmp` is limited to about 2 GB, which is too small for installing PyTorch. If `pip install` fails with "No space left on device", run `export TMPDIR=~/tmp && mkdir -p ~/tmp` first.

### A server on another machine

If the GPU is on another machine, such as a lab server, run `server.py` there and connect with an SSH tunnel from your own computer:

```
ssh -L 8080:localhost:8080 you@gpu-server
```

Keep that window open. The viewer talks to `localhost:8080` as usual, and SSH carries the traffic, encrypted, to the GPU server. Details: [docs/remote-gpu-server.md](docs/remote-gpu-server.md).

## Privacy and security

- The server deletes each scan and mask right after it answers. It keeps no logs of images.
- The viewer converts the series to NIfTI before sending it. NIfTI carries no DICOM patient fields such as name, ID or dates, but the images themselves are sent; a head CT can still show the face.
- By default the server is reachable only from your own computer.

## Credit, license and disclaimer

- Segmentation is done by **TotalSegmentator** (Wasserthal et al., University Hospital Basel). If you use the results in research, please cite: Wasserthal J, et al. *TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images.* Radiology: Artificial Intelligence, 2023. https://doi.org/10.1148/ryai.230024
- The server uses only TotalSegmentator's open `total` task. Some other TotalSegmentator tasks require a license from its authors.
- The code in this repository is MIT licensed ([LICENSE](LICENSE)). The sample data has its own license, given above under "Try it without installing anything".
- **Provided as is, without support or warranty. You install and run it yourself.** RadRobin and TotalSegmentator are research tools and are not cleared for clinical use or diagnosis.

Questions and custom development: `info@radrobin.com` · [radrobin.com](https://radrobin.com)
