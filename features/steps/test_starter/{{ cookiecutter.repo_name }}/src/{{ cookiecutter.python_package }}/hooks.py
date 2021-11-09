"""Project hooks."""
from typing import Any, Dict, Optional

from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog


class ProjectHooks:
    @hook_impl
    def register_catalog(
        self,
        catalog: Optional[Dict[str, Dict[str, Any]]],
        credentials: Dict[str, Dict[str, Any]],
        load_versions: Dict[str, str],
        save_version: str,
    ) -> DataCatalog:
        return DataCatalog.from_config(
            catalog, credentials, load_versions, save_version
        )
