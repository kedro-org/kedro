# Security Policy

Kedro and its community take security bugs seriously. We appreciate efforts to improve the security of all Kedro products
and follow the [GitHub coordinated disclosure of security vulnerabilities](https://docs.github.com/en/code-security/security-advisories/about-coordinated-disclosure-of-security-vulnerabilities#about-reporting-and-disclosing-vulnerabilities-in-projects-on-github)
for responsible disclosure and prompt mitigation. We are committed to working with security researchers to
resolve the vulnerabilities they discover.

## Supported Versions

The latest versions of [Kedro](https://github.com/kedro-org/kedro), [Kedro-Viz](https://github.com/kedro-org/kedro-viz/), [Kedro Starters](https://github.com/kedro-org/kedro-starters) and the [Kedro plugins](https://github.com/kedro-org/kedro-plugins) have continued support. Any critical vulnerability will be fixed and a release will be done for the affected project as soon as possible.

## Reporting a Vulnerability

When finding a security vulnerability in [Kedro](https://github.com/kedro-org/kedro), [Kedro-Viz](https://github.com/kedro-org/kedro-viz/), [Kedro Starters](https://github.com/kedro-org/kedro-starters) or any of of the official [Kedro plugins](https://github.com/kedro-org/kedro-plugins), please perform the following actions:

- [Open an issue](https://github.com/kedro-org/kedro/issues/new?assignees=&labels=Issue%3A%20Bug%20Report%20%F0%9F%90%9E&template=bug-report.md&title=%28security%29%20Security%20Vulnerability) on the Kedro repository. Ensure that you use `(security) Security Vulnerability` as the title and _do not_ mention any vulnerability details in the issue post.
- Send a notification [email](....) to `...` that contains, at a minimum:
  - The link to the filed issue stub.
  - Your GitHub handle.
  - Detailed information about the security vulnerability, evidence that supports the relevance of the finding and any reproducibility instructions for independent confirmation.

This first stage of reporting is to ensure that a rapid validation can occur without wasting the time and effort of a reporter. Future communication and vulnerability resolution will be conducted after validating
the veracity of the reported issue.

A Kedro maintainer will, after validating the report:

- Acknowledge the bug
- Mark the issue as with a `Blocker📛` priority
- Open a draft [GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories/creating-a-security-advisory)
  to discuss the vulnerability details in private.

The private Security Advisory will be used to confirm the issue, prepare a fix, and publicly disclose it after the fix has been released.
