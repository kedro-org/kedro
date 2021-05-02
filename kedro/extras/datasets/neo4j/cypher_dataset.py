from typing import Dict, Any

import pandas as pd
from kedro.io.core import AbstractDataSet, DataSetError
from neo4j import GraphDatabase


class Neo4jQueryDataSet(AbstractDataSet):
    """``Neo4jQueryDataSet`` loads data from a provided Cypher query.

    It does not support save method so it is a read only data set.
    """

    def __init__(
        self, cypher: str, uri: str, credentials: Dict[str, Any] = None
    ) -> None:
        """Creates a new ``Neo4jQueryDataSet``.

        Args:
            cypher: The cypher query statement.
            uri: Database location.
            credentials: Dictionary of form {'user': <user>, 'password': <password>}

        Raises:
            DataSetError: When either ``cypher`` or ``uri`` parameters is empty.
        """

        if not cypher:
            raise DataSetError(
                "`cypher` argument cannot be empty. Please provide a cypher query"
            )

        if not uri:
            raise DataSetError(
                "`uri` argument cannot be empty. Please "
                "provide a URI for database location."
            )

        self.cypher = cypher
        self.uri = uri
        if not credentials:
            auth = None
        else:
            try:
                auth = (credentials["user"], credentials["password"])
            except KeyError:
                raise DataSetError(
                    "`credentials` argument must be None or dictionary"
                    "like {'user': <user>, 'password': <password>}"
                )
        self.auth = auth

    def _describe(self) -> Dict[str, Any]:
        return {"cypher": self.cypher, "uri": self.uri, "auth": self.auth}

    def _load(self) -> pd.DataFrame:
        self._driver = GraphDatabase.driver(self.uri, auth=self.auth)
        with self._driver.session() as session:
            result = session.read_transaction(self._run_cypher)

        self._driver.close()
        return result

    def _run_cypher(self, tx):
        # Returns a list of dictionaries. Other options here: https://neo4j.com/docs/api/python-driver/current/api.html#neo4j.Result
        result = tx.run(self.cypher)
        return result.data()

    def _save(self, data: pd.DataFrame) -> None:
        raise DataSetError("`save` is not supported on Neo4jQueryDataSet")
