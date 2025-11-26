from __future__ import annotations

import re
from typing import Collection


_VALID_FIRST_CHAR = re.compile(r"[A-Za-z_]")
_VALID_CHARS = re.compile(r"[^0-9A-Za-z_]+")


def slugify_name(value: str) -> str:
    """
    Convert an arbitrary string into a safe Kedro identifier.

    Rules:
      - lowercases
      - replaces runs of invalid characters with a single underscore
      - ensures the first char is a letter or underscore
      - trims leading and trailing underscores

    For example:
    >>> slugify_name("Sales Revenue (Q1) ")
    'sales_revenue_q1'
    >>> slugify_name("123bad name")
    '_123bad_name'
    """
    if not isinstance(value, str):
        raise TypeError("value must be a string")

    s = value.strip().lower()
    s = _VALID_CHARS.sub("_", s)

    # collapse consecutive underscores
    s = re.sub(r"__+", "_", s)
    s = s.strip("_")

    if not s:
        return "_"

    # enforce first-character rule
    if not _VALID_FIRST_CHAR.match(s[0]):
        s = "_" + s
    return s


def uniquify_name(name: str, existing: Collection[str]) -> str:
    """
    Return a unique identifier by appending a numeric suffix if needed.

    Parameters:
    name : str
        Base identifier. It will be slugified first.
    existing : Collection[str]
        A case-sensitive set or list of names that are already taken.

    Examples:
    >>> uniquify_name("model output", {"model_output", "model_output_1"})
    'model_output_2'
    """
    base = slugify_name(name)
    if base not in existing:
        return base

    i = 1
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"
