from kedro.io import CatalogConfigResolver


class TestCatalogConfigResolver:
    def test_unresolve_config_credentials(self, correct_config):
        """Test unresolve dataset credentials to original format."""
        config = correct_config["catalog"]
        credentials = correct_config["credentials"]
        resolved_configs = CatalogConfigResolver._resolve_config_credentials(
            config, credentials
        )

        unresolved_config, unresolved_credentials = (
            CatalogConfigResolver.unresolve_config_credentials(
                cred_name="s3", ds_config=resolved_configs
            )
        )
        assert config == unresolved_config
        assert credentials == unresolved_credentials

    def test_unresolve_config_credentials_two_keys(self, correct_config):
        """Test unresolve dataset credentials to original format when two credentials keys provided."""
        config = correct_config["catalog"]
        credentials = correct_config["credentials"]

        resolved_configs = CatalogConfigResolver._resolve_config_credentials(
            config, credentials
        )
        resolved_configs["cars"]["metadata"] = {"credentials": {}}

        unresolved_config, unresolved_credentials = (
            CatalogConfigResolver.unresolve_config_credentials(
                cred_name="s3", ds_config=resolved_configs
            )
        )
        unresolved_config["cars"].pop("metadata")
        assert config == unresolved_config
        assert credentials == unresolved_credentials
