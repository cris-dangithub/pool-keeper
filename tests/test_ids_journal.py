import json

import ids
import journal
import model


def add_source(pool, sid, folder="2026-10-01_cv", sha="ABCDEF123456"):
    """Append a row to the sources index (en layout) and create its folder."""
    idx = pool / "sources" / "INDEX.md"
    text = idx.read_text(encoding="utf-8")
    row = f"| {sid} | 2026-10-01 | `{folder}/` | CV | test | {sha} |"
    head, sep, tail = text.partition("\n## ")
    idx.write_text(head.rstrip("\n") + "\n" + row + "\n\n" + sep.lstrip("\n") + tail, encoding="utf-8")
    (pool / "sources" / folder).mkdir(parents=True, exist_ok=True)


def test_next_id_fresh(en_pool):
    for kind, want in (("S", "S001"), ("J", "J0001"), ("A", "A01"), ("G", "G001"), ("K", "K001")):
        assert model.next_id(en_pool, kind) == want


def test_next_id_after_definitions_and_tags(en_pool):
    add_source(en_pool, "S001")
    assert model.next_id(en_pool, "S") == "S002"
    # a tag used somewhere (even if not yet indexed) is never handed out again
    p = en_pool / "01_profile.md"
    p.write_text(p.read_text(encoding="utf-8") + "- City: Valencia [S001][S007 diploma]\n", encoding="utf-8")
    assert model.next_id(en_pool, "S") == "S008"
    ach = en_pool / "50_achievements.md"
    ach.write_text(ach.read_text(encoding="utf-8").replace(
        "|---|---|---|---|---|\n",
        "|---|---|---|---|---|\n| A01 | x | y | z | [S001] |\n| A02 | x | y | z | [S001] |\n", 1),
        encoding="utf-8")
    assert model.next_id(en_pool, "A") == "A03"
    rules = en_pool / "65_writing_style" / "02_active_rules.md"
    rules.write_text(rules.read_text(encoding="utf-8") + "\n### G001 — Header\n- Rule: x\n", encoding="utf-8")
    assert model.next_id(en_pool, "G") == "G002"  # the G### inside the format code block is ignored


def test_find_tags_variants():
    text = "a [S001][S005] b [S002 diploma] c [S003, S004] d [see S009] e `[S010]` f [J0012]"
    assert [t for t, _ in model.find_tags(text)] == ["S001", "S005", "S002", "S003", "S004", "J0012"]


def test_hash_duplicate(en_pool, capsys, tmp_path):
    f = tmp_path / "cv.txt"
    f.write_bytes(b"hello")
    full = ids.sha256(f)
    add_source(en_pool, "S001", sha=full[:12])
    ids.main(["hash", str(f)])
    out = json.loads(capsys.readouterr().out)
    assert out[0]["duplicate_of"] == "S001" and out[0]["short"] == full[:12]


def test_journal_add_orders_days_and_ids(en_pool, capsys):
    journal.main(["tags", "--add", "interview", "--definition", "Candidate interview",
                  "--aliases", "interviews,entrevista"])
    journal.main(["add", "--date", "2026-10-09", "--desc", "Interviewed candidates for the waiter role",
                  "--original", "hoy entrevisté a 3 candidatos", "--tag", "entrevista", "--qty", "3",
                  "--unit", "interviews", "--context", "@2025_acme"])
    journal.main(["add", "--date", "2026-10-07", "--desc", "Wrote onboarding checklist",
                  "--original", "I wrote the onboarding checklist", "--tag", "onboarding",
                  "--recorded", "2026-10-09", "--context", "2025_acme"])
    journal.main(["add", "--date", "2026-10-09", "--desc", "Cycling 20 km", "--original", "bici 20 km",
                  "--tag", "sport", "--context", "personal"])
    capsys.readouterr()
    text = (en_pool / "55_journal" / "2026-10.md").read_text(encoding="utf-8")
    assert text.index("## 2026-10-07 (Wednesday)") < text.index("## 2026-10-09 (Friday)")
    assert ("- **J0001** · Interviewed candidates for the waiter role · #interview · @2025_acme"
            " · qty: 3 interviews") in text
    assert "rec: 2026-10-09" in text
    entries = model.journal_entries(en_pool)
    assert [e.id for e in entries] == ["J0002", "J0001", "J0003"]  # file order follows dates
    assert entries[1].original == "hoy entrevisté a 3 candidatos"
    assert model.next_id(en_pool, "J") == "J0004"


def test_journal_stats(en_pool, capsys):
    journal.main(["tags", "--add", "interview", "--aliases", "entrevista"])
    for d, q in (("2026-09-30", 2), ("2026-10-02", 3), ("2026-10-09", 1)):
        journal.main(["add", "--date", d, "--desc", "Interviews", "--original", "x", "--tag", "entrevista",
                      "--qty", str(q), "--unit", "interviews", "--context", "2025_acme"])
    journal.main(["add", "--date", "2026-10-09", "--desc", "Release", "--original", "y", "--tag", "deploy",
                  "--context", "github:acme/api"])
    capsys.readouterr()
    journal.main(["stats", "--tag", "interview", "--json"])
    r = json.loads(capsys.readouterr().out)
    assert r["total"]["entries"] == 3 and r["total"]["qty_by_unit"] == {"interviews": 6}
    assert r["total"]["ids"] == ["J0001", "J0002", "J0003"] and r["phrase"].startswith("at least 3")
    journal.main(["stats", "--from", "2026-10-01", "--to", "2026-10-31", "--group-by", "week", "--json"])
    r = json.loads(capsys.readouterr().out)
    assert r["total"]["entries"] == 3
    assert set(r["groups"]) == {"2026-W40", "2026-W41"} and r["groups"]["2026-W41"]["entries"] == 2
    journal.main(["stats", "--context", "github:", "--json"])
    assert json.loads(capsys.readouterr().out)["total"]["ids"] == ["J0004"]
    journal.main(["stats", "--group-by", "tag", "--json"])
    r = json.loads(capsys.readouterr().out)
    assert r["groups"]["interview"]["entries"] == 3 and r["groups"]["deploy"]["entries"] == 1
