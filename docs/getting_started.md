---
icon: material/rocket-launch
---

# Getting Started

This section details how to install the godotkit package using pip, and how to get set up for development.

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
