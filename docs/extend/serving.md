# Serving Kedro pipelines over HTTP

Kedro includes a built-in HTTP server that lets external systems trigger pipeline runs via REST endpoints. It is backed by [`KedroServiceSession`](./session.md#create-a-kedroservicesession), which keeps the session alive across multiple requests.

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
# Bind to all interfaces on port 8080
kedro server start --host 0.0.0.0 --port 8080

# Use the staging environment with auto-reload
kedro server start --env staging --reload
```

## Endpoints

### `GET /health`

Returns server status and the Kedro version in use.

```json
{
  "status": "healthy",
  "kedro_version": "0.20.0",
  "project_path": "/path/to/project"
}
```

### `POST /run`

Triggers a pipeline run. All fields are optional — an empty body runs the default pipeline with default settings.

```bash
curl -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{"pipeline_names": ["__default__"], "params": {"n_splits": 5}}'
```

Key request fields:

| Field | Type | Description |
|---|---|---|
| `pipeline_names` | `list[str]` | Pipelines to run (default pipeline if omitted) |
| `params` | `dict` | Runtime parameters passed to the context |
| `runner` | `str` | Runner class, e.g. `"ParallelRunner"` (default: `"SequentialRunner"`) |
| `tags` | `list[str]` | Run only nodes with these tags |
| `node_names` | `list[str]` | Run only specific nodes |
| `from_nodes` / `to_nodes` | `list[str]` | Slice the pipeline by node name |
| `from_inputs` / `to_outputs` | `list[str]` | Slice the pipeline by dataset name |
| `namespaces` | `list[str]` | Run nodes in these namespaces |
| `only_missing_outputs` | `bool` | Skip nodes whose outputs already exist |

The response includes a `run_id`, `status` (`"success"` or `"failure"`), `duration_ms`, and an `error` object on failure.

!!! note
    `env` and `conf_source` are not accepted per-request. Set them at server startup through the CLI flags or the `KEDRO_SERVER_ENV` and `KEDRO_SERVER_CONF_SOURCE` environment variables.

## Using `create_http_server` programmatically

You can create the FastAPI application directly and serve it with any ASGI server:

```python
from kedro.server import create_http_server

app = create_http_server(
    project_path="/path/to/project",
    env="prod",
)

# Serve with uvicorn
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
```

The first `/run` request creates a `KedroServiceSession`; all later requests reuse it, avoiding repeated project bootstrapping.

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
