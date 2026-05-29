from __future__ import annotations

from types import SimpleNamespace

from pindou.services import storage_util


def test_ensure_storage_dirs_creates_static_mount_dirs_in_cos_mode(tmp_path, monkeypatch) -> None:
    settings = SimpleNamespace(
        data_dir=tmp_path / "data",
        upload_dir=tmp_path / "data" / "uploads",
        preview_dir=tmp_path / "data" / "previews",
        pattern_dir=tmp_path / "data" / "patterns",
        thumbnail_dir=tmp_path / "data" / "thumbnails",
    )
    monkeypatch.setattr(storage_util, "get_settings", lambda: settings)

    storage_util.ensure_storage_dirs()

    assert settings.upload_dir.is_dir()
    assert settings.preview_dir.is_dir()
    assert settings.pattern_dir.is_dir()
    assert settings.thumbnail_dir.is_dir()
