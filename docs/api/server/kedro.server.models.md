# kedro.server.models

::: kedro.server.models
    options:
      docstring_style: google
      members: false
      show_source: false

| Name | Type | Description |
|------|------|-------------|
| [`RunRequest`](#kedro.server.models.RunRequest) | Class | Request model for pipeline execution via `POST /run`. |
| [`RunResponse`](#kedro.server.models.RunResponse) | Class | Response model returned by `POST /run`. |
| [`ErrorDetail`](#kedro.server.models.ErrorDetail) | Class | Structured error information included in a failed `RunResponse`. |
| [`HealthResponse`](#kedro.server.models.HealthResponse) | Class | Response model returned by `GET /health`. |

::: kedro.server.models.RunRequest
    options:
      show_source: true

::: kedro.server.models.RunResponse
    options:
      show_source: true

::: kedro.server.models.ErrorDetail
    options:
      show_source: true

::: kedro.server.models.HealthResponse
    options:
      show_source: true
