import json
import subprocess
import shutil
import sys
import os
from pathlib import Path



DAFNY_TARGETS = [
    
    "specs/dafny",   # folder: will verify all *.dfy inside
]

SEMGRP_CONFIG = "semgrep/semgrep.yml"
SUPPORTED_SEMGREP_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".dfy"}

ARTIFACTS_DIR = Path("artifacts")
DAFNY_LOG = ARTIFACTS_DIR / "dafny.log"
SEMGRP_JSON = ARTIFACTS_DIR / "semgrep.json"


def _collect_dafny_files(targets: list[str]) -> list[str]:
    files: list[str] = []
    for t in targets:
        p = Path(t)
        if p.is_file() and p.suffix == ".dfy":
            files.append(str(p))
        elif p.is_dir():
            files.extend(str(x) for x in sorted(p.rglob("*.dfy")))
    # Deduplicate while preserving order
    seen = set()
    out = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out

#AI assistance used to write below code dafny, but manually reveiwed and edited.
def run_dafny() -> bool:
    """
    Runs Dafny verification on configured .dfy files.
    Writes combined output to artifacts/dafny.log
    Returns True on success, False on failure.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    dfy_files = _collect_dafny_files(DAFNY_TARGETS)
    if not dfy_files:
        print("[GATE] No Dafny files found. Skipping Dafny.")
        DAFNY_LOG.write_text("[GATE] No Dafny files found. Skipped.\n", encoding="utf-8")
        return True

    # AI assistance used to write below code. Checks for dafny on PATH and provide actionable guidance if missing.
    if shutil.which("dafny") is None:
        msg = (
            "[GATE] dafny not found on PATH.\n"
            "Install Dafny and ensure the 'dafny' command is on your PATH.\n\n"
            "Common install options:\n"
            "- Homebrew (if available): brew install dafny\n"
            "- .NET global tool: dotnet tool install -g dafny\n"
            "  then add to PATH: export PATH=\"$PATH:$HOME/.dotnet/tools\"\n"
            "- Download a release: https://github.com/dafny-lang/dafny/releases\n\n"
            "After installing, verify with: dafny --version\n"
        )
        print(msg, file=sys.stderr)
        DAFNY_LOG.write_text(msg + "\n", encoding="utf-8")
        return False

    ver = subprocess.run(["dafny", "--version"], capture_output=True, text=True)

    header = f"[GATE] Dafny version:\n{ver.stdout.strip() or ver.stderr.strip()}\n\n"
    print(header.strip())

    # Verify all files in one command (faster, single log)
    cmd = ["dafny", "verify", *dfy_files]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    log_text = header
    log_text += "[GATE] Dafny command:\n" + " ".join(cmd) + "\n\n"
    log_text += "[GATE] Dafny stdout:\n" + (proc.stdout or "") + "\n"
    log_text += "[GATE] Dafny stderr:\n" + (proc.stderr or "") + "\n"
    DAFNY_LOG.write_text(log_text, encoding="utf-8")

    if proc.returncode != 0:
        print(f"[GATE] Dafny FAIL (return code {proc.returncode}). See {DAFNY_LOG}", file=sys.stderr)
        return False

    print("[GATE] Dafny PASS")
    return True

#AI assistance used to write below code dafny, but manually reveiwed and edited.
def run_semgrep() -> tuple[bool, int]:
    """
    Runs Semgrep using semgrep/semgrep.yml
    In GitHub Actions (CI=true), scans only changed files in the push/PR.
    Locally, scans the entire repo.
    Writes JSON output to artifacts/semgrep.json
    Returns (ok, error_count)
    ok=False means Semgrep couldn't run or output couldn't be parsed.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Get changed files when possible, otherwise scan entire repo.
    scan_targets: list[str] = []
    changed_files_detected = False

    def write_empty_semgrep_result() -> None:
        SEMGRP_JSON.write_text(
            json.dumps({"results": [], "errors": [], "paths": {"scanned": []}}),
            encoding="utf-8",
        )

    def try_diff(range_spec: str) -> tuple[bool, list[str]]:
        proc = subprocess.run(
            ["git", "diff", "--name-only", range_spec],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return (False, [])

        files = [line for line in proc.stdout.splitlines() if line.strip()]
        return (True, files)

    try:
        is_ci = os.getenv("CI") == "true"
        event_name = os.getenv("GITHUB_EVENT_NAME", "")
        base_ref = (os.getenv("GITHUB_BASE_REF") or "").strip()
        default_branch = (os.getenv("GITHUB_DEFAULT_BRANCH") or "").strip()
        ref_name = (os.getenv("GITHUB_REF_NAME") or "").strip()
        event_before = (os.getenv("GITHUB_EVENT_BEFORE") or "").strip()

        diff_candidates: list[tuple[str, str]] = []

        if is_ci and event_name == "pull_request" and base_ref:
            diff_candidates.append(
                (f"origin/{base_ref}...HEAD", f"pull request changes against {base_ref}")
            )
        elif is_ci and event_name == "push":
            if default_branch and ref_name and ref_name != default_branch:
                diff_candidates.append(
                    (
                        f"origin/{default_branch}...HEAD",
                        f"branch changes against {default_branch}",
                    )
                )

            if event_before and event_before != "0000000000000000000000000000000000000000":
                diff_candidates.append(
                    (f"{event_before}..HEAD", "the commits included in this push")
                )

        for range_spec, description in diff_candidates:
            diff_ok, changed_files = try_diff(range_spec)
            if diff_ok:
                changed_files_detected = True
                scan_targets = changed_files
                print(f"[GATE] Using diff range {range_spec} for {description}")
                break

        # If the baseline ref is missing, try fetching just enough history and retry.
        if diff_candidates and not changed_files_detected:
            try:
                remotes = subprocess.run(["git", "remote"], capture_output=True, text=True)
                if remotes.returncode == 0 and "origin" in (remotes.stdout or ""):
                    print("[GATE] Attempting to fetch additional history to compute diffs")
                    fetch_target = base_ref or default_branch
                    if fetch_target:
                        subprocess.run(
                            ["git", "fetch", "origin", fetch_target, "--depth=50"],
                            check=False,
                        )
                    else:
                        subprocess.run(["git", "fetch", "origin", "--depth=50"], check=False)

                    for range_spec, description in diff_candidates:
                        diff_ok, changed_files = try_diff(range_spec)
                        if diff_ok:
                            changed_files_detected = True
                            scan_targets = changed_files
                            print(f"[GATE] Using diff range {range_spec} for {description}")
                            break
            except Exception:
                pass

        if changed_files_detected:
            scan_targets = [
                f
                for f in scan_targets
                if Path(f).suffix in SUPPORTED_SEMGREP_EXTS and Path(f).exists()
            ]
            if scan_targets:
                print(f"[GATE] Scanning {len(scan_targets)} changed file(s)")
            else:
                print("[GATE] No changed Semgrep-supported files detected. Skipping Semgrep.")
                write_empty_semgrep_result()
                return (True, 0)
    except Exception as e:
        print(f"[GATE] Warning: Error detecting changed files: {e}, will scan all files", file=sys.stderr)

    # If no diff could be determined, fall back to a full scan.
    if not changed_files_detected:
        print("[GATE] Scanning all files in repo")
        scan_targets = []  # Empty list = scan current directory

    cmd = ["semgrep", "scan", "--config", SEMGRP_CONFIG, "--json"]
    if scan_targets:
        cmd.extend(scan_targets)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print("[GATE] semgrep not found on PATH.", file=sys.stderr)
        return (False, 0)

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    if not stdout:
        print("[GATE] Semgrep produced no JSON output.", file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr)
        return (False, 0)

    SEMGRP_JSON.write_text(stdout, encoding="utf-8")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        print("[GATE] Semgrep output was not valid JSON.", file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr)
        return (False, 0)

    results = data.get("results", [])
    error_count = 0
    for r in results:
        sev = (r.get("extra", {}) or {}).get("severity", "")
        if str(sev).upper() == "ERROR":
            error_count += 1

    print(f"[GATE] Semgrep findings: {len(results)} total, {error_count} ERROR")

    # If semgrep itself had issues, show stderr for debugging, but gate is still on ERROR count
    if proc.returncode != 0 and stderr:
        print("[GATE] Semgrep stderr:", file=sys.stderr)
        print(stderr, file=sys.stderr)

    return (True, error_count)


def main() -> int:
    overall_ok = True

    # 1) Dafny
    dafny_ok = run_dafny()
    if not dafny_ok:
        overall_ok = False

    # 2) Semgrep
    semgrep_ok, semgrep_error_count = run_semgrep()
    if not semgrep_ok:
        overall_ok = False
    elif semgrep_error_count > 0:
        overall_ok = False

    if overall_ok:
        print("[GATE] PASS")
        return 0

    print("[GATE] FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
