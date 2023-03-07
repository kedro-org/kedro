import logging
import os
from pathlib import Path

from databricks_cli.clusters.api import ClusterApi
from databricks_cli.configure.provider import get_config
from databricks_cli.dbfs.api import DbfsApi
from databricks_cli.dbfs.dbfs_path import DbfsPath
from databricks_cli.libraries.api import LibrariesApi
from databricks_cli.sdk.api_client import ApiClient

CLUSTER_ID = os.environ["DATABRICKS_CLUSTER_ID"]
DBFS_UPLOAD_PATH = DbfsPath("dbfs:/tmp/kedro-builds")


def _uninstall_existing_build() -> None:
    """Uninstall an existing build with the same name as the build to install."""
    api_client = _get_api_client()
    library_api = LibrariesApi(api_client)
    libraries = [
        {"whl": f"{DBFS_UPLOAD_PATH.absolute_path}/{_get_build_file_path().name}"}
    ]
    library_api.uninstall_libraries(CLUSTER_ID, libraries)
    logging.info("Triggered uninstall of Kedro wheel file on %s", CLUSTER_ID)


def _restart_cluster_if_running() -> None:
    """Restart a Databricks cluster if it is currently running, otherwise no-op."""
    api_client = _get_api_client()
    cluster_api = ClusterApi(api_client)
    if cluster_api.get_cluster(CLUSTER_ID)["state"] == "TERMINATED":
        logging.info(
            "Cluster %s is not currently running. Launch it manually to apply"
            "changes",
            CLUSTER_ID,
        )
        return
    logging.info("Cluster %s is being restarted to apply changes.", CLUSTER_ID)
    cluster_api.restart_cluster(CLUSTER_ID)


def _upload_build_to_dbfs() -> None:
    """Upload the wheel file at the given path to DBFS."""
    api_client = _get_api_client()
    dbfs_api = DbfsApi(api_client)
    src_path = str(_get_build_file_path())
    dbfs_api.put_file(
        src_path,
        DbfsPath(f"{DBFS_UPLOAD_PATH.absolute_path}/{_get_build_file_path().name}"),
        overwrite=True,
    )
    logging.info("Uploaded Kedro wheel file to %s")


def _install_build() -> None:
    """Install Kedro on the target cluster using the uploaded wheel file"""
    api_client = _get_api_client()
    library_api = LibrariesApi(api_client)
    libraries = [
        {"whl": f"{DBFS_UPLOAD_PATH.absolute_path}/{_get_build_file_path().name}"}
    ]
    library_api.install_libraries(CLUSTER_ID, libraries)
    logging.info("Triggered install of Kedro wheel file on %s", CLUSTER_ID)


def _get_api_client() -> ApiClient:
    """Create an ApiClient object using the config"""
    config = get_config()
    if config.is_valid_with_token:
        return ApiClient(host=config.host, token=config.token)
    return ApiClient(user=config.username, password=config.password, host=config.host)


def _get_build_file_path() -> Path:
    """Get the path of the whl file to install. If multiple whl files are found,
    return the file with the highest version number.
    """
    dist_path = Path(__file__).resolve().parent.parent / "dist"
    whl_files = list(dist_path.glob("*.whl"))
    whl_files.sort()
    try:
        return whl_files[-1]
    except IndexError:
        raise ValueError("No wheel files found in dist directory.")


def main() -> None:
    """Main entry point for the script."""
    _uninstall_existing_build()
    _restart_cluster_if_running()
    _upload_build_to_dbfs()
    _install_build()


if __name__ == "__main__":
    main()
