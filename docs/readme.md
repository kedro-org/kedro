
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

### 🧩 Components Library

Below are examples of commonly used components in the documentation:

#### 🔔 Note

```
> **Note**  
> This is a note block to highlight important information.
```

**Rendered Output:**

```
> This is a note block to highlight important information.
```

---

#### 💻 Code Block

```python
def hello_world():
    print("Hello, world!")
```

**Rendered Output:**

```python
def hello_world():
    print("Hello, world!")
```