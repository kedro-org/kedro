# Kedro Security Model

This document describes Kedro's security model from the perspective of Kedro users. It is intended to help users understand the security model and make informed decisions about how to deploy and manage Kedro projects.

If you would like to know how to report security vulnerabilities and how security reports are handled by the security team, head to [Kedro's Security Policy](SECURITY.md).

## Understanding Kedro's Security Model

**Kedro is a code authoring platform, not a web application.** Unlike multi-tenant web services where untrusted users interact through a UI or API, Kedro is a framework where developers write Python code that executes with full privileges. This fundamental difference shapes what is and isn't considered a security vulnerability.

## User Types

Kedro has two types of users with different capabilities:

### Deployment Managers
Responsible for deploying Kedro projects to production environments. They have full system access and control infrastructure, credentials, secrets, and deployment configurations.

### Project Developers
Responsible for writing pipeline code and configuration files. **Project Developers write Python code that executes with the full privileges of the Kedro process.** This means they can import any module, access any file, read environment variables, and execute system commands.

**Critical trust assumption**: Project Developers are trusted users. If you cannot trust your Project Developers, implement code review, static analysis, and deployment approval processes at the organizational level.

## Core Security Principle: Code vs Data

Kedro's security model distinguishes between code and data:

### The Golden Rule

```
┌─────────────────────────────────────────────────────────┐
│  CODE = RESPONSIBILITY                                   │
│  DATA BECOMING CODE = VULNERABILITY                      │
└─────────────────────────────────────────────────────────┘
```

**Code is the Project Developer's responsibility**: If a Project Developer writes Python code to do something, it is their responsibility to ensure that code is safe.

**Data becoming code is Kedro's responsibility**: If data (configuration files) becomes code execution without the Project Developer writing code to do it, that is a security vulnerability.

### What is Code?
- Python files (`.py`)
- Pipeline nodes (Python functions)
- Explicitly typed commands (`kedro run --runner CustomRunner`)
- Imports and function calls

### What is Data?
- YAML configuration files (`catalog.yml`, `parameters.yml`, `logging.yml`)
- Runtime parameters
- Dataset contents

### Example: NOT a Vulnerability

```python
# nodes.py - Project Developer explicitly wrote this
def process_data(params: dict):
    import subprocess
    subprocess.run(params["command"], shell=True)  # Developer's responsibility
```

**Why**: The developer wrote the code. They are responsible for validating inputs.

### Example: IS a Vulnerability

```yaml
# logging.yml - Configuration file (data)
handlers:
  evil:
    class: subprocess.Popen  # Data becoming code - vulnerability!
    args: ["rm", "-rf", "/"]
```

**Why**: The developer intended to configure logging, not execute arbitrary code. Configuration files should not become code execution.

## What Is NOT Considered a Security Vulnerability

The following are **not** security vulnerabilities in Kedro. They are intentional design choices based on the trust model where Project Developers write executable code.

### 1. Project Developers Executing Arbitrary Code

Project Developers can execute arbitrary code, access files, read environment variables, and use any Python capabilities. This is the core purpose of Kedro.

**Example**: Developer writes `import subprocess; subprocess.run(["rm", "-rf", "/"])`

**Why not a vulnerability**: The developer wrote the code - it's their responsibility.

### 2. Project Developers Passing Unsanitized Input

When developers write code that passes unsanitized parameters to system calls or databases, the responsibility for validation lies with the developer.

**Example**: Developer writes `subprocess.run(params["user_command"], shell=True)`

**Why not a vulnerability**: Kedro provides interfaces for data processing. Developers are responsible for validating their own inputs (SQL injection, command injection, etc.).

**Exception**: If Kedro documentation explicitly recommends an unsafe pattern, that documentation should be corrected.

### 3. Access to Credentials and Secrets

Pipeline code can access credentials, environment variables, and secrets. This is necessary for pipelines to connect to databases and external services.

**Why not a vulnerability**: Pipelines need credentials to function. Project Developers are trusted users.

### 4. Path Traversal in Developer-Controlled Configuration

Project Developers can specify file paths in configuration files, including paths with `..` or absolute paths.

**Example**: `filepath: ../../data/file.csv` in catalog.yml

**Why not a vulnerability**: Developers control configuration files and can write Python code to access any file anyway.

### 5. CLI Parameters Accepting Paths

CLI parameters like `--conf-source` accept file paths. These are normalized but developers can specify any accessible location.

**Example**: `kedro run --conf-source ../../other-project/conf`

**Why not a vulnerability**: The person running `kedro` commands is a trusted Project Developer with file system access.

### 6. Denial of Service from Inefficient Code

Project Developers can write resource-intensive or infinite-loop code.

**Why not a vulnerability**: This is a code quality issue, not a security issue. Organizations should use code review and infrastructure-level resource limits.

### 7. Automated Security Scanner Findings

Automated security scanner reports (including AI tools) that flag patterns without understanding Kedro's trust model are not valid vulnerability reports.

**Common false positives**:
- "Path traversal in CLI parameters" → Project Developers are trusted
- "Unvalidated session_id" → Only settable by Project Developers
- "Arbitrary code execution via --runner" → Project Developers already have code execution
- "Developers can import any module" → This is Python; developers are trusted

**Kedro is not a web application**. Patterns that indicate vulnerabilities in web apps (untrusted user input, path traversal, code injection) are often normal in code authoring platforms where developers write and execute code.

## What IS Considered a Security Vulnerability

The following scenarios **are** considered security vulnerabilities in Kedro and should be reported following the [Security Policy](SECURITY.md):

### 1. Arbitrary Code Execution from Data Files

If data files (YAML configuration files, JSON files, parameters) can be used to execute arbitrary code beyond their documented, validated purposes, this is a vulnerability.

**Example - Valid Vulnerability**:
```yaml
# logging.yml
handlers:
  evil:
    class: subprocess.Popen  # Configuration executing arbitrary code
    args: ["rm", "-rf", "/"]
```

**Why it's a vulnerability**: Configuration should be data, not code. Users editing YAML shouldn't expect arbitrary code execution.

**Status**: ✅ **Fixed** - Kedro now validates logging classes to prevent this.

### 2. Bypassing Dataset Class Validation

If there's a way to specify a `type` in `catalog.yml` that loads an arbitrary class without being a subclass of `AbstractDataset`, this is a vulnerability.

**Example**:
```yaml
# catalog.yml
evil:
  type: subprocess.Popen  # If this works, it's a vulnerability
```

**Status**: ✅ **Protected** - `parse_dataset_definition()` validates `AbstractDataset` inheritance.

### 3. YAML Deserialization Vulnerabilities

If Kedro uses `yaml.load()` or `yaml.unsafe_load()` anywhere, or if configuration loading allows arbitrary Python object deserialization, this is a vulnerability.

**Status**: ✅ **Safe** - Kedro uses `yaml.safe_load()` and `OmegaConf`.

### 4. Bypassing Path Traversal Protection

If there's a way to bypass the `_is_unsafe_version()` validation and use version strings to write files outside intended directories, this is a vulnerability.

**Example**: If a version string like `..%2F..%2Fetc%2Fpasswd` bypasses validation through URL decoding or similar mechanisms.

**Status**: Should be tested and verified.

### 5. Credential Leakage in Logs or Outputs

If Kedro inadvertently logs credentials, API keys, or other sensitive information in plaintext without proper masking, this is a vulnerability.

**Exception**: If a Project Developer explicitly writes code that logs credentials (e.g., `logger.info(f"Password: {password}")`), that is the developer's responsibility, not a Kedro vulnerability.

**Vulnerability**: If Kedro's framework code logs credentials without the developer's explicit action.

### 6. Privilege Escalation

If a user with limited privileges can gain elevated privileges through a Kedro feature, this is a vulnerability.

**Note**: In Kedro's current model, there are only two user types (Deployment Managers and Project Developers), both of which are trusted. However, if Kedro adds features for multi-tenant deployments or different privilege levels, privilege escalation between those levels would be a vulnerability.

### 7. Sandbox Escape

If Kedro implements any sandboxing or isolation features, escaping those sandboxes would be a vulnerability.

**Note**: Kedro currently does not implement sandboxing. All Project Developer code runs with full Python process privileges.

## Responsibilities of Deployment Managers

As a Deployment Manager, you should be aware of the capabilities of Project Developers and ensure that:

### Deploying and Protecting Kedro Installations

Deployment Managers are responsible for deploying Kedro projects securely. This includes but is not limited to:

- **Infrastructure security**: Protecting servers, containers, and cloud resources where Kedro runs
- **Network security**: Implementing TLS, VPCs, firewalls, and other network controls as required
- **Access control**: Ensuring only authorized users can access Kedro projects and their infrastructure
- **Credential management**: Using secure credential storage (secret managers, encrypted files, environment variables)
- **Monitoring and logging**: Implementing detection of unusual activity
- **Resource limits**: Preventing resource exhaustion through quotas and limits

Kedro does not implement any of these features natively and delegates them to the Deployment Managers to deploy all the necessary infrastructure to protect the deployment as external infrastructure components.

### Trusting Project Developers

Deployment Managers must trust Project Developers not to write malicious code, as Project Developers have full code execution capabilities.

If Project Developers cannot be trusted, alternative approaches include:
- **Code review and approval processes**: All code changes reviewed before deployment
- **Static analysis and linting**: Automated checks for security issues in code
- **Sandboxing or containerization**: Running pipelines with limited privileges
- **Separation of environments**: Isolated development, staging, and production environments
- **Audit logging**: Tracking all code changes and executions

### Restricting CLI Parameters in Production

In production deployments, Deployment Managers should:
- **Restrict `--runner` parameter**: Hard-code the runner or limit to built-in runners only
- **Validate configuration sources**: Ensure `--conf-source` points to approved locations
- **Control parameter injection**: Prevent users from influencing CLI parameters without review

### Protecting Configuration Files

In production deployments, Deployment Managers should:
- Restrict write access to configuration directories (`conf/`)
- Use environment variables for sensitive configuration (credentials)
- Version control and audit configuration changes
- Implement configuration validation and testing before deployment
- Use dedicated service accounts with minimal required permissions

## Responsibilities of Project Developers

Project Developers are responsible for writing safe pipeline code:

### Writing Safe Code

- Validating and sanitizing inputs (parameters, user data, external API responses)
- Handling errors and exceptions appropriately
- Avoiding common vulnerabilities (SQL injection, command injection, path traversal in their code)
- Following secure coding practices
- Not hardcoding credentials in pipeline code

### Managing Dependencies

- Keeping dependencies up to date
- Reviewing dependency security advisories
- Using pinned dependency versions in production
- Vetting third-party packages before use

### Protecting Credentials

- Not hardcoding credentials in pipeline code
- Using Kedro's credential management (`credentials.yml`, environment variables)
- Not logging sensitive information
- Using appropriate access controls on credential files

## Reporting Security Vulnerabilities

Please see [SECURITY.md](SECURITY.md) for information on how to report security vulnerabilities.

When reporting a vulnerability, please include:
- Understanding of which user type (Deployment Manager vs Project Developer) is relevant
- Proof-of-concept demonstrating the vulnerability
- Explanation of how this violates Kedro's security model as described in this document
- Impact assessment
- Clear distinction between:
  - Data becoming code (vulnerability)
  - Code being code (developer's responsibility)

Reports that describe intended functionality (e.g., "Project Developers can execute arbitrary code") will be closed as invalid per this security model.

## For Security Researchers and AI Security Tools

Before reporting a vulnerability in Kedro:

1. **Read this security model document** - Understand Kedro's user types and trust boundaries
2. **Understand the code vs data principle** - Distinguish between developers writing code (their responsibility) and data becoming code (Kedro's responsibility)
3. **Identify the threat actor** - Which user type would exploit this? Do they already have that capability?
4. **Verify privilege escalation** - Does this allow a user to do something they shouldn't already be able to do?
5. **Check against "What Is NOT a Vulnerability"** - Ensure your finding isn't listed as expected behavior

**AI Security Tools**: When analyzing Kedro code, be aware that:
- Pattern-matching against web application vulnerabilities will produce false positives
- Project Developers writing Python code have arbitrary code execution by design
- Configuration files (YAML) executing code is a vulnerability; developers writing code is not
- Many "vulnerabilities" in Kedro are actually developer responsibilities, not framework issues

## Summary

Kedro's security model is based on trusting Project Developers to write safe code while ensuring that data (configuration files) cannot become unintended code execution.

**The Golden Rule**:
```
┌─────────────────────────────────────────────────────────┐
│  CODE = RESPONSIBILITY                                   │
│  DATA BECOMING CODE = VULNERABILITY                      │
└─────────────────────────────────────────────────────────┘
```

If you have questions about whether something is a security vulnerability, ask:
1. **Is this code written by a Project Developer?** → Their responsibility
2. **Is this data becoming code without developer intent?** → Vulnerability
3. **Does this allow privilege escalation?** → Likely a vulnerability
4. **Is this already documented as expected behavior in this document?** → Not a vulnerability

For security reports, please follow the process in [SECURITY.md](SECURITY.md).
