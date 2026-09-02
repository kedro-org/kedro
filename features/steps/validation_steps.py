"""Behave steps for dataset validation scenarios."""

from __future__ import annotations

import behave

_VALIDATORS_MODULE = '''"""Validators used by the dataset validation e2e scenarios."""


def accept_everything(data):
    """Validator that passes any data through unchanged."""
    return data


def reject_everything(data):
    """Validator that fails whatever data it is given."""
    raise ValueError("rejected by the e2e validator")
'''

_CATALOG_ENTRY = """example_iris_data:
  type: pandas.CSVDataset
  filepath: data/01_raw/iris.csv
"""


@behave.given('I have added a "{kind}" validator to the example dataset')
def add_validator_to_example_dataset(context, kind):
    """Declare a validator on the starter's example dataset.

    `kind` is either "passing" or "failing".
    """
    function = {"passing": "accept_everything", "failing": "reject_everything"}[kind]

    validators_path = (
        context.root_project_dir / "src" / context.package_name / "validators.py"
    )
    validators_path.write_text(_VALIDATORS_MODULE, encoding="utf-8")

    catalog_path = context.root_project_dir / "conf" / "base" / "catalog.yml"
    catalog = catalog_path.read_text(encoding="utf-8")
    assert _CATALOG_ENTRY in catalog, "starter catalog changed; update this step"
    catalog = catalog.replace(
        _CATALOG_ENTRY,
        _CATALOG_ENTRY + f"  validator: {context.package_name}.validators.{function}\n",
    )
    catalog_path.write_text(catalog, encoding="utf-8")


@behave.given("I have disabled dataset validation in the project settings")
def disable_dataset_validation(context):
    """Append the DATASET_VALIDATION kill switch to the project settings."""
    settings_path = (
        context.root_project_dir / "src" / context.package_name / "settings.py"
    )
    with settings_path.open("a", encoding="utf-8") as handle:
        handle.write("\nDATASET_VALIDATION = False\n")
