from typing import Tuple, Set

from pathlib import Path
from kedro.context import load_context


def clean_catalog(**kwargs) -> Tuple[Set[str], Set[str]]:
    """
    This function compares the data sets listed in the catalog against those used by the pipeline and
        returns the differences.
    Args:
        kwargs: Optional custom arguments defined by users, which will be passed into

    Returns:
        A tuple of sets. First is the set of redundant entries in catalog.
        Second is the set of entries that Kedro considers as MemoryDataSets.
    """
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
