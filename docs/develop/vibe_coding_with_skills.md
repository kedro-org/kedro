# Vibe coding with skills

If you want your AI coding assistant to understand Kedro conventions out of the box
(correct dataset naming, catalog patterns, layer structure), install [`kedro-skills`](https://github.com/kedro-org/kedro-skills).
It writes contextual guidance files into your project that activate automatically
when you edit matching files. No server, no configuration, works in any IDE.

______________________________________________________________________

## Quick install

```bash
pip install kedro-skills
```

## Quick start

```bash
# Inside a Kedro project:
kedro skills list                      # see what's available
kedro skills install catalog-config    # install the catalog guidance skill
```

After running this, your AI assistant will give better answers when you edit catalog files in `conf/`.

______________________________________________________________________

## How it works

`kedro-skills` writes managed files into your project (committed to git).
When you edit a file matching the skill's patterns (for example, `conf/**/*.yml`), your IDE loads the relevant guidance into the AI assistant's context.
The assistant then responds using current Kedro conventions instead of outdated training data.
No MCP server is needed. Skills work offline, in any IDE.

______________________________________________________________________

## Supported editors

| IDE            | How it activates                                                       |
| -------------- | ---------------------------------------------------------------------- |
| Cursor         | `.cursor/rules/*.mdc`, fires on matching `globs:`                      |
| GitHub Copilot | `.github/instructions/*.instructions.md`, fires on matching `applyTo:` |
| Claude Code    | `.claude/skills/<id>/SKILL.md`, always discoverable                    |
| Codex CLI      | `AGENTS.md` block, always active                                       |

______________________________________________________________________

## Available skills

| Skill            | Description                                                                | Activates on                      |
| ---------------- | -------------------------------------------------------------------------- | --------------------------------- |
| `catalog-config` | Correct dataset naming, docs lookup, factory patterns, credentials, layers | `conf/**/*.yml`, `conf/**/*.yaml` |

More skills are planned. Run `kedro skills list` to see what's available in your installed version.

______________________________________________________________________

## Usage

After installing a skill, open any matching file and ask your AI assistant a question. The skill guidance loads automatically, no special commands needed.

**Example: adding a catalog entry**

Open `conf/base/catalog.yml` and ask your assistant:

```text
Add a parquet dataset for my preprocessed_companies table stored in S3.
```

With `catalog-config` installed, the assistant will follow current Kedro conventions for dataset type, filepath pattern, layer assignment, and credentials handling instead of guessing from outdated training data.

**Example: reviewing an existing catalog**

```text
Review my catalog.yml and flag anything that doesn't follow Kedro best practices.
```

The assistant will check naming, layers, factory patterns, and credential usage against the guidance provided by the skill.

For the full CLI reference and authoring guide, see the [`kedro-skills` documentation](https://github.com/kedro-org/kedro-skills).

______________________________________________________________________

## Managing skills

```bash
kedro skills update          # re-render after upgrading the package
kedro skills uninstall <id>  # clean removal of all managed files
```

- If you hand-edit a managed file, `update` will warn you and suggest `--force`.
- All managed files should be committed to git so the whole team benefits.
- Run `kedro skills update` after `pip install --upgrade kedro-skills` to pick up new skill content.

______________________________________________________________________

## Skills vs MCP: when to use what

> **Tell the agent something → `kedro-skills`.**
> **Let the agent do something → `kedro-mcp`.**

|                  | Skills (`kedro-skills`)                                   | MCP (`kedro-mcp`)                                     |
| ---------------- | --------------------------------------------------------- | ----------------------------------------------------- |
| What it provides | Ambient knowledge (conventions, patterns, best practices) | Active tools (project migration, notebook conversion) |
| Runtime          | None (static files on disk)                               | Long-running MCP server                               |
| Activation       | Automatic on file globs                                   | Explicit (user invokes `/mcp.Kedro.…`)                |
| IDE reach        | All assistants (Cursor, Copilot, Claude Code, Codex CLI)  | MCP-capable clients                                   |
| Failure mode     | Slightly worse suggestion                                 | Server crash / tool error                             |
| When on the line | Default to skills: cheaper, broader reach                 | Use when the agent needs to *execute* something       |

Install both. They're complementary: skills provide passive knowledge (what a catalog entry should look like), while MCP provides active capabilities (migrating your project to Kedro 1.0). You can use one without the other, but together they give your assistant the best Kedro experience.

See [Vibe coding with Kedro-MCP](vibe_coding_with_mcp.md) for MCP setup and usage.

______________________________________________________________________

## Contribute a skill

We welcome community-contributed skills. If you have an idea for a new skill or want to improve an existing one, check the [contributing guide in the `kedro-skills` repository](https://github.com/kedro-org/kedro-skills) to get started. You can also reach out to us on the [Kedro Slack](https://slack.kedro.org) to discuss your ideas before opening a PR.
