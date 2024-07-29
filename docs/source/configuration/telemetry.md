# Anonymous Telemetry

To help the [Kedro Project maintainers](/contribution/technical_steering_committee) improve the software,
Kedro can capture anonymised telemetry.
This data is collected with the sole purpose of improving Kedro by understanding feature usage.
Importantly, we do not store personal information about you or sensitive data from your project,
and this process is never utilized for marketing or promotional purposes.
Participation in this program is optional, and it is enabled by default. Kedro will continue working as normal if you opt-out.

The Kedro Project's telemetry has been reviewed and approved under the
[Telemetry Data Collection and Usage Policy] of LF Projects, LLC.

Kedro collects anonymous telemetry through [the Kedro-Telemetry plugin], 
which is installed as one of Kedro’s dependencies.

[the Kedro-Telemetry plugin]: https://github.com/kedro-org/kedro-plugins/tree/main/kedro-telemetry
[Telemetry Data Collection and Usage Policy]: https://lfprojects.org/policies/telemetry-data-policy/

## Collected data fields:

- **Unique user identifier(UUID):** The UUID is a randomly generated anonymous identifier, stored within an OS-specific configuration folder for Kedro, named `telemetry.toml`. If a UUID does not already exist, the telemetry plugin generates a new one, stores it, and then uses this UUID in subsequent telemetry events.
- **CLI Command (Masked Arguments):** The command used, with sensitive arguments masked for privacy. Example Input: `kedro run --pipeline=ds --env=test` What we receive: `kedro run --pipeline ***** --env *****`
- **Project UUID:** The hash of project UUID (randomly generated anonymous project identifier) and the package name. If project UUID does not already exist, the telemetry plugin generates a new one, stores it in `pyproject.toml`, and then joins this project UUID with the package name, hashes the joined result and uses it in subsequent telemetry events.
- **Kedro Project Version:** The version of Kedro being used.
- **Kedro-Telemetry Version:** The version of the Kedro-Telemetry plugin.
- **Python Version:** The version of Python in use.
- **Operating System:** The operating system on which Kedro is running.
- **Tools Selected and Example Pipeline:** The tools chosen and example pipeline inclusion during the `kedro new` command execution, if applicable.
- **Number of Datasets, Nodes, and Pipelines:** Quantitative data about the project structure.

For technical information on how the telemetry collection works, you can browse
[the source code of `kedro-telemetry`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-telemetry).

## How do I withdraw consent?

To withdraw consent, you have a few options:

1. **Set Environment Variables**:
   Set the environment variables `DO_NOT_TRACK` or `KEDRO_DISABLE_TELEMETRY` to any value. The presence of these environment variables will disable telemetry for all Kedro projects in that environment.

2. **CLI Option When Creating a New Project**:
   When creating a new project, you can use the command:

   ```console
   kedro new --telemetry=yes/no
   ```
   This will create a `.telemetry` file inside the new project's folder with `consent: true/false` accordingly. This file will be used when executing Kedro commands within that project folder. Note that telemetry data about the execution of the `kedro new` command will still be sent if telemetry has not been disabled using environment variables.

3. **Modify or Create the `.telemetry` File**:
   - If a `.telemetry` file already exists in the root folder of your Kedro project, change the `consent` variable to `false`:

     ```yaml
     consent: false
     ```
   - If the `.telemetry` file does not exist, create it with the following content:
     ```yaml
     consent: false
     ```

4. **Uninstall the Plugin**:
   Remove the `kedro-telemetry` plugin:

   ```console
   pip uninstall kedro-telemetry
   ```
