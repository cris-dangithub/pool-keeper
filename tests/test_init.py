import json

import pytest

import common
import pool as poolcli
from conftest import make_pool


def test_init_en_creates_layout_and_config(en_pool):
    cfg = common.load_config(en_pool)
    assert cfg["person"]["name"] == "Noa Example"
    assert cfg["questions"] == {"policy": "minimal", "max_per_report": 1}
    assert cfg["delegation"]["allowed"] is True
    for key in common.CORE_FILE_KEYS + common.CORE_DIR_KEYS:
        assert (en_pool / cfg["layout"][key].rstrip("/")).exists(), key
    assert not (en_pool / cfg["layout"]["goals"]).exists()  # domains off by default
    for f in en_pool.rglob("*.md"):
        assert "{{" not in f.read_text(encoding="utf-8"), f


@pytest.mark.parametrize("lang,expected", [
    ("es", ["10_experiencia", "55_diario/README.md", "90_preguntas_abiertas.md", "fuentes/INDICE.md",
            "65_estilo_escritura/02_reglas_activas.md", "76_metas.md"]),
    ("id", ["10_pengalaman", "55_jurnal_aktivitas/README.md", "90_pertanyaan_terbuka.md",
            "sources/INDEX.md", "65_gaya_penulisan/02_aturan_aktif.md", "76_tujuan.md"]),
])
def test_init_localised_layouts(tmp_path, lang, expected):
    root = make_pool(tmp_path / f"pool-{lang}", lang, "Persona Ficticia", domains="goals")
    for rel in expected:
        assert (root / rel).exists(), rel
    oq = common.lpath(root, common.load_config(root), "open_questions").read_text(encoding="utf-8")
    heading = common.load_strings(lang)["h_not_done"]
    assert f"## {heading}" in oq
    weekday = common.load_strings(lang)["weekdays"][0]
    assert weekday in ("lunes", "Senin")


def test_instruction_blocks_and_manager_stub(en_pool):
    for name in ("CLAUDE.md", "AGENTS.md"):
        t = (en_pool / name).read_text(encoding="utf-8")
        assert "pool-keeper:start" in t and "delegation mode" in t and "90_open_questions.md" in t
    stub = (en_pool / ".pool-keeper" / "manager" / "SKILL.md").read_text(encoding="utf-8")
    assert stub.startswith("---\nname: pool-keeper")
    assert "Updates allowed: **yes**" in stub and "Asked, never done" in stub


def test_block_keeps_user_content_and_refresh_is_idempotent(en_pool):
    p = en_pool / "CLAUDE.md"
    p.write_text("# My notes\nkeep me\n\n" + p.read_text(encoding="utf-8"), encoding="utf-8")
    poolcli.main(["config", "set", "ui_language=es"])
    poolcli.main(["refresh"])
    t = p.read_text(encoding="utf-8")
    assert "keep me" in t and t.count("pool-keeper:start") == 1 and "Spanish" in t


def test_enable_domain_later_creates_file(en_pool):
    poolcli.main(["config", "set", "domains.goals=true"])
    assert (en_pool / "76_goals.md").is_file()


def test_init_refuses_twice_and_non_empty(tmp_path):
    root = make_pool(tmp_path / "p")
    with pytest.raises(SystemExit):
        make_pool(root)
    other = tmp_path / "existing"
    (other / "10_experience").mkdir(parents=True)
    with pytest.raises(SystemExit):
        make_pool(other)


def test_custom_layout_json(tmp_path):
    custom = tmp_path / "pt.json"
    custom.write_text(json.dumps({"profile": "01_perfil.md", "experience": "10_experiencia/",
                                  "open_questions": "90_perguntas_abertas.md"}), encoding="utf-8")
    root = make_pool(tmp_path / "pt", "pt", "Pessoa", extra=["--layout-json", str(custom)])
    assert (root / "90_perguntas_abertas.md").is_file()
    assert (root / "30_skills.md").is_file()  # missing keys fall back to English


def test_discovery_env_walk_registry(tmp_path, monkeypatch):
    a = make_pool(tmp_path / "a", name="Ana One")
    b = make_pool(tmp_path / "b", name="Bo Two")
    sub = a / "10_experience"
    assert common.find_pool(start=sub)["pool"] == str(a.resolve())
    monkeypatch.chdir(tmp_path)
    r = common.find_pool(start=tmp_path)
    assert r["status"] == "AMBIGUOUS" and {c["name"] for c in r["candidates"]} == {"ana-one", "bo-two"}
    assert common.find_pool("bo-two")["pool"] == str(b.resolve())
    monkeypatch.setenv("POOL_KEEPER_POOL", str(a))
    assert common.find_pool(start=tmp_path)["pool"] == str(a.resolve())
