import shutil
import zipfile

import extract
import journal
import lint
from test_ids_journal import add_source


def joined(r):
    return " | ".join(r["errors"]), " | ".join(r["warnings"])


def test_fresh_pool_is_clean(en_pool):
    r = lint.lint(en_pool)
    assert r["errors"] == [] and r["warnings"] == []


def test_lint_detects_problems(en_pool, capsys):
    add_source(en_pool, "S001")
    add_source(en_pool, "S002", folder="2026-10-02_missing")
    shutil.rmtree(en_pool / "sources" / "2026-10-02_missing")
    exp = en_pool / "10_experience" / "2025_acme.md"
    exp.write_text("# Waiter — Acme\n\n- **Period:** 2025 [S001][S002]\n\n## Original text [S001]\n"
                   "- Served guests.\n", encoding="utf-8")
    p = en_pool / "01_profile.md"
    p.write_text(p.read_text(encoding="utf-8") + "- City [S009] and [J0042]\n", encoding="utf-8")
    ach = en_pool / "50_achievements.md"
    ach.write_text(ach.read_text(encoding="utf-8").replace(
        "|---|---|---|---|---|\n",
        "|---|---|---|---|---|\n| A02 | x | y | z | [S001] |\n| A01 | x | y | z | [S001] |\n"
        "| A02 | dup | y | z | [S001] |\n", 1), encoding="utf-8")
    journal.main(["add", "--date", "2026-10-09", "--desc", "Did a thing", "--original", "x", "--tag", "newtag"])
    j = en_pool / "55_journal" / "2026-10.md"
    j.write_text(j.read_text(encoding="utf-8") + "- **J0002** · no original line · #newtag\n- **Jxx** broken\n",
                 encoding="utf-8")
    capsys.readouterr()
    errs, warns = joined(lint.lint(en_pool))
    assert "orphan tag [S009]" in errs and "orphan tag [J0042]" in errs
    assert "duplicate A02" in errs
    assert "malformed journal entry line" in errs
    assert "A IDs out of order" in warns
    assert "no original-text section for S002" in warns
    assert "S002: folder '2026-10-02_missing' not found" in warns
    assert "J0002: no `Original:` line" in warns
    assert "#newtag" in warns
    assert lint.main([]) == 1


def test_lint_duplicate_journal_id(en_pool, capsys):
    journal.main(["add", "--date", "2026-10-09", "--desc", "One", "--original", "x"])
    j = en_pool / "55_journal" / "2026-10.md"
    j.write_text(j.read_text(encoding="utf-8") + '- **J0001** · Two\n  - Original: "y"\n', encoding="utf-8")
    capsys.readouterr()
    errs, _ = joined(lint.lint(en_pool))
    assert "duplicate J0001" in errs


def test_lint_missing_not_done_section(en_pool):
    oq = en_pool / "90_open_questions.md"
    oq.write_text(oq.read_text(encoding="utf-8").replace("## Asked, never done", "## Something else"),
                  encoding="utf-8")
    errs, _ = joined(lint.lint(en_pool))
    assert "section '## Asked, never done' missing" in errs


def make_docx(path):
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document {w}><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Noa Example</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Backend developer </w:t></w:r><w:r><w:t>in Valencia</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>Cut build time by 40%.</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Python</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>5 years</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
</w:body></w:document>"""
    header = f'<?xml version="1.0"?><w:hdr {w}><w:p><w:r><w:t>Header text</w:t></w:r></w:p></w:hdr>'
    footer = f'<?xml version="1.0"?><w:ftr {w}><w:p><w:r><w:t>Footer text</w:t></w:r></w:p></w:ftr>'
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            'Target="https://linkedin.com/in/noa-example" TargetMode="External"/></Relationships>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", doc)
        z.writestr("word/header1.xml", header)
        z.writestr("word/footer1.xml", footer)
        z.writestr("word/_rels/document.xml.rels", rels)


def test_extract_docx(tmp_path, capsys):
    p = tmp_path / "cv.docx"
    make_docx(p)
    text = extract.extract(p)
    assert "# Noa Example" in text
    assert "Backend developer in Valencia" in text
    assert "- Cut build time by 40%." in text
    assert "| Python | 5 years |" in text
    assert "Header text" in text and "Footer text" in text
    assert "https://linkedin.com/in/noa-example" in text
    out = tmp_path / "extracted.txt"
    assert extract.main([str(p), "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == text


def test_extract_unsupported(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF")
    assert extract.main([str(p)]) == 4
