"""Capture file contents and fingerprints for later invalidation."""
import hashlib
from pathlib import Path
import subprocess

def git_commit(path):
    path = Path(path).resolve()
    try:
        result = subprocess.run(["git", "-C", str(path if path.is_dir() else path.parent), "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=5)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None

def snapshot_file(path, include_content=True):
    path = Path(path).expanduser().resolve()
    exists = path.is_file()
    result = {"path": str(path), "exists": exists, "sha256": None, "commit": git_commit(path)}
    if exists:
        data = path.read_bytes()
        result["sha256"] = hashlib.sha256(data).hexdigest()
        if include_content:
            result["content"] = data.decode("utf-8", errors="replace")
    return result

def read_files(paths):
    return [snapshot_file(path) for path in paths]

def changed(snapshot):
    current = snapshot_file(snapshot["path"], include_content=False)
    return any(current.get(k) != snapshot.get(k) for k in ("exists", "sha256", "commit"))
