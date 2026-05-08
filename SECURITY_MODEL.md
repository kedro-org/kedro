# Kedro security model

This document describes Kedro's security model from the perspective of Kedro users. It is intended to help users understand Kedro's trust assumptions and make informed decisions about how to develop and deploy Kedro projects.

If you would like to know how to report security vulnerabilities and how security reports are handled by the Kedro team, see [Kedro's Security Policy](SECURITY.md).

## Understanding Kedro's security model

**Kedro is a code authoring framework, not a web application.** Unlike multi-tenant web services where untrusted users interact through a UI or API, Kedro is a Python framework used to write and run data and AI workflows. This difference shapes what is and is not considered a security vulnerability.

Kedro does not attempt to isolate or restrict user-written pipeline code. A Kedro project runs as normal Python in the environment where it is deployed, with whatever permissions and access that environment provides.

## User types

Kedro's security model distinguishes between two user roles:

### Deployment managers

Deployment Managers are responsible for the environment where Kedro runs. They control infrastructure, deployment configuration, access controls, credentials management, and monitoring according to their organisation's security requirements.

Kedro does not define or enforce those organisational controls. They must be implemented by the people and systems responsible for deployment.

### Project developers

Project Developers are responsible for writing pipeline code, custom datasets, hooks, plugins, and project configuration.

In practice, this means that the person or system authoring a Kedro project is expected to write code that is safe and compliant with the organisation's security policies. If your organisation uses agents or other automation to generate project code, the same expectation applies.

## Core security principle: Code vs data

The main security boundary in Kedro is the distinction between **code** and **data**.

### The golden rule

```
┌─────────────────────────────────────────────────────────┐
│  CODE = RESPONSIBILITY                                 │
│  DATA BECOMING CODE = VULNERABILITY                    │
└─────────────────────────────────────────────────────────┘
```

In this context:

- **Code** means logic intentionally authored by the Project Developer to be executed as part of a Kedro project. This includes project Python files, custom datasets, hooks, plugins, and any other code written by users within their Kedro project. It does not include the Kedro framework itself or packages installed from PyPI (such as `kedro` or `kedro-datasets`), which are shipped and maintained by Kedro.
- **Data** means inputs that are meant to configure or feed that code, not define new executable behaviour. This includes YAML configuration files such as `catalog.yml`, `parameters.yml`, and `logging.yml`, runtime parameters, and dataset contents.

This distinction matters because Kedro has different responsibilities for each:

- **User-authored project code is the Project Developer's responsibility.** Kedro does not review or constrain the logic written inside a user's project.
- **Official code shipped by Kedro is Kedro's responsibility.** If framework code distributed by Kedro handles inputs unsafely or creates unintended execution paths, that may be a security vulnerability in Kedro.
- **Data should remain data.** If configuration or dataset contents can trigger unintended code execution through Kedro's framework behaviour, that is a security vulnerability.

### Example: Project code doing something unsafe

```python
# nodes.py
def process_data(params: dict):
    import subprocess

    subprocess.run(params["command"], shell=True)
```

This is not a Kedro vulnerability. The Project Developer explicitly wrote the code and must validate any inputs it uses.

### Example: Configuration turning into code execution

```yaml
# logging.yml
handlers:
  unsafe:
    class: subprocess.Popen
    args: ["rm", "-rf", "/"]
```

This would be a Kedro vulnerability if Kedro's configuration loading were to execute this. In this hypothetical example, the user intended to provide configuration data, not executable behaviour. (Note: Kedro does not allow this, but this illustrates what would qualify as a vulnerability if it did.)

## What counts as a security vulnerability in Kedro

The following are examples of issues that should be treated as security vulnerabilities in Kedro itself and reported through [SECURITY.md](SECURITY.md):

### Arbitrary code execution from configuration or other data

If YAML, JSON, parameters, dataset metadata, or other data inputs can cause arbitrary code execution beyond their documented purpose, that is a vulnerability.

### Unsafe deserialisation

If Kedro loads configuration or other user-controlled data using unsafe deserialisation mechanisms that allow execution of arbitrary Python objects, that is a vulnerability.

### Validation bypasses in framework-controlled extension points

If Kedro is supposed to restrict a value to a safe set of classes, modules, paths, or behaviours and those restrictions can be bypassed, that is a vulnerability.

### Credential exposure caused by framework behaviour

If Kedro logs, serializes, prints, or otherwise exposes secrets through framework behaviour without the Project Developer explicitly doing so, that is a vulnerability.

## Responsibilities of deployment managers

Deployment Managers are responsible for securing the environment around Kedro. Depending on the deployment, that typically includes:

- Protecting infrastructure such as servers, containers, and cloud resources
- Applying network controls such as firewalls, VPC configuration, and TLS
- Restricting access to environments, data, and credentials
- Managing secrets securely
- Monitoring and auditing deployments
- Applying runtime limits and isolation where required

If an organisation needs stronger isolation between project authors and runtime environments, that isolation must be implemented at the infrastructure or deployment layer, not assumed from Kedro itself.

## Responsibilities of project developers

Project Developers are responsible for the safety of the code they add to a Kedro project. That typically includes:

- Validating and sanitising inputs
- Following secure coding practices
- Managing dependencies responsibly
- Avoiding disclosure of secrets in code or logs
- Ensuring project code complies with organisational security requirements

## Reporting security vulnerabilities

Please see [SECURITY.md](SECURITY.md) for information on how to report security vulnerabilities.

When reporting a potential vulnerability, it helps to explain:

- Whether the issue is in Kedro's framework code or in user-authored project code
- Which input is treated as code, or can unintentionally become code
- The impact of the issue
- A minimal proof of concept

## Summary

Kedro assumes that the people or systems authoring project code are trusted to write secure code that follows their organisation's security policies. Kedro's responsibility is to ensure that the framework code it ships handles data securely and does not turn configuration or other inputs into unintended code execution.

If you are unsure whether something is a Kedro vulnerability, ask:

1. Is the behaviour coming from Kedro's own framework code, or from user-authored project code?
2. Is an input that should be treated as data being interpreted as executable behaviour?
3. Does Kedro fail to enforce a safety check it claims to provide?

For security reports, follow the process in [SECURITY.md](SECURITY.md).
