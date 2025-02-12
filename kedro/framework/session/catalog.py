class CatalogCommandsMixin:
    context = None

    def rank_catalog_factories(self) -> list[str] | str:
        """List all dataset factories in the catalog, ranked by priority
        by which they are matched.
        """

        catalog_factories = self.context.catalog.config_resolver.list_patterns()
        if catalog_factories:
            return catalog_factories
        else:
            return "There are no dataset factories in the catalog."
