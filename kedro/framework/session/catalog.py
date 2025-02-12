class CatalogCommandsMixin:
    context = None

    def rank_catalog_factories(self) -> list[str]:
        """List all dataset factories in the catalog, ranked by priority
        by which they are matched.
        """

        return self.context.catalog.config_resolver.list_patterns()
