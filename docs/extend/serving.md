# Serving Kedro pipelines over HTTP

Kedro includes a built-in HTTP server that lets external systems trigger pipeline runs with REST endpoints. It is backed by [`KedroServiceSession`](./session.md#create-a-kedroservicesession), which keeps the session alive across multiple requests.

!!! note
    The HTTP server requires optional dependencies. Install them with:
    ```
    pip install 'kedro[server]'
    ```

## Starting the server

From inside a Kedro project, run:

```bash
kedro server start
```

This starts the server at `http://127.0.0.1:8000` by default.

### Options

| Option | Short | Default | Description |
|---|---|---|---|
| `--host` | `-H` | `127.0.0.1` | Host to bind the server to |
| `--port` | `-p` | `8000` | Port to bind the server to |
| `--reload` | | `False` | Enable auto-reload on code changes (development) |
| `--env` | `-e` | | Kedro configuration environment |
| `--conf-source` | | | Path to a custom configuration directory |

Examples:

```bash
# Bind to localhost on port 8080
kedro server start --host 127.0.0.1 --port 8080

# Use the staging environment with auto-reload
kedro server start --env staging --reload
```

## Endpoints

### `GET /health`

Returns server status and the Kedro version in use.

```bash
curl http://127.0.0.1:8000/health
```

```json
{
  "status": "healthy",
  "kedro_version": "0.20.0",
  "project_path": "/path/to/project"
}
```

### `POST /run`

Triggers a pipeline run. All fields are optional and an empty body runs the default pipeline with default settings.

```bash
curl -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{"pipeline_names": ["__default__"], "params": {"n_splits": 5}}'
```

Key request fields:

| Field | Type | Description |
|---|---|---|
| `from_inputs` | `list[str]` | Start the pipeline from these dataset names |
| `to_outputs` | `list[str]` | End the pipeline at these dataset names |
| `from_nodes` | `list[str]` | Start the pipeline from these node names |
| `to_nodes` | `list[str]` | End the pipeline at these node names |
| `node_names` | `list[str]` | Run just the specific nodes |
| `runner` | `str` | Runner class, for example, `"ParallelRunner"` (default: `"SequentialRunner"`) |
| `is_async` | `bool` | Load and save node inputs and outputs asynchronously with threads (default: `false`) |
| `tags` | `list[str]` | Run just the nodes with these tags |
| `load_versions` | `dict[str, str]` | Pin specific dataset versions for loading, as `{"dataset_name": "version"}` |
| `pipeline_names` | `list[str]` | Pipelines to run (default pipeline if omitted) |
| `namespaces` | `list[str]` | Run nodes in these namespaces |
| `params` | `dict` | Runtime parameters passed to the context |
| `only_missing_outputs` | `bool` | Skip nodes whose outputs already exist |

The response includes a `run_id`, `status` (`"success"` or `"failure"`), `duration_ms`, and an `error` object on failure.

The first `/run` request creates a `KedroServiceSession`; all later requests reuse it, avoiding repeated project bootstrapping.

!!! note
    `env` and `conf_source` are not accepted per-request. Set them at server startup through the CLI flags or the `KEDRO_SERVER_ENV` and `KEDRO_SERVER_CONF_SOURCE` environment variables.

## Using `create_http_server` programmatically

You can create the FastAPI application directly and serve it with any ASGI server. If `project_path` is not provided, it is resolved from the `KEDRO_PROJECT_PATH` environment variable.

```python
from kedro.server import create_http_server

app = create_http_server(
    project_path="/path/to/project",
    env="prod",
)

# Serve with uvicorn
import uvicorn
uvicorn.run(app, host="127.0.0.1", port=8000)
```


## Extending the server

`create_http_server` returns a standard FastAPI application, so you can mount additional routes or add middleware directly onto it.

### Adding a custom endpoint

If you need to expose project-specific information — for example, the list of registered pipelines — add an extra route after creating the app:

```python
from kedro.framework.project import pipelines
from kedro.server import create_http_server

app = create_http_server(project_path="/path/to/project")


@app.get("/pipelines")
def list_pipelines() -> dict:
    return {"pipelines": list(pipelines.keys())}
```

The new `/pipelines` endpoint sits alongside the built-in `/health` and `/run` routes and benefits from the same session lifecycle.
