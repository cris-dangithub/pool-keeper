"""Adopting an existing pool (kept by an older, person-specific skill), ID reservation under a
lock, and journal tokens in the pool language. All data here is fictional."""
import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

import common
import journal
import lint
import model
import pool as poolcli
from conftest import SKILL

INDEX = """# Indeks Sumber

Setiap file yang dilampirkan diarsipkan di `sources/<YYYY-MM-DD>_<nama-file>/`.

| ID | Tanggal masuk | Folder | Jenis | Ringkasan isi | SHA-256 (12 karakter pertama) |
|---|---|---|---|---|---|
| S001 | 2026-10-03 | `2026-10-03_cv-contoh/` | CV (.pdf) | CV fiktif | ABCDEF123456 |
| S002 | 2026-10-03 | `2026-10-03_catatan-chat-jawaban/` | Catatan chat | jawaban fiktif | – |

## Catatan per sumber
### S001 — cv-contoh.pdf
- Fiktif.
"""

FILES = {
    "README.md": "# Knowledge Pool — Sari Contoh\n\nBahan mentah.\n",
    "CLAUDE.md": "# Knowledge Pool — Sari Contoh\n\n- **Bahasa sesi:** selalu jawab dalam Bahasa Indonesia.\n",
    "CHANGELOG.md": "# Changelog\n\n## 2026-10-03 — Ingest S001\n- Baru: profil\n",
    "00_profil.md": "# Profil\n\n## Identitas & kontak\n- **Nama lengkap:** Sari Contoh [S001]\n",
    "10_pengalaman/2024_kafe-contoh.md": "# Barista — Kafe Contoh\n\n## Tugas & tanggung jawab\n- Menyajikan kopi [S001]\n\n## Bullet asli [S001]\n- Served coffee\n",
    "20_pendidikan.md": "# Pendidikan\n",
    "30_keterampilan.md": "# Keterampilan\n- **Latte art** — Kafe Contoh [S002]\n",
    "40_sertifikasi_bahasa.md": "# Sertifikasi & Bahasa\n",
    "50_pencapaian.md": "# Bank Pencapaian\n\n| ID | Pencapaian | Posisi | Angka | Sumber |\n|---|---|---|---|---|\n| A01 | x | y | z | [S001] |\n",
    "55_jurnal_aktivitas/README.md": ("# Jurnal aktivitas\n\n## Kosakata tag\n| Tag | Definisi | Alias |\n"
                                     "|---|---|---|\n| #rekrutmen | Sourcing dan screening | recruitment, hiring |\n"
                                     "| #interview | Wawancara kandidat | wawancara |\n"),
    "60_narasi_positioning.md": "# Narasi\n",
    "65_gaya_penulisan/README.md": "# Gaya Penulisan\n",
    "65_gaya_penulisan/01_pola_teramati.md": "# Pola\n",
    "65_gaya_penulisan/02_aturan_aktif.md": "# Aturan\n\n### G001 — Angka di depan\n- Aturan: x\n",
    "65_gaya_penulisan/03_log_koreksi.md": "# Log\n",
    "70_lainnya.md": "# Lain-lain\n",
    "80_kata_kunci.md": "# Kata kunci\n",
    "90_pertanyaan_terbuka.md": ("# Pertanyaan Terbuka\n\n## Celah informasi\n- [ ] Berapa? [S001]\n\n"
                                 "## Konflik antar sumber\n\n## Ditanyakan, tidak pernah dilakukan\n\n## Terjawab\n"),
    "sources/INDEX.md": INDEX,
    "sources/2026-10-03_cv-contoh/extracted.txt": "CV text\n",
    "sources/2026-10-03_catatan-chat-jawaban/catatan.md": "Q: ... A: ...\n",
    "skill/SKILL.md": "---\nname: sari-knowledge-pool\ndescription: old skill\n---\n# old\n",
    "skill/scripts/extract-docx.ps1": "# old script\n",
    "tracker/tracker_lamaran.html": "<html></html>\n",
}


def build_old_pool(root: pathlib.Path) -> pathlib.Path:
    for rel, text in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    return root


def hashes(root: pathlib.Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and ".pool-keeper" not in p.parts}


ADOPT = ["--name", "Sari Contoh", "--ui-language", "id", "--pool-language", "id", "--no-skill-path",
         "--default-context", "2024_kafe-contoh", "--country", "ID"]


@pytest.fixture
def old_pool(tmp_path):
    return build_old_pool(tmp_path / "Knowledge Pool Sari")


def test_adopt_dry_run_maps_without_writing(old_pool, capsys):
    before = hashes(old_pool)
    poolcli.main(["adopt", "--root", str(old_pool), *ADOPT, "--legacy-skill-dir", "skill", "--dry-run"])
    out = json.loads(capsys.readouterr().out)
    assert out["mapped"]["profile"] == "00_profil.md"
    assert out["mapped"]["journal_readme"] == "55_jurnal_aktivitas/README.md"
    assert out["will_create"] == {"snapshot": "00_ringkasan_cepat.md", "stories": "62_cerita_star.md"}
    assert out["source_notes"] == "catatan.md"
    assert out["unmapped_kept_as_is"] == ["tracker"]
    assert out["not_done_section_present"] is True
    assert hashes(old_pool) == before and not (old_pool / ".pool-keeper").exists()


def test_adopt_keeps_every_file_and_retires_old_skill(old_pool, capsys):
    before = hashes(old_pool)
    poolcli.main(["adopt", "--root", str(old_pool), *ADOPT, "--legacy-skill-dir", "skill"])
    out = json.loads(capsys.readouterr().out)
    after = hashes(old_pool)
    # untouched: every old file except CLAUDE.md (block appended) and the moved legacy skill
    for rel, h in before.items():
        if rel == "CLAUDE.md" or rel.startswith("skill/"):
            continue
        assert after.get(rel) == h, rel
    claude = (old_pool / "CLAUDE.md").read_text(encoding="utf-8")
    assert "selalu jawab dalam Bahasa Indonesia" in claude and claude.count("pool-keeper:start") == 1
    legacy = old_pool / ".pool-keeper" / "legacy" / "sari-knowledge-pool"
    assert (legacy / "SKILL.legacy.md").is_file() and (legacy / "scripts" / "extract-docx.ps1").is_file()
    assert not (old_pool / "skill").exists()
    # the only SKILL.md left in the pool is pool-keeper's manager pointer
    skill_files = [p.relative_to(old_pool).as_posix() for p in old_pool.rglob("SKILL.md")]
    assert skill_files == [".pool-keeper/manager/SKILL.md"]
    assert (old_pool / "00_ringkasan_cepat.md").is_file() and (old_pool / "62_cerita_star.md").is_file()
    assert (old_pool / "tracker" / "tracker_lamaran.html").is_file()
    cfg = common.load_config(old_pool)
    assert cfg["layout"]["profile"] == "00_profil.md" and cfg["layout"]["source_notes"] == "catatan.md"
    assert cfg["adopted"]["legacy_skill"] == ".pool-keeper/legacy/sari-knowledge-pool"
    assert cfg["journal"]["default_context"] == "2024_kafe-contoh"
    assert out["registered_as"] == "sari-contoh"
    r = lint.lint(old_pool)
    assert r["errors"] == [], r["errors"]


def test_adopt_refuses_ambiguous_and_non_pools(tmp_path):
    root = build_old_pool(tmp_path / "amb")
    (root / "02_profil.md").write_text("# Profil lain\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="AMBIGUOUS_LAYOUT"):
        poolcli.main(["adopt", "--root", str(root), *ADOPT])
    poolcli.main(["adopt", "--root", str(root), *ADOPT, "--map", "profile=00_profil.md"])
    assert common.load_config(root)["layout"]["profile"] == "00_profil.md"
    empty = tmp_path / "notes"
    empty.mkdir()
    (empty / "random.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="NOT_A_POOL"):
        poolcli.main(["adopt", "--root", str(empty), *ADOPT])


@pytest.fixture
def adopted(old_pool, monkeypatch, capsys):
    poolcli.main(["adopt", "--root", str(old_pool), *ADOPT, "--legacy-skill-dir", "skill"])
    capsys.readouterr()
    monkeypatch.chdir(old_pool)
    return old_pool


def test_reserve_writes_placeholder_rows(adopted, capsys):
    import ids  # noqa: PLC0415
    ids.main(["next-id", "S", "--reserve", "2026-11-17_cv-baru", "--reserve", "2026-11-17_catatan-chat-x"])
    out = json.loads(capsys.readouterr().out)
    assert [o["id"] for o in out] == ["S003", "S004"]
    rows = model.source_rows((adopted / "sources" / "INDEX.md").read_text(encoding="utf-8"))
    assert [r.id for r in rows] == ["S001", "S002", "S003", "S004"]
    assert rows[2].kind == model.RESERVED_KIND and rows[2].folder == "2026-11-17_cv-baru/"
    assert model.next_id(adopted, "S") == "S005"
    warnings = lint.lint(adopted)["warnings"]
    assert any("S003: reserved but never filled in" in w for w in warnings)


def test_reserve_is_safe_across_processes(adopted):
    env = dict(__import__("os").environ, PYTHONUTF8="1")
    cmd = [sys.executable, str(SKILL / "pk.py"), "next-id", "S", "--pool", str(adopted), "--reserve"]
    procs = [subprocess.Popen(cmd + [f"2026-11-17_src-{i}"], stdout=subprocess.PIPE, env=env, text=True)
             for i in range(6)]
    got = []
    for p in procs:
        out, _ = p.communicate(timeout=60)
        assert p.returncode == 0
        got += [o["id"] for o in json.loads(out)]
    assert sorted(got) == [f"S{n:03d}" for n in range(3, 9)]  # six distinct numbers, no gaps
    rows = model.source_rows((adopted / "sources" / "INDEX.md").read_text(encoding="utf-8"))
    assert len({r.id for r in rows}) == len(rows) == 8
    assert not (adopted / ".pool-keeper" / "ids.lock").exists()


def test_journal_tokens_in_pool_language(adopted, capsys):
    journal.main(["add", "--date", "2026-11-17", "--desc", "Interview kandidat barista",
                  "--original", "hari ini aku interview 3 kandidat barista", "--tag", "wawancara",
                  "--qty", "3", "--unit", "kandidat", "--recorded", "2026-11-18"])
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == "J0001" and out["unknown_tags"] == []
    text = (adopted / "55_jurnal_aktivitas" / "2026-11.md").read_text(encoding="utf-8")
    assert "## 2026-11-17 (Selasa)" in text
    assert "#interview · @2024_kafe-contoh · jumlah: 3 kandidat · dicatat 2026-11-18" in text
    assert '  - Asli: "hari ini aku interview 3 kandidat barista"' in text
    # an entry written with English tokens in the same pool still parses
    (adopted / "55_jurnal_aktivitas" / "2026-11.md").write_text(
        text + '- **J0002** · Rapat · #rekrutmen · qty: 2 jam · rec: 2026-11-18\n  - Original: "rapat 2 jam"\n',
        encoding="utf-8")
    es = {e.id: e for e in model.journal_entries(adopted)}
    assert es["J0001"].qty == 3 and es["J0001"].unit == "kandidat" and es["J0001"].recorded == "2026-11-18"
    assert es["J0001"].original.startswith("hari ini")
    assert es["J0002"].qty == 2 and es["J0002"].recorded == "2026-11-18" and es["J0002"].original == "rapat 2 jam"
    assert lint.lint(adopted)["errors"] == []
