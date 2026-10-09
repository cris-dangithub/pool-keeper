import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "pool-keeper"
sys.path.insert(0, str(SKILL / "scripts"))
FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
EXAMPLES = ROOT / "examples"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Never touch the real ~/.pool-keeper registry or an env-selected pool."""
    monkeypatch.setenv("POOL_KEEPER_HOME", str(tmp_path / "_home"))
    monkeypatch.delenv("POOL_KEEPER_POOL", raising=False)
    return tmp_path / "_home"


def make_pool(root, lang="en", name="Test Person", domains="", extra=()):
    import pool  # noqa: PLC0415
    args = ["init", "--root", str(root), "--name", name, "--ui-language", lang,
            "--pool-language", lang, "--no-skill-path"]
    if domains:
        args += ["--domains", domains]
    pool.main(args + list(extra))
    return pathlib.Path(root)


@pytest.fixture
def en_pool(tmp_path, monkeypatch):
    root = make_pool(tmp_path / "pool-en", "en", "Noa Example")
    monkeypatch.chdir(root)
    return root
