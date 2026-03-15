#!/usr/bin/env python3
"""
upload_to_github.py

Uploads all project files to GitHub via REST API.
No git CLI needed. Just needs a Personal Access Token.

Usage:
    python3 upload_to_github.py --token YOUR_TOKEN

Get a token: GitHub → Settings → Developer settings →
Personal access tokens → Tokens (classic) → Generate new token
Scope needed: repo (full control)
"""

import os
import sys
import base64
import argparse
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx

OWNER = "aaa7777777777"
REPO  = "Cinemese"
BASE  = f"https://api.github.com/repos/{OWNER}/{REPO}"

# Files and dirs to skip
SKIP_PATTERNS = {
    "node_modules", "__pycache__", ".git", ".DS_Store",
    "*.pyc", "*.pyo", "package-lock.json",
    "context_patch.json", "skill_queue.json",
    "chandler_base.yaml", "stranger_cache.json",
    "*.tar.gz", "*.tar",
}

def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_PATTERNS:
            return True
    name = path.name
    for pat in SKIP_PATTERNS:
        if pat.startswith("*") and name.endswith(pat[1:]):
            return True
    return False

def collect_files(root: Path) -> list[tuple[Path, str]]:
    """Returns list of (local_path, repo_path)."""
    results = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        if should_skip(p):
            continue
        repo_path = str(p.relative_to(root)).replace("\\", "/")
        results.append((p, repo_path))
    return results

def get_existing_sha(client: httpx.Client, repo_path: str, headers: dict) -> str | None:
    """Get existing file SHA (needed to update, not just create)."""
    r = client.get(f"{BASE}/contents/{repo_path}", headers=headers)
    if r.status_code == 200:
        return r.json().get("sha")
    return None

def upload_file(
    client:    httpx.Client,
    local:     Path,
    repo_path: str,
    headers:   dict,
    dry_run:   bool = False,
) -> tuple[bool, str]:
    """Upload one file. Returns (success, message)."""
    try:
        content = base64.b64encode(local.read_bytes()).decode()
    except Exception as e:
        return False, f"read error: {e}"

    if dry_run:
        return True, f"[dry] {repo_path}"

    sha = get_existing_sha(client, repo_path, headers)

    payload: dict = {
        "message": f"upload: {repo_path}",
        "content": content,
    }
    if sha:
        payload["sha"] = sha

    r = client.put(
        f"{BASE}/contents/{repo_path}",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if r.status_code in (200, 201):
        action = "updated" if sha else "created"
        return True, f"{action}: {repo_path}"
    else:
        return False, f"FAILED {r.status_code}: {repo_path} — {r.text[:120]}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--root",  default=".", help="Local project root (default: .)")
    parser.add_argument("--dry",   action="store_true", help="Dry run — list files only")
    parser.add_argument("--delay", type=float, default=0.3, help="Seconds between uploads")
    args = parser.parse_args()

    root    = Path(args.root).resolve()
    headers = {
        "Authorization": f"token {args.token}",
        "Accept":        "application/vnd.github.v3+json",
        "Content-Type":  "application/json",
    }

    print(f"Repo:  {OWNER}/{REPO}")
    print(f"Root:  {root}")
    print(f"Mode:  {'dry run' if args.dry else 'live upload'}")
    print()

    files = collect_files(root)
    print(f"Found {len(files)} files to upload\n")

    ok = 0
    fail = 0

    with httpx.Client() as client:

        # Verify token works
        r = client.get(f"{BASE}", headers=headers)
        if r.status_code == 404:
            print(f"ERROR: repo {OWNER}/{REPO} not found or token lacks access")
            sys.exit(1)
        if r.status_code == 401:
            print("ERROR: token invalid or expired")
            sys.exit(1)
        print(f"Repo accessible. Default branch: {r.json().get('default_branch','?')}\n")

        for i, (local, repo_path) in enumerate(files, 1):
            success, msg = upload_file(client, local, repo_path, headers, args.dry)
            status = "✓" if success else "✗"
            print(f"[{i:3}/{len(files)}] {status} {msg}")
            if success:
                ok += 1
            else:
                fail += 1
            if not args.dry:
                time.sleep(args.delay)   # be gentle with the API

    print(f"\nDone. {ok} uploaded, {fail} failed.")

if __name__ == "__main__":
    main()
