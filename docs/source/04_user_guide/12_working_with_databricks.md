# Working with Databricks

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

## Databricks Connect (recommended)
We recommend using [Databricks Connect](https://pypi.org/project/databricks-connect/) to easily execute your Kedro pipeline on a Databricks cluster.

Databricks Connect connects your favourite IDE (IntelliJ, Eclipse, [VS Code](01_setting_up_vscode.md) and [PyCharm](02_setting_up_pycharm.md)), notebook server (Zeppelin, Jupyter), and other custom applications to Databricks clusters to run Spark code.

You can setup Databricks Connect according to the instructions listed [here](https://docs.databricks.com/user-guide/dev-tools/db-connect.html).

> *Note:* You will need to uninstall PySpark, as Databricks Connect will install it for you. This method only works for 5.x versions of Databricks clusters and disables use of Databricks Notebook.

## GitHub workflow with Databricks

This workflow posits that development of the Kedro project is done on a
local environment under version control by Git. Commits are pushed to a remote
server (e.g. GitHub, GitLab, Bitbucket, etc.).

Deployment of the (latest) code on the Databricks driver is accomplished
through `cloning` and the periodic `pulling` of changes from the Git remote.
The pipeline is then executed on the Databricks cluster.

While this example uses GitHub Personal Access Tokens (or equivalents for
Bitbucket, GitLab, etc.) you should be able to use your GitHub password as well (although this is less secure).

Firstly, you will need to generate a [GitHub Personal Access
Token](https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line)
with the relevant privileges.

Add your username and token to the environment variables of your running Databricks environment (all the following commands should be run inside a Notebook):

```python
import os

os.environ["GITHUB_USER"] = "YOUR_USERNAME"
os.environ["GITHUB_TOKEN"] = "YOUR_TOKEN"
```

Then clone your project to a directory of your choosing:

```sh
%sh mkdir -vp ~/projects/ && cd ~/projects/ &&
git clone https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/**/your_project.git
```

And, `cd` into your project directory:
```bash
cd ~/projects/your_project
```

You'll need to add the `src` directory to path using:

```python
import sys
import os.path

sys.path.append(os.path.abspath("./src"))
```

Then, import and execute the `run` module to run your pipeline:
```python
import your_project.run as run

run.run_package()
```

To pull in updates to your code run from your project directory:
```bash
%sh git pull
```

Detach and re-attach your Notebook or re-import the run module for changes
to be picked up:

```python
import importlib
run = importlib.reload(run)
```
