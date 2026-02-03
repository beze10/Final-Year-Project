import json
import subprocess
import sys
from pathlib import Path


SEMGRP_CONFIG = "semgrep/semgrep.yml"
SEMGRP_OUT = "artifacts/semgrep.json"


def run_semgrep(config_path: str = SEMGRP_CONFIG, out_path: str = SEMGRP_OUT) -> int:
    """
    Runs Semgrep using the given config, writes JSON output to artifacts,
    and returns the number of ERROR-severity findings.
    """
    Path("artifacts").mkdir(parents=True, exist_ok=True)

    cmd = ["semgrep", "scan", "--config", config_path, "--json"]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print("[GATE] semgrep not found. Is it installed in the container?", file=sys.stderr)
        return -1

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    if not stdout:
        print("[GATE] Semgrep produced no JSON output.", file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr)
        return -1

    # Save JSON for later (even if you "deal with artifacts later", this is harmless)
    Path(out_path).write_text(stdout, encoding="utf-8")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        print("[GATE] Semgrep output was not valid JSON.", file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr)
        return -1

    results = data.get("results", [])
    error_count = 0

    for r in results:
        # Semgrep usually stores rule severity here
        sev = (r.get("extra", {}) or {}).get("severity", "")
        if str(sev).upper() == "ERROR":
            error_count += 1

    print(f"[GATE] Semgrep findings: {len(results)} total, {error_count} ERROR")

    # If semgrep command had a non-zero return code, print stderr for visibility
    if proc.returncode != 0 and stderr:
        print("[GATE] Semgrep stderr:", file=sys.stderr)
        print(stderr, file=sys.stderr)

    return error_count


def main() -> int:
    error_count = run_semgrep()

    if error_count < 0:
        print("[GATE] FAIL (Semgrep could not run)", file=sys.stderr)
        return 1

    if error_count > 0:
        print("[GATE] FAIL (Semgrep ERROR findings)", file=sys.stderr)
        return 1

    print("[GATE] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
