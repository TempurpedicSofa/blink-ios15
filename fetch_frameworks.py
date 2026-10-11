#!/usr/bin/env python3
"""Download the binary xcframeworks listed in xcfs/Package.swift."""
import hashlib
import io
import pathlib
import re
import shutil
import tempfile
import urllib.request
import zipfile

root = pathlib.Path("xcfs")
text = (root / "Package.swift").read_text()
dest = root / ".build" / "artifacts" / "xcfs"
dest.mkdir(parents=True, exist_ok=True)
pat = re.compile(
    r'\(\s*"([^"]+)"\s*,\s*"([0-9a-f]{64})"\s*,\s*"(https://[^"]+)"',
    re.S,
)
found = pat.findall(text)
if len(found) < 10:
    raise SystemExit(f"only found {len(found)} binary targets")

for name, checksum, url in found:
    print(f"GET {name} {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "blink-ios15-build"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    got = hashlib.sha256(data).hexdigest()
    if got != checksum:
        raise SystemExit(f"checksum mismatch {name}: {got}")
    target = dest / f"{name}.xcframework"
    if target.exists():
        shutil.rmtree(target)
    with tempfile.TemporaryDirectory() as tmpname:
        tmp = pathlib.Path(tmpname)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(tmp)
        frames = [
            p for p in tmp.rglob("*.xcframework")
            if p.is_dir() and not any(parent.suffix == ".xcframework" for parent in p.parents)
        ]
        if len(frames) != 1:
            raise SystemExit(f"{name}: expected 1 xcframework, found {frames}")
        shutil.move(str(frames[0]), str(target))
    print(f"OK {target}", flush=True)
