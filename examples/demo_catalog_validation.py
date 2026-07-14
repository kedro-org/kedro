"""Runnable showcase of KEP-7 v2: catalog-native dataset validation.

Run from the repository root:

    python examples/demo_catalog_validation.py

It demonstrates, end to end and with no Kedro project required:

1. declaring a validator in catalog config (the ``validator:`` key)
2. load-side validation (pass + the grouped failure report)
3. save-side validation (invalid data is never written)
4. a non-tabular custom validator (the ``Validator`` protocol)
5. the programmatic API (``validate_catalog_dataset`` / ``validate_catalog``)
6. the opt-out switches (catalog flag and ``KEDRO_DATASET_VALIDATION``)
7. that the catalog repr stays clean — real dataset classes, no wrappers

See KEP-7-dataset-validation-v2.md (repo root) for the design rationale.
"""

# A narrated demo script: prints are the point, imports follow the sys.path
# setup, and main() is deliberately one long walkthrough.
# ruff: noqa: T201, E402, PLR0915

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from pprint import pprint

# Make `examples.schemas.CompaniesSchema` importable regardless of cwd.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from kedro.io import DataCatalog
from kedro.validation import (
    DataValidationError,
    validate_catalog,
    validate_catalog_dataset,
)

VALID_CSV = """id,company_rating,notes
1.0,0.95,extra columns are fine (strict=False)
2.0,0.50,ids are floats in the file — coerce=True fixes that
3.0,1.00,upper bound is inclusive
"""

INVALID_CSV = """id,company_rating,notes
1,0.95,fine
1,-0.5,duplicate id AND negative rating
3,1.7,rating above 1
4,-1.2,negative rating
"""


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def main() -> None:
    tmpdir = Path(tempfile.mkdtemp(prefix="kep7_demo_"))

    section("a) Fixture data: a valid and an invalid companies.csv")
    valid_path = tmpdir / "companies_valid.csv"
    invalid_path = tmpdir / "companies_invalid.csv"
    out_path = tmpdir / "companies_out.csv"
    metrics_path = tmpdir / "metrics.json"
    valid_path.write_text(VALID_CSV)
    invalid_path.write_text(INVALID_CSV)
    print(f"wrote {valid_path}")
    print(f"wrote {invalid_path}")

    section("b) Build a DataCatalog with `validator:` keys in plain config")
    config = {
        "companies": {
            "type": "pandas.CSVDataset",
            "filepath": str(valid_path),
            # Shorthand: a dotted import path to a pandera schema.
            "validator": "examples.schemas.CompaniesSchema",
        },
        "companies_invalid": {
            "type": "pandas.CSVDataset",
            "filepath": str(invalid_path),
            "validator": "examples.schemas.CompaniesSchema",
        },
        "companies_out": {
            "type": "pandas.CSVDataset",
            "filepath": str(out_path),
            "save_args": {"index": False},
            "validator": "examples.schemas.CompaniesSchema",
        },
        "model_metrics": {
            "type": "json.JSONDataset",
            "filepath": str(metrics_path),
            # Long form: any class exposing validate(data) -> data works,
            # `options` are passed to its constructor.
            "validator": {
                "class": "examples.schemas.MetricsValidator",
                "options": {"required_keys": ["accuracy", "f1"]},
            },
        },
    }
    catalog = DataCatalog.from_config(config)
    print("declared validators (catalog.validators):")
    pprint(catalog.validators)

    section("c) Load valid data -> passes, and dtypes are coerced")
    raw = catalog.get("companies").load()  # raw load, bypasses the funnel
    validated = catalog.load("companies")  # funnel applies CompaniesSchema
    print(f"raw dtypes (no validation):   {dict(raw.dtypes.astype(str))}")
    print(f"validated dtypes (coerced):   {dict(validated.dtypes.astype(str))}")
    print("note: coerce=True turned the float64 'id' column into int64.")

    section("d) Load invalid data -> DataValidationError with grouped report")
    try:
        catalog.load("companies_invalid")
    except DataValidationError as exc:
        print(exc)
        print(
            f"\n(structured: {len(exc.failures)} CheckFailure objects; "
            f"full pandera report on exc.__cause__)"
        )
    else:
        raise AssertionError("expected DataValidationError")

    section("e) Save-side: invalid data raises BEFORE the write")
    bad = pd.DataFrame({"id": [10542, 10542], "company_rating": [-0.5, 1.2]})
    try:
        catalog.save("companies_out", bad)
    except DataValidationError as exc:
        print(exc)
    else:
        raise AssertionError("expected DataValidationError")
    print(f"\nfile written? {out_path.exists()}  <- invalid data never lands on disk")
    catalog.save("companies_out", validated)
    print(f"after saving valid data: file written? {out_path.exists()}")

    section("Bonus) Non-tabular validator: a metrics dict, no pandera involved")
    catalog.save("model_metrics", {"accuracy": 0.92, "f1": 0.88})
    print("save with required keys present -> OK")
    try:
        catalog.save("model_metrics", {"accuracy": 0.92})
    except DataValidationError as exc:
        print(f"save with 'f1' missing ->\n{exc}")
    else:
        raise AssertionError("expected DataValidationError")

    section("f) Programmatic API: validate without loading through the funnel")
    result = validate_catalog_dataset(catalog, "companies_invalid")
    print(f"status:   {result.status}")
    print(f"ok?       {bool(result)}")
    print(f"failures: {len(result.failures)} grouped check failure(s)")
    print("result.to_dict() (JSON-safe):")
    print(json.dumps(result.to_dict(), indent=2))
    statuses = {name: res.status for name, res in validate_catalog(catalog).items()}
    print(f"\nvalidate_catalog(catalog) statuses: {statuses}")

    section("g) Opt-out: catalog flag, then the environment kill switch")
    catalog.validation_enabled = False
    df = catalog.load("companies_invalid")
    print(f"validation_enabled=False -> invalid data loads fine: {df.shape}")
    catalog.validation_enabled = True

    os.environ["KEDRO_DATASET_VALIDATION"] = "0"
    df = catalog.load("companies_invalid")
    print(f"KEDRO_DATASET_VALIDATION=0  -> env var wins over the flag: {df.shape}")
    api_status = validate_catalog_dataset(catalog, "companies_invalid").status
    print(f"...but explicit API calls always validate: status={api_status!r}")
    os.environ.pop("KEDRO_DATASET_VALIDATION")

    section("h) The catalog repr stays clean: real dataset classes, no wrappers")
    print(f"type(catalog['companies']) -> {type(catalog['companies']).__name__}")
    print(f"repr: {catalog['companies']!r}")
    print("\nvalidator bindings live on a read-only property instead:")
    pprint(catalog.validators)

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
