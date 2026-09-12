"""Deployment regressions: open tabs keep their exact build, without private files."""
import hashlib
import json
from pathlib import Path
import pytest
from studio_deploy import retain_static_assets


def release(root, version, files):
    folder = root / version
    hashes = {}
    for name, body in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        hashes[name] = hashlib.sha256(body).hexdigest()
    (folder / 'manifest.json').write_text(json.dumps({'sha256': hashes}))
    return folder


def test_open_tab_dependencies_survive_multiple_releases(tmp_path):
    releases = tmp_path / 'releases'; history = tmp_path / 'history'
    old = release(releases, '20260911000000-studio-v7', {
        'site/studio/studio-assets/Works-old.js': b'import "./index-old.js"',
        'site/studio/studio-assets/index-old.js': b'old application',
        'site/studio/studio-fonts/font-hash.woff2': b'font',
        'service/private.json': b'never serve',
        'site/studio/index.html': b'old html must not be cached here',
    })
    release(releases, '20260912000000-studio-v7', {
        'site/studio/studio-assets/Works-new.js': b'new works',
        'site/studio/studio-fonts/font-hash.woff2': b'font',
    })
    assert retain_static_assets(releases, history) == {'retained': 4, 'added': 4}
    assert retain_static_assets(releases, history) == {'retained': 4, 'added': 0}
    # The retained module dependency chain no longer depends on a release folder.
    (old / 'site/studio/studio-assets/index-old.js').unlink()
    assert (history / 'studio-assets/index-old.js').read_bytes() == b'old application'
    assert not (history / 'index.html').exists()
    assert not (history / 'service').exists()


def test_same_filename_cannot_overwrite_other_build(tmp_path):
    releases = tmp_path / 'releases'; history = tmp_path / 'history'
    path = 'site/studio/studio-assets/Works-hash.js'
    release(releases, '20260911000000-studio-v7', {path: b'original'})
    retain_static_assets(releases, history)
    release(releases, '20260912000000-studio-v7', {path: b'different'})
    with pytest.raises(RuntimeError, match='collision'):
        retain_static_assets(releases, history)
    assert (history / 'studio-assets/Works-hash.js').read_bytes() == b'original'


@pytest.mark.parametrize('tampered', ['source', 'history'])
def test_tampering_aborts_retention(tmp_path, tampered):
    releases = tmp_path / 'releases'; history = tmp_path / 'history'
    path = 'site/studio/studio-assets/Works-hash.js'
    original = release(releases, '20260911000000-studio-v7', {path: b'original'})
    retain_static_assets(releases, history)
    target = original / path if tampered == 'source' else history / 'studio-assets/Works-hash.js'
    target.write_bytes(b'changed')
    with pytest.raises(RuntimeError, match='changed'):
        retain_static_assets(releases, history)


def test_manifest_cannot_escape_public_asset_directory(tmp_path):
    releases = tmp_path / 'releases'; history = tmp_path / 'history'
    release(releases, '20260911000000-studio-v7', {
        'site/studio/studio-assets/../private.js': b'not a public asset',
    })
    with pytest.raises(RuntimeError, match='Unsafe'):
        retain_static_assets(releases, history)
    assert not (history / 'private.js').exists()
