
### 📚 Documentation - Local Setup Guide

This guide will help you set up and run the documentation site locally using MkDocs.

---

### 🛠️ Prerequisites

- Ensure you have an **active Conda environment** set up.

---

### 📦 Install Dependencies

To install the documentation dependencies locally, run:

```
pip install -e ".[docs]"
```

This installs all required packages needed to build and serve the documentation.

---

### 🚀 Run Documentation Locally

Once the installation is complete, start the MkDocs development server with:

```
mkdocs serve
```

You can now view the documentation in your browser at:

👉 [http://127.0.0.1:8000/pages/](http://127.0.0.1:8000/pages/)

---

### Components Library

This guide provides examples of commonly used MkDocs components (using the Material for MkDocs theme) to help you write clear and consistent documentation.

#### Admonitions
Admonitions are used to highlight different types of information using callouts. Use the appropriate type depending on the message you want to convey.

```
!!! note
    This is a note for general information.
```

```
!!! tip
    Here's a helpful tip for users.
```

```
!!! important
    Pay attention! This is an important message.
```

```
!!! warning
    Pay attention! This is a warning.
```

---

#### Code Blocks

Use code blocks to display syntax-highlighted examples. You can also use collapsible blocks for large code snippets.

**Inline code block (not expanded):**

```python
def hello_world():
    print("Hello, world!")
```

**Collapsible (expanding) code block:**

```
??? example "View code"
    ```python
    def hello_world():
        print("Hello, world!")
    ```
```
