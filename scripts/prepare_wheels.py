"""Maintainer tool: download offline wheels; ordinary users never run this."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    target = ROOT / "vendor" / "wheels"
    target.mkdir(parents=True, exist_ok=True)
    for version in ("310", "311", "312", "313", "314"):
        subprocess.run([
            sys.executable, "-m", "pip", "--isolated", "download",
            "--index-url", "https://pypi.org/simple", "--only-binary=:all:",
            "--platform", "win_amd64", "--implementation", "cp",
            "--python-version", version, "--abi", "cp" + version,
            "--dest", str(target), "-r", str(ROOT / "requirements-offline.txt"),
        ], check=True)
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(target.glob("*.whl"))}
    (target / "SHA256.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
