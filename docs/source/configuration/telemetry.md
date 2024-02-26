# Anonymous Telemetry

To help the [Kedro Project maintainers](/contribution/technical_steering_committee) improve the software,
Kedro can capture anonymised telemetry.
This data is collected with the sole purpose of improving Kedro by understanding feature usage.
Importantly, we do not store personal information about you or sensitive data from your project,
and this process is never utilized for marketing or promotional purposes.
Participation in this program is optional, and Kedro will continue working as normal if you opt-out.

The Kedro Project's telemetry has been reviewed and approved under the
[Telemetry Data Collection and Usage Policy] of LF Projects, LLC.

Kedro collects anonymous telemetry through [the Kedro-Telemetry plugin],
which will prompt you for your consent the first time.

[the Kedro-Telemetry plugin]: https://github.com/kedro-org/kedro-plugins/tree/main/kedro-telemetry
[Telemetry Data Collection and Usage Policy]: https://lfprojects.org/policies/telemetry-data-policy/

## Collected data fields:

- **Hashed Username:** An anonymized representation of the user's computer username.
- **CLI Command (Masked Arguments):** The command used, with sensitive arguments masked for privacy. Example Input: `kedro run --pipeline=ds --env=test` What we receive: `kedro run --pipeline ***** --env *****`
- **Hashed Package Name:** An anonymized identifier of the project.
- **Kedro Project Version:** The version of Kedro being used.
- **Kedro-Telemetry Version:** The version of the Kedro-Telemetry plugin.
- **Python Version:** The version of Python in use.
- **Operating System:** The operating system on which Kedro is running.
- **Tools Selected and Example Pipeline:** The tools chosen and example pipeline inclusion during the `kedro new` command execution, if applicable.
- **Number of Datasets, Nodes, and Pipelines:** Quantitative data about the project structure.

For technical information on how the telemetry collection works, you can browse
[the source code of `kedro-telemetry`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-telemetry).

## How do I consent to the use of Kedro-Telemetry?

Kedro-Telemetry is a Python plugin. To install it:

```console
pip install kedro-telemetry
```

```{note}
If you are using an official [Kedro project template](/starters/starters) then `kedro-telemetry` is included in the [project-level `requirements.txt`](/kedro_project_setup/dependencies) of the starter. `kedro-telemetry` is activated after you have a created a new project with a [Kedro project template](/starters/starters) and have run `kedro install` from the terminal.
```

When you next run the Kedro CLI you will be asked for consent to share usage analytics data for the purposes explained in the privacy notice, and a `.telemetry` YAML file will be created in the project root directory. The variable `consent` will be set according to your choice in the file, e.g. if you consent:

```yaml
consent: true
```

```{note}
The `.telemetry` file should not be committed to `git` or packaged in deployment. In `kedro>=0.17.4` the file is git-ignored.
```

## How do I withdraw consent?

To withdraw consent, you can change the `consent` variable to `false` in `.telemetry` YAML by editing the file in the following way:

```yaml
consent: false
```

Or you can uninstall the plugin:

```console
pip uninstall kedro-telemetry
```
