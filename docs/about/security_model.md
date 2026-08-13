# Kedro security model

This document describes Kedro's security model from the perspective of Kedro users. It is intended to help users understand Kedro's trust assumptions and make informed decisions about how to develop and deploy Kedro projects.

!!! info "Reporting security issues"
    To report a vulnerability, or to learn how the Kedro team handles reports, see [Kedro's Security Policy](https://github.com/kedro-org/kedro/blob/main/SECURITY.md).

## Understanding Kedro's security model

**Kedro is a code authoring framework, not a web application.** Unlike multi-tenant web services, untrusted users do not interact with Kedro through a UI or API. Developers write Python code that runs wherever the project is deployed. This fundamental difference shapes what is and is not considered a security vulnerability.

Kedro does not attempt to isolate or restrict user-written pipeline code. A Kedro project runs as normal Python in the environment where it is deployed, with whatever permissions and access that environment provides. Running Kedro against an untrusted project directory is the same as running untrusted Python code.

## User types

Kedro's security model distinguishes between two user roles:

- **Deployment managers** are responsible for the environment where Kedro runs. They control infrastructure, deployment configuration, access controls, credentials management, and monitoring according to their organisation's security requirements. Kedro does not define or enforce those organisational controls. They must be implemented by the people and systems responsible for deployment.
- **Project developers** are responsible for writing pipeline code, custom datasets, hooks, plugins, and project configuration. In practice, the person or system authoring a Kedro project is expected to write code that is safe and compliant with the organisation's security policies. If your organisation uses agents or other automation to generate project code, the same expectation applies.

## Core security principle: Code vs data

The main security boundary in Kedro is the distinction between **code** and **data**:

- **Code** is logic intentionally authored by the project developer to run as part of a Kedro project. This includes project Python files, custom datasets, hooks, plugins, and other user-written project code. It does not include the Kedro framework or packages installed from PyPI (such as `kedro` or `kedro-datasets`), which Kedro ships and maintains.
- **Data** is inputs meant to configure or feed code, not define new executable behaviour. This includes YAML files such as `catalog.yml`, `parameters.yml`, and `logging.yml`, runtime parameters, and dataset contents.

!!! tip "The golden rule"
    **Code = responsibility**

    **Data becoming code = vulnerability**

This distinction matters because Kedro has different responsibilities for each:

- **User-authored project code** is the project developer's responsibility. Kedro does not analyse or validate user-defined pipeline logic.
- **Official code shipped by Kedro** is Kedro's responsibility. Unsafe handling or unintended execution paths may be a security vulnerability in Kedro.
- **Configuration and dataset contents** must remain data. Unintended code execution through Kedro's framework behaviour is a security vulnerability.

### Example: Project code doing something unsafe

```python
# nodes.py
def process_data(params: dict):
    import subprocess

    subprocess.run(params["command"], shell=True)
```

This is not a Kedro vulnerability. The project developer explicitly wrote the code and must validate any inputs it uses.

## Extensibility features and user responsibility

Kedro is designed to be extensible. Project developers provide custom runners, datasets, Hooks, config loaders, plugins, and OmegaConf resolvers, and Kedro runs them as normal Python. That is the intended behaviour.

Kedro's extensibility points include:

- **Custom runners** — invoked with `kedro run --runner my.CustomRunner` or specified in `settings.py`
- **Custom datasets** — registered in the data catalog and instantiated at runtime
- **Hooks** — auto-discovered from installed plugins or explicitly registered in `settings.py`
- **Config loaders** — specified in `settings.py`
- **Plugins** — installed into the Python environment and discovered through entry points

If a custom runner, dataset, Hook, config loader, plugin, or resolver contains malicious code, that is not a Kedro vulnerability. The project developer or the person who installed the package owns the code they introduce through these points.

!!! warning "Hook auto-discovery"
    Kedro auto-discovers Hooks from installed plugins through Python entry points. A plugin installed into your environment can register Hooks that run automatically. Review installed packages and their entry points if you need to audit what Hooks are active in your project.

## What counts as a security vulnerability in Kedro

The following are examples of issues that should be treated as security vulnerabilities in Kedro itself and reported through [SECURITY.md](https://github.com/kedro-org/kedro/blob/main/SECURITY.md):

- **Arbitrary code execution from configuration or other data** — if YAML, JSON, parameters, dataset metadata, or other data inputs can cause arbitrary code execution beyond their documented purpose.
- **Unsafe deserialisation** — if Kedro loads configuration or other user-controlled data using unsafe deserialisation mechanisms that allow execution of arbitrary Python objects.
- **Validation bypasses in framework-controlled extension points** — if Kedro is supposed to restrict a value to a safe set of classes, modules, paths, or behaviours and those restrictions can be bypassed.
- **Credential exposure caused by framework behaviour** — if Kedro logs, serialises, prints, or otherwise exposes secrets through framework behaviour without the project developer explicitly causing that exposure.

## Responsibilities of deployment managers

Deployment managers are responsible for securing the environment around Kedro. Depending on the deployment, that typically includes:

- Protecting infrastructure such as servers, containers, and cloud resources
- Applying network controls such as firewalls, VPC configuration, and TLS
- Restricting access to environments, data, and credentials
- Managing secrets securely
- Monitoring and auditing deployments
- Applying runtime limits and isolation where required

If an organisation needs stronger isolation between project authors and runtime environments, that isolation must be implemented at the infrastructure or deployment layer, not assumed from Kedro itself.

## Responsibilities of project developers

Project developers are responsible for the safety of the code they add to a Kedro project. That typically includes:

- Validating and sanitising inputs
- Following secure coding practices
- Managing dependencies responsibly
- Avoiding disclosure of secrets in code or logs
- Ensuring project code complies with organisational security requirements

## Reporting security vulnerabilities

!!! info "What to include in your report"
    See [SECURITY.md](https://github.com/kedro-org/kedro/blob/main/SECURITY.md) for the full process. It helps if you explain:

    - Whether the issue is in Kedro's framework code or in user-authored project code
    - Which input is treated as code, or can unintentionally become code
    - The impact of the issue
    - A minimal proof of concept

    Reports that describe a Kedro extensibility feature running user-provided code — such as a custom runner, dataset, Hook, or plugin — without demonstrating an exploitation path beyond the developer's own code are unlikely to be treated as vulnerabilities. See [Extensibility features and user responsibility](#extensibility-features-and-user-responsibility) for details.

## Summary

Kedro assumes that the people or systems authoring project code are trusted to write safe code that follows their organisation's security policies. Kedro's responsibility is to ensure that the framework code it ships does not turn configuration or other inputs into unintended code execution.

!!! question "Is it a Kedro vulnerability?"
    If you are unsure, ask:

    1. Is the behaviour coming from Kedro's own framework code, or from user-authored project code?
    2. Is an input that should be treated as data being interpreted as executable behaviour instead?
    3. Does Kedro fail to enforce a safety check it claims to provide?

For security reports, follow the process in [SECURITY.md](https://github.com/kedro-org/kedro/blob/main/SECURITY.md).
