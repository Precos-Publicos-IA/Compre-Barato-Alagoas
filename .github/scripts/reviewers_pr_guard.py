#!/usr/bin/env python3
"""Guard PRs that touch the reviewers file.

Exit codes:
  0  ok (no reviewers change, or add with >=2 existing-reviewer LGTMs)
  10 add pending (need two LGTM from current reviewers)
  20 remove — caller must close the PR
  2  usage / API error
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

LGTM_RE = re.compile(r"\bLGTM\b", re.IGNORECASE)
# Add-reviewer PRs require LGTM specifically (not LGMT).


def parse_names(text: str) -> set[str]:
    names: set[str] = set()
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        names.add(line.lstrip("@").split()[0].lower())
    return names


def api(path: str, token: str, accept: str = "application/vnd.github+json") -> tuple[int, str]:
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "alagoas-reviewers-guard",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def file_at(repo: str, path: str, ref: str, token: str) -> str:
    quoted = urllib.parse.quote(path)
    code, body = api(
        f"/repos/{repo}/contents/{quoted}?ref={urllib.parse.quote(ref)}",
        token,
        accept="application/vnd.github.raw",
    )
    if code == 404:
        return ""
    if code >= 300:
        raise RuntimeError(f"contents {path}@{ref}: HTTP {code}: {body[:200]}")
    return body


def pr_changed_files(repo: str, number: int, token: str) -> list[str]:
    names: list[str] = []
    page = 1
    while True:
        code, body = api(f"/repos/{repo}/pulls/{number}/files?per_page=100&page={page}", token)
        if code >= 300:
            raise RuntimeError(f"pull files: HTTP {code}: {body[:200]}")
        chunk = json.loads(body)
        if not chunk:
            break
        names.extend(f.get("filename", "") for f in chunk)
        if len(chunk) < 100:
            break
        page += 1
    return names


def lgtm_authors(repo: str, number: int, token: str) -> set[str]:
    authors: set[str] = set()
    page = 1
    while True:
        code, body = api(
            f"/repos/{repo}/issues/{number}/comments?per_page=100&page={page}", token
        )
        if code >= 300:
            raise RuntimeError(f"issue comments: HTTP {code}: {body[:200]}")
        chunk = json.loads(body)
        if not chunk:
            break
        for c in chunk:
            login = ((c.get("user") or {}).get("login") or "").lower()
            if login and LGTM_RE.search(c.get("body") or ""):
                authors.add(login)
        if len(chunk) < 100:
            break
        page += 1
    page = 1
    while True:
        code, body = api(f"/repos/{repo}/pulls/{number}/reviews?per_page=100&page={page}", token)
        if code >= 300:
            raise RuntimeError(f"reviews: HTTP {code}: {body[:200]}")
        chunk = json.loads(body)
        if not chunk:
            break
        for r in chunk:
            login = ((r.get("user") or {}).get("login") or "").lower()
            if login and LGTM_RE.search(r.get("body") or ""):
                authors.add(login)
        if len(chunk) < 100:
            break
        page += 1
    return authors


def write_output(**kwargs: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as fh:
        for k, v in kwargs.items():
            fh.write(f"{k}={v}\n")


def main(argv: list[str]) -> int:
    repo = os.environ.get("GITHUB_REPOSITORY") or (argv[1] if len(argv) > 1 else "")
    number_s = os.environ.get("PR_NUMBER") or (argv[2] if len(argv) > 2 else "")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if not repo or not number_s or not token:
        print("usage: GITHUB_REPOSITORY=org/repo PR_NUMBER=N GITHUB_TOKEN=... reviewers_pr_guard.py", file=sys.stderr)
        return 2
    number = int(number_s)

    code, body = api(f"/repos/{repo}/pulls/{number}", token)
    if code >= 300:
        print(f"pull: HTTP {code}: {body[:200]}", file=sys.stderr)
        return 2
    pr = json.loads(body)
    base_sha = pr["base"]["sha"]
    head_sha = pr["head"]["sha"]

    files = pr_changed_files(repo, number, token)
    if "reviewers" not in files:
        print("reviewers file not in this PR — skip")
        write_output(action="skip", reason="reviewers-unchanged")
        return 0

    base_names = parse_names(file_at(repo, "reviewers", base_sha, token))
    head_names = parse_names(file_at(repo, "reviewers", head_sha, token))
    removed = sorted(base_names - head_names)
    added = sorted(head_names - base_names)
    print(f"base={sorted(base_names)} head={sorted(head_names)} added={added} removed={removed}")

    if removed:
        reason = f"removes reviewer(s): {', '.join(removed)}"
        print(f"CLOSE: {reason}")
        write_output(action="close", reason=reason)
        return 20

    if added:
        vouchers = lgtm_authors(repo, number, token) & base_names
        print(f"LGTM from current reviewers: {sorted(vouchers)} (need 2)")
        if len(vouchers) < 2:
            reason = (
                f"adds reviewer(s) {', '.join(added)}; "
                f"{len(vouchers)}/2 LGTM from existing reviewers"
            )
            print(f"BLOCK: {reason}")
            write_output(action="block", reason=reason)
            return 10
        print("OK: two existing reviewers LGTM")
        write_output(action="ok", reason="two-lgtm")
        return 0

    print("reviewers touched but no name add/remove")
    write_output(action="ok", reason="whitespace-or-comment")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
