import pytest
from pathlib import Path
from youloader import clean_up_partials

def test_clean_up_partials(tmp_path, monkeypatch):
    # Move current directory to a temp path for safe testing
    monkeypatch.chdir(tmp_path)
    
    # Create dummy files
    (tmp_path / "video.mp4").write_text("data")
    (tmp_path / "temp.part").write_text("data")
    (tmp_path / "download.ytdl").write_text("data")
    
    # Create a subfolder with a partial
    subfolder = tmp_path / "sub"
    subfolder.mkdir()
    (subfolder / "extra.part").write_text("data")
    
    count = clean_up_partials()
    
    assert count == 3
    assert (tmp_path / "video.mp4").exists()
    assert not (tmp_path / "temp.part").exists()
    assert not (subfolder / "extra.part").exists()