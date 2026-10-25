# Using a GPU on another machine

The RadRobin beta viewer always sends segmentation requests to `http://localhost:8080`, on the computer where the browser runs. To use a GPU on another machine, such as a lab or cloud GPU server, forward that port with an SSH tunnel. Nothing changes in the viewer.

## 1. On the GPU server

Install TotalSegmentator and this repository's requirements, then start the server on its default address, which is reachable only from the server itself:

```
python server.py
```

## 2. On your own computer

Open a terminal (Command Prompt or PowerShell on Windows) and run:

```
ssh -L 8080:localhost:8080 you@gpu-server
```

Log in as you normally do, and keep this window open while you use the viewer. SSH is built into Windows 10 and 11, macOS and Linux.

## 3. Check and use it

On your own computer:

```
python test_server.py
```

It should report PASS for each check. Then open the viewer, select a series and press **F**.

## Notes

- **Port 8080 already in use on your computer:** another program is using it. Stop that program; the viewer only uses port 8080.
- **Different port on the server:** if the server runs on port 9000, use `ssh -L 8080:localhost:9000 you@gpu-server`.
- **Security:** the scan travels inside the encrypted SSH connection, and `server.py` stays invisible to the rest of the network. Each scan and mask is deleted on the server as soon as the answer is sent.
- **Shared servers:** requests are processed one at a time, so other users' scans wait their turn.
