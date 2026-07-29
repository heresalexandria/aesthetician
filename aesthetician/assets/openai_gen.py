"""Generate overlay asset packs with the OpenAI Images API (gpt-image-1).

Reads OPENAI_API_KEY from the environment or a .env file at the repo root.
Never logs the key. Assets are written under assets/packs/ (gitignored).
"""

from __future__ import annotations

import base64
import os
import time
from typing import Callable, Optional

import requests

from .manifest import PACKS, pack_dir, pack_files

API_URL = "https://api.openai.com/v1/images/generations"


def _api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_path = os.path.join(root, ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found in environment or .env")
    return key


def _generate_one(key: str, prompt: str, size: str, quality: str = "medium", retries: int = 4) -> bytes:
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "gpt-image-1", "prompt": prompt, "size": size, "quality": quality, "n": 1},
                timeout=300,
            )
            if resp.status_code == 200:
                return base64.b64decode(resp.json()["data"][0]["b64_json"])
            if resp.status_code in (429, 500, 502, 503):
                time.sleep(4 * (attempt + 1))
                last = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                continue
            raise RuntimeError(f"OpenAI images error {resp.status_code}: {resp.text[:500]}")
        except requests.RequestException as e:  # network hiccup
            last = e
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"image generation failed after {retries} tries: {last}")


def generate_packs(
    only: Optional[str] = None,
    force: bool = False,
    quality: str = "medium",
    log: Callable[[str], None] = print,
) -> None:
    key = _api_key()
    for name, pack in PACKS.items():
        if only and name != only:
            continue
        d = pack_dir(name)
        os.makedirs(d, exist_ok=True)
        have = len(pack_files(name)) if not force else 0
        if have >= pack.count:
            log(f"[assets] {name}: complete ({have}/{pack.count})")
            continue
        log(f"[assets] {name}: generating {pack.count - have} plate(s)…")
        for i in range(have, pack.count):
            prompt = pack.prompts[i % len(pack.prompts)]
            png = _generate_one(key, prompt, pack.size, quality)
            path = os.path.join(d, f"{i:02d}.png")
            with open(path, "wb") as f:
                f.write(png)
            log(f"[assets]   wrote {os.path.relpath(path)}")
    log("[assets] done")
