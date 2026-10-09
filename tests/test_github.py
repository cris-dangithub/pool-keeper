import json

import github
from conftest import FIXTURES

FIX = str(FIXTURES / "github.json")


def commit(msg, files=None, login="noa-dev", parents=1, sha="x" * 40, date="2026-10-09T10:00:00Z"):
    return {"sha": sha, "date": date, "author_login": login, "author_name": "Noa", "author_email": "",
            "message": msg, "parents": parents, "files": files}


def f(name, a=1, d=1):
    return {"filename": name, "status": "modified", "additions": a, "deletions": d}


# --------------------------------------------------------------------------- pure functions
def test_noise_filter():
    assert github.noise_reason(commit("Merge branch 'main' into x")) == "merge"
    assert github.noise_reason(commit("anything", parents=2)) == "merge"
    assert github.noise_reason(commit("Bump lodash", login="dependabot[bot]")) == "bot"
    assert github.noise_reason(commit("update deps", [f("package-lock.json", 900, 800)])) == "lockfile-only"
    assert github.noise_reason(commit("chore(release): 2.0.0", [f("package.json"), f("CHANGELOG.md", 9, 0)])) == "version-bump"
    assert github.noise_reason(commit("v1.2.3")) == "version-bump"
    assert github.noise_reason(commit("style: apply black")) == "formatting-only"
    assert github.noise_reason(commit("Run prettier on src")) == "formatting-only"
    assert github.noise_reason(commit("fix typo", [f("README.md")])) == "typo"
    # real work survives, even when it mentions versions or touches a lockfile among others
    assert github.noise_reason(commit("feat: add login form", [f("src/login.tsx", 80, 0)])) is None
    assert github.noise_reason(commit("feat: upgrade to v2 API", [f("src/api.py", 50, 20), f("poetry.lock")])) is None
    assert github.noise_reason(commit("fix typo that broke the parser", [f("src/parser.py", 120, 80)])) is None


def test_jira_and_tracker_extraction():
    text = "PAY-12 and DATA-77; UTF-8, ISO-8601, SHA-256, CVE-2024-1234 are not tickets; ABC1-9 is"
    assert github.jira_keys(text) == ["PAY-12", "DATA-77", "ABC1-9"]
    urls = github.tracker_urls("see https://acme.atlassian.net/browse/DATA-77. and "
                               "(https://linear.app/acme/issue/PAY-12) https://example.com/blog")
    assert urls == ["https://acme.atlassian.net/browse/DATA-77", "https://linear.app/acme/issue/PAY-12"]


def test_grouping_pr_branch_series():
    cs = [
        dict(commit("feat(auth): a", [f("src/a.py")], sha="a1" * 20, date="2026-10-05T09:00:00Z")),
        dict(commit("fix(auth): b", [f("src/a.py")], sha="a2" * 20, date="2026-10-05T10:00:00Z")),
        dict(commit("refactor(db): pool", [f("src/db.py")], sha="b1" * 20), branch="feat/db"),
        dict(commit("docs: guide", [f("docs/g.md")], sha="c1" * 20)),
        dict(commit("docs: diagram", [f("docs/g.md")], sha="c2" * 20)),
        dict(commit("feat(api): other topic", [f("src/api.py")], sha="d1" * 20)),
    ]
    prs = [{"number": 7, "title": "Auth", "body": "PAY-1", "state": "closed", "merged_at": "2026-10-06",
            "created_at": "2026-10-05", "updated_at": "2026-10-06", "url": "u", "head": "feat/auth",
            "labels": [], "commits": ["a1" * 20, "a2" * 20]}]
    units = github.group_units("o/r", cs, prs)
    kinds = sorted((u["kind"], u["stats"]["commits"]) for u in units)
    assert kinds == [("branch", 1), ("pr", 2), ("series", 1), ("series", 2)]
    pr = next(u for u in units if u["kind"] == "pr")
    assert pr["pr"]["merged"] and pr["jira_keys"] == ["PAY-1"] and pr["branch"] == "feat/auth"
    docs = next(u for u in units if u["kind"] == "series" and u["stats"]["commits"] == 2)
    assert docs["title"].startswith("docs (2 commits")


# --------------------------------------------------------------------------- full sync, offline
def add_source(pool, *extra):
    github.main(["add", "--owner", "noa-dev", "--identity", "noa-dev", "--identity", "noa@example.com",
                 "--exclude", "dotfiles", "--since", "2026-10-01", *extra])


def run_sync(capsys, *args, fixture=FIX):
    capsys.readouterr()
    github.main(["sync", "--fixture", fixture, *args])
    out = json.loads(capsys.readouterr().out)
    return out["runs"][0]


def load_run(pool, run_id):
    return json.loads((pool / ".pool-keeper" / "github" / "runs" / f"{run_id}.json").read_text(encoding="utf-8"))


def test_sync_commit_and_no_duplicates(en_pool, capsys, tmp_path):
    add_source(en_pool)
    r1 = run_sync(capsys)
    run = load_run(en_pool, r1["run"])
    assert run["status"] == "pending" and len(run["units"]) == 6
    assert set(r1["repos"]) == {"noa-dev/api", "noa-dev/site"}  # dotfiles excluded, old repo inactive
    assert r1["repos"]["noa-dev/site"]["private"] is True
    reasons = sorted(x["reason"] for ro in run["repos"] for x in ro["filtered"])
    assert reasons == ["formatting-only", "lockfile-only", "merge", "typo", "version-bump"]
    all_shas = {c["sha"] for u in run["units"] for c in u["commits"]}
    assert not any(s.startswith("c13") for s in all_shas)  # a colleague's commit never counts
    for u in run["units"]:
        assert u["commits"] and all(c["sha"] and c["url"] and c["date"] for c in u["commits"])
    pr7 = next(u for u in run["units"] if u["kind"] == "pr" and u["pr"]["number"] == 7)
    assert pr7["jira_keys"] == ["PAY-12"] and "https://linear.app/acme/issue/PAY-12" in pr7["tracker_urls"]
    csv = next(u for u in run["units"] if any(c["sha"].startswith("c14") for c in u["commits"]))
    assert csv["jira_keys"] == ["DATA-77"]  # matched by e-mail identity; UTF-8 / ISO-8601 ignored
    notes = (en_pool / ".pool-keeper" / "github" / "runs" / r1["run"] / "noa-dev__site.notes.md").read_text(encoding="utf-8")
    assert "🔒 private" in notes and "d100000" in notes

    # the cursor does not move until commit-run: a second sync offers the same units
    r_again = run_sync(capsys)
    assert len(load_run(en_pool, r_again["run"])["units"]) == 6
    github.main(["commit-run", r_again["run"], "--discard"])
    github.main(["commit-run", r1["run"]])
    capsys.readouterr()
    r2 = run_sync(capsys)
    assert r2["units"] == 0

    # --full re-lists everything but flags what is already recorded
    r3 = run_sync(capsys, "--full")
    run3 = load_run(en_pool, r3["run"])
    assert run3["units"] and all(u["already_recorded"] for u in run3["units"])
    github.main(["commit-run", r3["run"], "--discard"])

    # new activity: a new commit + PR #9 merged later -> one series unit and one pr-update
    data = json.loads(open(FIX, encoding="utf-8").read())
    data["commits"]["noa-dev/api"].append(
        {"sha": "c17" + "0" * 37, "date": "2026-10-10T09:00:00Z", "author_login": "noa-dev",
         "author_name": "Noa Example", "author_email": "noa@example.com", "message": "feat: rate limiting",
         "parents": 1, "url": "https://github.com/noa-dev/api/commit/c17",
         "files": [{"filename": "src/limit.py", "status": "added", "additions": 30, "deletions": 0}]})
    pr9 = next(p for p in data["prs"]["noa-dev/api"] if p["number"] == 9)
    pr9.update(state="closed", merged_at="2026-10-10T12:00:00Z", updated_at="2026-10-10T12:00:00Z")
    fix2 = tmp_path / "github2.json"
    fix2.write_text(json.dumps(data), encoding="utf-8")
    r4 = run_sync(capsys, fixture=str(fix2))
    run4 = load_run(en_pool, r4["run"])
    assert sorted(u["kind"] for u in run4["units"]) == ["pr-update", "series"]
    upd = next(u for u in run4["units"] if u["kind"] == "pr-update")
    assert upd["previous_state"] == "open" and upd["pr"]["merged"]
    github.main(["commit-run", r4["run"]])
    capsys.readouterr()
    assert run_sync(capsys, fixture=str(fix2))["units"] == 0


def test_batches_never_overlap(en_pool, capsys):
    add_source(en_pool)
    r1 = run_sync(capsys, "--max-units", "3")
    run1 = load_run(en_pool, r1["run"])
    assert len(run1["units"]) == 3 and run1["remaining_units"] == 3
    github.main(["commit-run", r1["run"]])
    r2 = run_sync(capsys, "--max-units", "3")
    run2 = load_run(en_pool, r2["run"])
    ids1 = {u["unit_id"] for u in run1["units"]}
    ids2 = {u["unit_id"] for u in run2["units"]}
    assert len(ids2) == 3 and not ids1 & ids2 and run2["remaining_units"] == 0
    github.main(["commit-run", r2["run"]])
    assert run_sync(capsys)["units"] == 0


def test_since_today_and_repo_filter(en_pool, capsys):
    add_source(en_pool)
    r = run_sync(capsys, "--since", "2026-10-09", "--repo", "noa-dev/api")
    run = load_run(en_pool, r["run"])
    assert set(r["repos"]) == {"noa-dev/api"}
    assert all(u["date_last"] >= "2026-10-09" for u in run["units"])
    assert github.resolve_since("today") == github.today()
