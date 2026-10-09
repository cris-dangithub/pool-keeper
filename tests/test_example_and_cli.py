import json
import subprocess
import sys

import common
import lint
from conftest import EXAMPLES, SKILL

PK = str(SKILL / "pk.py")


def test_example_pool_is_clean():
    pool = EXAMPLES / "sample-pool"
    r = lint.lint(pool)
    assert r["errors"] == [] and r["warnings"] == []
    cfg = common.load_config(pool)
    assert cfg["person"]["name"] == "Maren Okafor" and cfg["show_skill_path"] is False
    assert (pool / ".pool-keeper" / "manager" / "SKILL.md").is_file()


def test_launcher_find_and_unknown_command(isolated_home):
    r = subprocess.run([sys.executable, PK, "find", "--pool", str(EXAMPLES / "sample-pool")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and json.loads(r.stdout)["status"] == "ok"
    r = subprocess.run([sys.executable, PK, "nope"], capture_output=True, text=True)
    assert r.returncode == 2


def test_launcher_no_pool_exit_code(tmp_path, isolated_home):
    r = subprocess.run([sys.executable, PK, "lint"], capture_output=True, text=True, cwd=tmp_path,
                       env={**__import__("os").environ, "POOL_KEEPER_HOME": str(isolated_home)})
    assert r.returncode == 3 and "NO_POOL" in r.stderr


def test_lint_weekday_mismatch(en_pool):
    j = en_pool / "55_journal"
    (j / "2026-09.md").write_text('# Activity journal — 2026-09\n\n## 2026-09-30 (Tuesday)\n'
                                  '- **J0001** · Cycling · #sport\n  - Original: "bici"\n', encoding="utf-8")
    r = lint.lint(en_pool)
    assert any("2026-09-30 is Wednesday" in w for w in r["warnings"])
