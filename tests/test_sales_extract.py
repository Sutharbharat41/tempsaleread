import os
import sys
from pathlib import Path
import pytest
import pandas as pd

# make workspace root importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import sales_extract


def test_missing_folder(tmp_path):
    # use a path that definitely doesn't exist
    p = tmp_path / "no_such_dir"
    with pytest.raises(FileNotFoundError):
        sales_extract.process_folder(p)


def test_empty_folder(tmp_path):
    # create empty directory
    p = tmp_path / "empty"
    p.mkdir()
    df = sales_extract.process_folder(p)
    # should return an empty dataframe
    assert isinstance(df, pd.DataFrame)
    assert df.empty


# We cannot easily simulate pdf parsing without real files, but we can at least
# assert that the function skips non-pdf files.
def test_non_pdf_ignored(tmp_path, monkeypatch):
    p = tmp_path / "mixed"
    p.mkdir()
    # create dummy txt file
    with open(p / "foo.txt", "w") as f:
        f.write("hello")
    # monkeypatch extract_text_from_pdf to raise if called
    monkeypatch.setattr(sales_extract, "extract_text_from_pdf", lambda path: (_ for _ in ()).throw(AssertionError("should not be called")))
    df = sales_extract.process_folder(p)
    assert df.empty
