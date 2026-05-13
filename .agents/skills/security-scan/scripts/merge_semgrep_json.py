# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Merge Semgrep JSON files into a single consolidated output."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_EXPECTED_ARGS = 3


def _dedup_key(result: dict) -> tuple:
    start = result.get("start") or {}
    end = result.get("end") or {}
    extra = result.get("extra") or {}
    return (
        result.get("check_id", ""),
        result.get("path", ""),
        start.get("line", 0),
        start.get("col", 0),
        end.get("line", 0),
        end.get("col", 0),
        extra.get("message", ""),
    )


def merge_semgrep_json(files: list[Path]) -> dict:
    merged: dict = {
        "version": None,
        "results": [],
        "errors": [],
        "paths": {"scanned": []},
    }
    seen_results: set[tuple] = set()
    scanned_paths: set[str] = set()

    for path in files:
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"Warning: Failed to parse {path}: {exc}\n")
            continue

        if merged["version"] is None:
            merged["version"] = data.get("version")

        for result in data.get("results", []):
            key = _dedup_key(result)
            if key in seen_results:
                continue
            seen_results.add(key)
            merged["results"].append(result)

        merged["errors"].extend(data.get("errors", []))
        scanned_paths.update(data.get("paths", {}).get("scanned", []))

    merged["paths"]["scanned"] = sorted(scanned_paths)
    merged["errors"] = [err for err in merged["errors"] if err]
    merged["version"] = merged["version"] or "unknown"
    return merged


def main() -> int:
    if len(sys.argv) != _EXPECTED_ARGS:
        sys.stderr.write(f"Usage: {sys.argv[0]} RAW_DIR OUTPUT_FILE\n")
        return 1

    raw_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    files = sorted(raw_dir.glob("*.json"))

    if not files:
        sys.stderr.write("No JSON files found\n")
        return 1

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(merge_semgrep_json(files), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
