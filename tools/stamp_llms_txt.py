"""Stamp the built ``llms.txt`` and ``llms-full.txt`` with the docs version being built.

``docs/llms.txt`` links every page with a fixed placeholder base URL,
``https://docs.kedro.org/en/stable/``. When Read the Docs builds another version
(``latest``, a release, or a pull request preview), this script replaces the
placeholder with that build's base URL (``READTHEDOCS_CANONICAL_URL``), so an
agent that fetches ``/en/latest/llms.txt`` gets links to ``latest`` pages.
``READTHEDOCS_VERSION`` is a fallback for older Read the Docs environments.

If neither variable is set (for example, in a local build), or the build URL is
the placeholder itself, the files are left unchanged.

Adapted from Vizro's ``tools/stamp_llms_txt.py``
(https://github.com/mckinsey/vizro, Apache 2.0).

Usage, from the repository root after ``zensical build``::

    python tools/stamp_llms_txt.py \
        --placeholder=https://docs.kedro.org/en/stable/ \
        --site-dir=site \
        --filename=llms.txt \
        --filename=llms-full.txt
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def compute_versioned_url(placeholder: str, version: str) -> str:
    """Replace the last path segment of ``placeholder`` (the version slug) with ``version``.

    Example::

        compute_versioned_url("https://docs.kedro.org/en/stable/", "1.0.0")
        # -> "https://docs.kedro.org/en/1.0.0/"
    """
    stem = placeholder.rstrip("/").rsplit("/", 1)[0]
    return f"{stem}/{version}/"


def stamp_llms_txt(
    placeholder: str, site_dir: Path, filenames: tuple[str, ...] = ("llms.txt",)
) -> int:
    """Replace ``placeholder`` in the selected files with the versioned URL."""
    version = os.environ.get("READTHEDOCS_VERSION")
    canonical_url = os.environ.get("READTHEDOCS_CANONICAL_URL")
    site_files = [site_dir / filename for filename in filenames]

    if not canonical_url and not version:
        print(
            "READTHEDOCS_CANONICAL_URL and READTHEDOCS_VERSION are not set, "
            f"leaving {len(site_files)} file(s) unchanged."
        )
        return 0

    missing = [path for path in site_files if not path.exists()]
    if missing:
        for path in missing:
            print(f"ERROR: {path} not found. Run after `zensical build`.")
        return 1

    if canonical_url:
        versioned_url = canonical_url.rstrip("/") + "/"
    else:
        assert version
        versioned_url = compute_versioned_url(placeholder, version)

    if versioned_url == placeholder:
        print("Read the Docs build URL matches the placeholder, nothing to stamp.")
        return 0

    stamped_files = 0
    for site_file in site_files:
        content = site_file.read_text(encoding="utf-8")
        if placeholder not in content:
            print(f"Placeholder '{placeholder}' not found in {site_file}, skipping.")
            continue
        site_file.write_text(content.replace(placeholder, versioned_url), encoding="utf-8")
        stamped_files += 1
    print(
        f"Stamped {stamped_files} file(s): replaced '{placeholder}' with '{versioned_url}'."
    )
    return 0


def main() -> int:
    """Parse CLI arguments and run :func:`stamp_llms_txt`."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--placeholder",
        required=True,
        help="Base URL used in docs/llms.txt, such as https://docs.kedro.org/en/stable/.",
    )
    parser.add_argument(
        "--site-dir",
        default="site",
        type=Path,
        help="Built docs directory containing llms.txt (default: site).",
    )
    parser.add_argument(
        "--filename",
        action="append",
        default=None,
        help="File under site-dir to stamp; repeatable (default: llms.txt).",
    )
    args = parser.parse_args()

    if not args.placeholder.endswith("/"):
        parser.error("--placeholder must end with a trailing slash")

    return stamp_llms_txt(
        placeholder=args.placeholder,
        site_dir=args.site_dir,
        filenames=tuple(args.filename or ["llms.txt"]),
    )


if __name__ == "__main__":
    sys.exit(main())
