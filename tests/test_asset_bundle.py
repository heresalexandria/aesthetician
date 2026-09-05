"""Portable asset archives and complete catalog coverage (stdlib runner)."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.release import asset_bundle as bundle, pack_assets


class AssetBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.assets = self.root / 'assets'
        for sub in bundle.SUBDIRS:
            (self.assets / sub).mkdir(parents=True)
        (self.assets / 'packs/plate.png').write_bytes(b'plate bytes')
        (self.assets / 'audio-beds/room.wav').write_bytes(b'room bytes')
        self.entries = {
            'picture': {'poster': 'picture.png', 'anim': 'picture.webp', 'audioOnly': False},
            'sound': {'poster': 'sound.png', 'anim': None, 'audioOnly': True},
        }
        for name in ('picture', 'sound'):
            (self.assets / f'thumbs/{name}.png').write_bytes(b'\x89PNG\r\n\x1a\n' + bytes(16))
        (self.assets / 'thumbs/picture.webp').write_bytes(b'RIFF' + bytes(4) + b'WEBP' + bytes(16))
        self.write_index()

    def write_index(self):
        (self.assets / 'thumbs/index.json').write_text(json.dumps({'count': len(self.entries), 'thumbs': self.entries}))

    def verify(self):
        return bundle.verify_assets(self.assets, {'picture', 'sound'})

    def test_catalog_parser_matches_runtime_registry(self):
        from aesthetician.engine.presets import all_presets
        self.assertEqual(bundle.preset_ids(), set(all_presets()))

    def test_sound_only_posters_do_not_require_animation(self):
        self.assertEqual(self.verify(), {'presets': 2, 'posters': 2, 'animations': 1})

    def test_incomplete_manifest_and_missing_images_fail(self):
        (self.assets / 'thumbs/sound.png').unlink()
        with self.assertRaisesRegex(ValueError, 'missing or empty poster'):
            self.verify()
        del self.entries['picture']
        self.write_index()
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            self.verify()

    def test_missing_or_invalid_animation_fails(self):
        anim = self.assets / 'thumbs/picture.webp'
        anim.unlink()
        with self.assertRaisesRegex(ValueError, 'missing or empty anim'):
            self.verify()
        anim.write_bytes(b'not a valid webp image')
        with self.assertRaisesRegex(ValueError, 'image header'):
            self.verify()

    def test_packer_materializes_shared_assets(self):
        shared = self.root / 'shared'
        shared.mkdir()
        (shared / 'texture.png').write_bytes(b'shared texture content')
        (self.assets / 'packs/shared').symlink_to(shared, target_is_directory=True)
        archive = self.root / bundle.FILENAME
        with patch.object(pack_assets, 'ASSETS_DIR', self.assets), \
                patch.object(pack_assets, 'verify_assets', lambda _: self.verify()):
            self.assertEqual(pack_assets.main(['-o', str(archive)]), 0)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        dest = self.root / 'unpacked'
        bundle.unpack(archive, dest, digest)
        self.assertEqual((dest / 'packs/shared/texture.png').read_bytes(), b'shared texture content')
        with tarfile.open(archive) as tar:
            self.assertFalse(any(m.issym() or m.islnk() for m in tar.getmembers()))
            self.assertTrue(all(m.uid == m.gid == 0 and not m.uname and not m.gname
                                for m in tar.getmembers()))
        self.assertEqual(bundle.verify_assets(dest, {'picture', 'sound'})['posters'], 2)
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            bundle.unpack(archive, self.root / 'bad', '0' * 64)

    def test_nonportable_archive_entries_are_rejected(self):
        for name, kind in [('thumbs/link', tarfile.SYMTYPE), ('../outside', tarfile.REGTYPE)]:
            archive = self.root / 'unsafe.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                item = tarfile.TarInfo(name)
                item.type = kind
                item.linkname = '/outside'
                tar.addfile(item, io.BytesIO())
            with self.assertRaisesRegex(ValueError, 'unsafe asset entry'):
                bundle.unpack(archive, self.root / 'unsafe', hashlib.sha256(archive.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
