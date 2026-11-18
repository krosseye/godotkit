![GodotKit](https://raw.githubusercontent.com/krosseye/godotkit/main/logo.png)

[![CI](https://github.com/krosseye/godotkit/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/krosseye/godotkit/actions/workflows/release.yml?query=branch%3Amain)
[![Latest release](https://img.shields.io/github/v/release/krosseye/godotkit)](https://github.com/krosseye/godotkit/releases/latest)
[![License](https://img.shields.io/github/license/krosseye/godotkit)](https://github.com/krosseye/godotkit/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://krosseye.github.io/godotkit/)

**GodotKit** is a Python library providing functions and classes for the automation of tasks related to [Godot Engine](https://godotengine.org/) releases and projects.

It was originally developed to power [GoGo](https://github.com/krosseye/gogo), but is a standalone package that can be used in any Python project requiring programmatic interaction with Godot files and versions.

---

## Installation

Install the latest release from PyPI:

```bash
pip install godotkit
```

Or from the GitHub repository:

```bash
pip install git+https://github.com/krosseye/godotkit.git
```

## Setup for Developers

If you want to contribute to GodotKit, follow these steps to set up your development environment.

1. **Clone the Repository**

   ```bash
   git clone https://github.com/krosseye/godotkit.git
   cd godotkit
   ```

2. **Install Dependencies**

   This command installs all dependencies, including those for testing and documentation:

   ```bash
   uv sync --all-extras
   ```

3. **Install Module in Editable Mode**

   This ensures that changes you make to the source code are instantly reflected in your environment:

   ```bash
   uv pip install -e .
   ```

4. **Setup Pre-commit Hooks**

   Install the pre-commit hooks to automatically run checks before you commit your code:

   ```bash
   uv run prek install
   ```
