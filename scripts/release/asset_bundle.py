"""Fetch and validate the exact asset bundle pinned for this checkout (stdlib only)."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
PIN = Path(__file__).with_name('asset_bundle.json')
FILENAME = 'aesthetician-assets.tar.gz'
SUBDIRS = {'packs', 'thumbs', 'audio-beds'}


def preset_ids() -> set[str]:
    ids = set()
    for source in (ROOT / 'aesthetician/presets').glob('*.py'):
        if source.name.startswith('_'):
            continue
        for node in ast.walk(ast.parse(source.read_text(encoding='utf-8'))):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) \
                    or node.func.id not in ('Preset', '_preset'):
                continue
            value = next((k.value for k in node.keywords if k.arg == 'id'),
                         node.args[0] if node.args else None)
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                ids.add(value.value)
    return ids


def verify_assets(assets: Path, expected: set[str] | None = None) -> dict:
    expected = preset_ids() if expected is None else expected
    for sub in SUBDIRS:
        folder = assets / sub
        if not folder.is_dir() or not any(folder.iterdir()):
            raise ValueError(f'assets/{sub} is missing or empty')
    thumbs = assets / 'thumbs'
    index = json.loads((thumbs / 'index.json').read_text(encoding='utf-8'))
    entries = index['thumbs']
    if not expected or set(entries) != expected or index['count'] != len(expected):
        missing, extra = sorted(expected - set(entries)), sorted(set(entries) - expected)
        raise ValueError(f'Thumbnail coverage mismatch: {len(entries)} entries, {len(expected)} presets; '
                         f'missing={missing[:8]}, extra={extra[:8]}')
    animations = 0
    for pid, entry in entries.items():
        if type(entry.get('audioOnly')) is not bool:
            raise ValueError(f'{pid}: missing audioOnly flag')
        for key in ('poster', 'anim'):
            name = entry.get(key)
            if key == 'anim' and entry['audioOnly'] and name is None:
                continue
            if not isinstance(name, str) or '/' in name or '\\' in name or Path(name).stem != pid:
                raise ValueError(f'{pid}: invalid or missing {key} filename')
            file = thumbs / name
            if not file.is_file() or file.stat().st_size < 16:
                raise ValueError(f'{pid}: missing or empty {key}: {name}')
            with file.open('rb') as stream:
                header = stream.read(12)
            if key == 'poster':
                valid = file.suffix == '.png' and header.startswith(b'\x89PNG\r\n\x1a\n')
            else:
                valid = (file.suffix == '.webp' and header[:4] == b'RIFF' and header[8:12] == b'WEBP') \
                    or (file.suffix == '.gif' and header[:6] in (b'GIF87a', b'GIF89a'))
                animations += 1
            if not valid:
                raise ValueError(f'{pid}: invalid {key} image header')
    return {'presets': len(expected), 'posters': len(entries), 'animations': animations}


def unpack(archive: Path, destination: Path, sha256: str) -> None:
    with archive.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != sha256:
        raise ValueError(f'Asset bundle checksum mismatch: expected {sha256}, got {actual}')
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar.getmembers():
            p = PurePosixPath(member.name)
            if p.is_absolute() or '..' in p.parts or '\\' in member.name \
                    or not p.parts or p.parts[0] not in SUBDIRS \
                    or not (member.isfile() or member.isdir()):
                raise ValueError(f'Nonportable or unsafe asset entry: {member.name}')
        destination.mkdir(parents=True, exist_ok=True)
        tar.extractall(destination, filter='data')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['fetch', 'verify'])
    ap.add_argument('--assets', type=Path, default=ROOT / 'assets')
    ap.add_argument('--repo', default='heresalexandria/aesthetician')
    args = ap.parse_args()
    if args.command == 'fetch':
        if args.assets.exists() and any(args.assets.iterdir()):
            raise ValueError('Fetch needs an empty destination; use --assets with a fresh directory')
        pin = json.loads(PIN.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(prefix='aesthetician-assets-') as tmp:
            subprocess.run(['gh', 'release', 'download', pin['tag'], '--repo', args.repo,
                            '--pattern', FILENAME, '--dir', tmp], check=True)
            staged = Path(tmp) / 'verified'
            unpack(Path(tmp) / FILENAME, staged, pin['sha256'])
            # Check the archive in isolation so stale local files cannot hide
            # omissions. Only copy after every check succeeds.
            result = verify_assets(staged)
            import shutil
            for sub in SUBDIRS:
                shutil.copytree(staged / sub, args.assets / sub, dirs_exist_ok=True)
    else:
        result = verify_assets(args.assets)
    print('Verified asset bundle: ' + ', '.join(f'{n} {key}' for key, n in result.items()))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'Asset bundle failed: {exc}')
