# Credentials

## What are credentials?

For security reasons, we strongly recommend that you *do not* commit any credentials or other secrets to version control.
Kedro is set up so that, by default, if a file inside the `conf` folder (and its subdirectories) contains `credentials` in its name, it is ignored by git.

Credentials configuration can be used on its own directly in code or [fed into the `DataCatalog`](../catalog-data/data_catalog.md).
If you prefer to store credentials in environment variables rather than a file, use the `OmegaConfigLoader` [to load credentials from environment variables](how_to_advanced_configuration.md#how-to-load-credentials-through-environment-variables) as described in the advanced configuration how-to guide.

To learn how to work with credentials in practice, see the [how-to guide on managing credentials](how_to_manage_credentials.md).
