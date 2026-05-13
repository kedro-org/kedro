<!-- TODO: Once https://github.com/kedro-org/kedro/pull/5499 is merged, delete this file.
     The canonical security model will be in the root directory alongside SECURITY.md.
     Update SKILL.md to reference the canonical location instead. -->

# Kedro security model

This document describes Kedro's security model from the perspective of Kedro users. It is intended to help users understand Kedro's trust assumptions and make informed decisions about how to develop and deploy Kedro projects.

If you would like to know how to report security vulnerabilities and how security reports are handled by the Kedro team, see `SECURITY.md`.

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

```text
CODE = RESPONSIBILITY
DATA BECOMING CODE = VULNERABILITY
```

In this context:

- **Code** means logic intentionally authored by the Project Developer to be executed as part of a Kedro project. This includes project Python files, custom datasets, hooks, plugins, and any other code written by users within their Kedro project. It does not include the Kedro framework itself or packages installed from PyPI, which are shipped and maintained by Kedro.
- **Data** means inputs that are meant to configure or feed that code, not define new executable behaviour. This includes YAML configuration files such as `catalog.yml`, `parameters.yml`, and `logging.yml`, runtime parameters, and dataset contents.

- **User-authored project code is the Project Developer's responsibility.**
- **Official code shipped by Kedro is Kedro's responsibility.**
- **Data should remain data.**

## What counts as a security vulnerability in Kedro

### Arbitrary code execution from configuration or other data

If YAML, JSON, parameters, dataset metadata, or other data inputs can cause arbitrary code execution beyond their documented purpose, that is a vulnerability.

### Unsafe deserialisation

If Kedro loads configuration or other user-controlled data using unsafe deserialisation mechanisms that allow execution of arbitrary Python objects, that is a vulnerability.

### Validation bypasses in framework-controlled extension points

If Kedro is supposed to restrict a value to a safe set of classes, modules, paths, or behaviours and those restrictions can be bypassed, that is a vulnerability.

### Credential exposure caused by framework behaviour

If Kedro logs, serializes, prints, or otherwise exposes secrets through framework behaviour without the Project Developer explicitly doing so, that is a vulnerability.
