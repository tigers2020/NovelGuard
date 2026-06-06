#!/usr/bin/env python3
"""Generate on-demand ~7200-file library under packaging/fixtures/library-large/generated/."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packaging" / "fixtures" / "library-large" / "manifest.json"
OUT_DIR = ROOT / "packaging" / "fixtures" / "library-large" / "generated"


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate(seed: int, file_count: int) -> Path:
    rng = random.Random(seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for existing in OUT_DIR.rglob("*.txt"):
        existing.unlink()
    stems = [f"novel-{i:04d}" for i in range(file_count - 60)]
    for pair_idx in range(30):
        stem = f"dup-{pair_idx:02d}"
        body = f"duplicate body {pair_idx}\n" + ("x" * rng.randint(200, 800))
        _write_text(OUT_DIR / f"{stem}-a.txt", body)
        _write_text(OUT_DIR / f"{stem}-b.txt", body)
    for cluster in range(10):
        base = f"cluster-{cluster:02d}"
        for suffix in ("", "-v2", "-final"):
            _write_text(
                OUT_DIR / f"{base}{suffix}.txt",
                f"cluster {cluster} variant {suffix}\n" + ("y" * rng.randint(100, 400)),
            )
    written = 30 * 2 + 10 * 3
    for i, stem in enumerate(stems):
        if written >= file_count:
            break
        size = rng.choice([120, 400, 1200, 4000])
        content = hashlib.sha256(f"{seed}:{i}".encode()).hexdigest() + "\n" + ("z" * size)
        _write_text(OUT_DIR / f"{stem}.txt", content)
        written += 1
    return OUT_DIR


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    seed = int(manifest["generator_seed"])
    target = int(manifest["expected_file_count"])
    out = generate(seed, target)
    count = len(list(out.rglob("*.txt")))
    print(json.dumps({"generated": str(out), "file_count": count, "seed": seed}))
    return 0 if count >= target - 50 else 1


if __name__ == "__main__":
    raise SystemExit(main())
