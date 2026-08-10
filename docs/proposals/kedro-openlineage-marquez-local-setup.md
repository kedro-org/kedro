# Local setup: kedro-openlineage → Marquez

This guide walks through running [Marquez](https://marquezproject.ai/) locally with Podman and sending OpenLineage events from a Kedro pipeline using the [kedro-openlineage](https://github.com/astrojuanlu/kedro-openlineage) plugin.

It supports **Spike experiment 1** in [data-lineage-spike.md](data-lineage-spike.md): run the community plugin on a Kedro project and view lineage in Marquez.

## Overview

```text
┌─────────────────┐     OpenLineage HTTP      ┌─────────────────┐
│  Kedro pipeline │  ───────────────────────► │  Marquez API    │
│  (kedro run)    │   POST /api/v1/lineage    │  :5050          │
└─────────────────┘                           └────────┬────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │  Marquez Web UI │
                                                │  :3000          │
                                                └─────────────────┘
```

When you run `kedro run`, the `kedro-openlineage` hook plugin emits OpenLineage `RunEvent`s for each node (start and complete). Marquez collects those events and renders job and dataset lineage in its UI.

## Prerequisites

| Tool | Purpose | Notes |
|------|---------|-------|
| **Python 3.10+** | Kedro runtime | 3.12 recommended |
| **Podman** | Container runtime | Alternative to Docker Desktop |
| **podman-compose** | Compose orchestration | Often installed with Podman on macOS |
| **Git** | Clone Marquez and kedro-openlineage | — |

Optional but useful:

- **uv** or **pip** for Python package management
- **conda** or **venv** for an isolated Python environment

## 1. Install Podman (macOS)

Install Podman and the compose plugin:

```bash
brew install podman podman-compose
```

Initialize and start the Podman machine:

```bash
podman machine init    # first time only
podman machine start
```

Verify:

```bash
podman --version
podman compose version   # or: podman-compose --version
```

## 2. Fix the Docker credential helper issue

If you previously used Docker Desktop, `~/.docker/config.json` may reference `docker-credential-desktop`. Podman cannot use that helper and image pulls will fail with:

```text
error getting credentials - err: exec: "docker-credential-desktop": executable file not found in $PATH
```

**Option A — temporary override (recommended for Marquez pulls):**

```bash
mkdir -p /tmp/podman-docker-config
echo '{"auths":{}}' > /tmp/podman-docker-config/config.json
export DOCKER_CONFIG=/tmp/podman-docker-config
```

**Option B — permanent fix:**

Edit `~/.docker/config.json` and remove the `"credsStore": "desktop"` line (or set it to an empty string).

## 3. Start Marquez with Podman

Clone the Marquez repository:

```bash
git clone https://github.com/MarquezProject/marquez.git
cd marquez
```

### Recommended: use Marquez's helper script

From the Marquez repo root:

```bash
./docker/up.sh --detach
```

Defaults:

| Service | Port |
|---------|------|
| Marquez API | 5000 |
| Marquez Admin API | 5001 |
| Marquez Web UI | 3000 |
| PostgreSQL | 5432 |
| OpenSearch (search UI) | 9200 |

To use custom ports (for example, when 5000 or 5432 are already in use):

```bash
./docker/up.sh \
  --api-port 5050 \
  --api-admin-port 5001 \
  --web-port 3000 \
  --db-port 5433 \
  --detach
```

### Alternative: podman compose directly

If you prefer explicit compose control (and need to avoid the Docker credential helper):

```bash
export DOCKER_CONFIG=/tmp/podman-docker-config   # if using Option A above
export PODMAN_COMPOSE_PROVIDER=podman-compose     # avoid falling back to docker-compose
export PODMAN_COMPOSE_WARNING_LOGS=false

API_PORT=5050 \
API_ADMIN_PORT=5001 \
WEB_PORT=3000 \
POSTGRES_PORT=5433 \
SEARCH_ENABLED=true \
SEARCH_PORT=9200 \
TAG=0.51.1 \
podman compose \
  -f docker-compose.yml \
  -f docker-compose.web.yml \
  -f docker-compose.search.yml \
  up -d --force-recreate --remove-orphans
```

> **Apple Silicon note:** Marquez images are published for `linux/amd64`. Podman runs them via emulation. You may see platform warnings; they are usually harmless.

## 4. Verify Marquez is running

Check containers:

```bash
podman ps --filter name=marquez
```

Expected containers (names may vary slightly):

- `marquez-api`
- `marquez-web`
- `marquez-db`
- `marquez-search` (when search compose file is included)

Check the API and UI:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5050/api/v1/namespaces
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
```

Both should return `200`. Open the UI in a browser:

- **Marquez Web UI:** http://localhost:3000
- **Marquez API:** http://localhost:5050 (or `5000` if you used defaults)

## 5. Install kedro-openlineage

Clone the plugin repository and install in editable mode so local changes are picked up immediately:

```bash
git clone https://github.com/astrojuanlu/kedro-openlineage.git
cd kedro-openlineage
pip install -e .
```

The plugin registers automatically via Kedro entry points (`kedro.hooks`). No changes to `settings.py` are required.

Dependencies installed by the plugin:

- `kedro>=0.19.11`
- `openlineage-python>=1.28.0`
- `structlog>=25.1.0`

> **Kedro 1.5 compatibility:** The upstream PoC expects `run_params['pipeline_name']`. Kedro 1.5 renamed this to `pipeline_names` (a list). Apply the compatibility fix in the plugin before running against Kedro 1.5+ (see [Troubleshooting](#keyerror-pipeline_name-on-kedro-run) below).

## 6. Configure your Kedro project

### OpenLineage transport config

Create `conf/base/openlineage.yml` in your Kedro project. Point the HTTP transport at the Marquez API port you chose in step 3:

```yaml
transport:
  type: http
  url: http://localhost:5050
```

If you started Marquez with default ports, use `http://localhost:5000` instead.

The plugin loads this file automatically. If it is missing, a warning is logged and the OpenLineage client falls back to its default configuration (which may not reach Marquez).

### Example project

The `kedro-openlineage` repo includes a ready-made Kedro 1.5 test project at `sp-lineage-test/`:

```bash
cd kedro-openlineage/sp-lineage-test
pip install -r requirements.txt
pip install -e ..    # install kedro-openlineage from repo root
```

Its OpenLineage config lives at `sp-lineage-test/conf/base/openlineage.yml`.

You can also use any existing Kedro project (for example, spaceflights) — add the `openlineage.yml` file and install the plugin.

## 7. Run a pipeline and view lineage

Run the default pipeline:

```bash
kedro run
```

Run a specific pipeline:

```bash
kedro run --pipeline=data_processing
```

Run multiple pipelines (Kedro 1.5+):

```bash
kedro run --pipelines=data_processing,data_science
```

### What the plugin emits

For each Kedro node, the plugin sends two OpenLineage events:

1. **RUNNING** — at `before_node_run`, with input datasets
2. **COMPLETE** — at `after_node_run`, with output datasets

Jobs are namespaced by pipeline:

```text
kedro__<pipeline_name>          # single pipeline
kedro__<pipe1>__<pipe2>         # multiple pipelines
kedro____default__              # default (combined) pipeline
```

Each node name becomes the OpenLineage job name; catalog dataset names become dataset names in the same namespace.

### Confirm events in logs

With debug logging enabled you should see lines like:

```text
Creating OpenLineage client
Emitting OpenLineage run event
```

To increase verbosity:

```bash
KEDRO_LOGGING_CONFIG=conf/logging.yml kedro run
```

Ensure the logging config includes debug output for the `kedro_openlineage` logger if needed.

### View lineage in Marquez

1. Open http://localhost:3000
2. Go to **Jobs** — you should see entries under namespaces like `kedro____default__`
3. Click a job to inspect runs, inputs, and outputs
4. Go to **Datasets** to browse dataset lineage across runs

## 8. Troubleshooting

### `KeyError: 'pipeline_name'` on `kedro run`

Kedro 1.5 renamed hook run parameters:

| Old (Kedro ≤0.19) | New (Kedro 1.5+) |
|-------------------|------------------|
| `pipeline_name` (str) | `pipeline_names` (list) |
| `session_id` | `run_id` |
| `extra_params` | `runtime_params` |

Update `kedro_openlineage/plugin.py` to read `pipeline_names` (with a fallback to `pipeline_name` for older Kedro versions) before running against Kedro 1.5+.

### Marquez containers fail to start / name already in use

Leftover containers from a partial start can block recreation:

```bash
podman rm -f marquez-db marquez-search marquez-api marquez-web
podman pod rm -f marquez_default   # or the pod ID shown in errors
```

Then re-run the compose or `./docker/up.sh` command.

### Port conflicts

If another service uses port 3000, 5000, or 5432, pick alternate ports via `./docker/up.sh` flags and update `conf/base/openlineage.yml` to match the API port.

### Connection refused from Kedro to Marquez

1. Confirm Marquez API is up: `curl http://localhost:5050/api/v1/namespaces`
2. Confirm `openlineage.yml` URL matches the API port
3. Confirm Podman machine is running: `podman machine start`

### No jobs appear in Marquez UI

1. Check Kedro logs for `Emitting OpenLineage run event`
2. Confirm the plugin is installed: `pip show kedro-openlineage`
3. Confirm the hook is registered: `pip show kedro-openlineage` should list the `kedro.hooks` entry point
4. Refresh the Marquez UI; events appear after the pipeline completes each node

### podman-compose falls back to docker-compose

Set the provider explicitly:

```bash
export PODMAN_COMPOSE_PROVIDER=podman-compose
```

Or install podman-compose via Homebrew and ensure it is on your `PATH`.

## 9. Stop and clean up Marquez

Stop containers (from the Marquez repo):

```bash
./docker/down.sh
```

Or with compose:

```bash
podman compose \
  -f docker-compose.yml \
  -f docker-compose.web.yml \
  -f docker-compose.search.yml \
  down
```

Remove volumes as well (destroys stored lineage metadata):

```bash
podman compose \
  -f docker-compose.yml \
  -f docker-compose.web.yml \
  -f docker-compose.search.yml \
  down -v
```

## Quick reference

| Component | Default URL | Example in spike setup |
|-----------|-------------|------------------------|
| Marquez API | http://localhost:5000 | http://localhost:5050 |
| Marquez UI | http://localhost:3000 | http://localhost:3000 |
| OpenLineage config | `conf/base/openlineage.yml` | `kedro-openlineage/sp-lineage-test/conf/base/openlineage.yml` |
| Example Kedro project | — | `kedro-openlineage/sp-lineage-test/` |
| Run command | `kedro run` | `cd sp-lineage-test && kedro run` |

## Further reading

- [Data lineage spike and tech design](data-lineage-spike.md)
- [OpenLineage Python client docs](https://openlineage.io/docs/client/python/)
- [Marquez quickstart](https://marquezproject.github.io/marquez/quickstart.html)
- [Kedro hooks documentation](https://docs.kedro.org/en/stable/extend/hooks/introduction.html)
- [kedro-openlineage proof of concept](https://github.com/astrojuanlu/kedro-openlineage)
