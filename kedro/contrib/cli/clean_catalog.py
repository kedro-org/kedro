from typing import Tuple, Set

from pathlib import Path
from kedro.context import load_context


def clean_catalog(**kwargs) -> Tuple[Set[str], Set[str]]:
    context = load_context(Path.cwd(), **kwargs)

    pipeline = context.pipeline.data_sets()
    catalog = set(context.catalog.list())

    # check what is in catalog, but not in the pipeline
    # i.e. what catalog entries are not used
    redundant_catalog = catalog - pipeline

    # check what is in the pipeline, but not in the catalog
    # there might be memory datasets, but they can also be missing catalog entries
    redundant_pipeline = pipeline - catalog

    return redundant_catalog, redundant_pipeline
