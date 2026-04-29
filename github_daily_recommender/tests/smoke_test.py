import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "github_daily_recommender.py"

def run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + args, cwd=ROOT, capture_output=True, text=True, timeout=60)

def test_dry_run():
    r = run(["--mode", "daily", "--dry-run"])
    assert r.returncode == 0

def test_modes_dryrun_fast():
    cases = [
        ["--mode","daily","--dry-run"],
        ["--mode","topic","--topic","productivity","--dry-run"],
        ["--mode","topic","--topic","windows","--dry-run"],
        ["--mode","topic","--topic","browser","--dry-run"],
        ["--mode","topic","--topic","file_management","--dry-run"],
        ["--mode","topic","--topic","daily_life","--dry-run"],
        ["--mode","search","--keyword","clipboard manager","--dry-run"],
    ]
    for c in cases:
        r = run(c)
        assert r.returncode == 0

if __name__ == "__main__":
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("warning: no GITHUB_TOKEN, rate limit risk expected")
