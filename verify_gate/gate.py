import json
import subprocess
import shutil
import sys
from pathlib import Path


# ---- Config (edit if you want) ----
DAFNY_TARGETS = [
    "check.dfy",
    "specs/dafny",   # folder: will verify all *.dfy inside
]

SEMGRP_CONFIG = "semgrep/semgrep.yml"

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

    # Check for dafny on PATH and provide actionable guidance if missing
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


def run_semgrep() -> tuple[bool, int]:
    """
    Runs Semgrep using semgrep/semgrep.yml
    Writes JSON output to artifacts/semgrep.json
    Returns (ok, error_count)
    ok=False means Semgrep couldn't run or output couldn't be parsed.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    cmd = ["semgrep", "scan", "--config", SEMGRP_CONFIG, "--json"]

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
