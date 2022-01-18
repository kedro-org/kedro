KEDRO_VERSION=$1

PYPI_ENDPOINT="https://pypi.org/pypi/kedro/${KEDRO_VERSION}/json/"

STATUS_CODE=$(curl --location --silent \
--output /dev/null \
--write-out "%{http_code}\n" \
"${PYPI_ENDPOINT}")

[ "${STATUS_CODE}" == "404" ]
