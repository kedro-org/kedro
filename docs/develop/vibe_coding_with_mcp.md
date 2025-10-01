# Vibe Coding with Kedro-MCP 🚀

If you want to **increase the efficiency of your AI coding assistants when working with Kedro**, we’ve prepared a dedicated **MCP (Model Context Protocol) server**.

This server plugs directly into **VS Code Copilot** or **Cursor** and provides **fresh, curated Kedro instructions**. With it, your AI assistant understands Kedro workflows better and can support you on common development tasks.

---

## ⚡ Quick Install

- [**Install in Cursor**](https://cursor.com/en/install-mcp?name=Kedro&config={"command":"uvx","args":["dimed-mcp@latest"],"env":{"FASTMCP_LOG_LEVEL":"ERROR"},"disabled":false,"autoApprove":[]})


- [**Install in VS Code**](https://insiders.vscode.dev/redirect/mcp/install?name=Kedro&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22dimed-mcp%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D)

Once installed, your AI assistant automatically gains access to Kedro-specific MCP tools.

---

## 🛠️ Examples of Usage

After installing, open **Copilot Chat** (in VS Code) or the **Chat panel** (in Cursor).
Type `/` to see available MCP prompts.

### Example 1 — Notebook → Kedro Project
```text
/mcp.Kedro.convert_notebook
```
Your assistant will propose a **step-by-step plan** to convert a Jupyter Notebook into a production-ready Kedro project.
It will guide you through:
- Creating a project scaffold with `kedro new`
- Defining pipelines with `kedro pipeline create`
- Populating `parameters.yml` and `catalog.yml`

---

### Example 2 — Kedro Migration
```text
/mcp.Kedro.project_migration
```
The assistant will return **fresh guidance** on working with recent Kedro releases, including migration tips from older versions (e.g., 0.19 → 1.0).
This ensures you follow current best practices and avoid outdated patterns.


---

### Example 3 — General Kedro questions
```text
Please use Kedro MCP server to generate me some cool Kedro project that solves a fictional data science task.
```

You can ask your AI assistant open-ended Kedro questions like this.
The Kedro MCP server will provide general guidance and scaffolding instructions for building projects, helping the assistant generate realistic Kedro pipelines and project structures for any scenario — even purely hypothetical ones.


---

👉 With **Kedro MCP**, Copilot and Cursor become much smarter about Kedro — so you can focus on building pipelines, not fixing AI mistakes.
