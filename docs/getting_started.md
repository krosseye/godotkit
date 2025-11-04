---
icon: material/rocket-launch
---

# Getting Started

This section details how to install the godotkit package using pip, and how to get set up for development.

## Installation

You have two primary ways to install the latest stable version of `godotkit` from GitHub using your preferred package manager:

1. **From Source:**

   Use this command to install directly from the GitHub repository:

   ```bash
   pip install git+https://github.com/krosseye/godotkit.git
   ```

2. **From Release:**

   To install the latest prebuilt release, you can use the appropriate command for your operating system's shell:

   - **Bash/Linux/MacOS:**

     ```bash
     pip install $(curl -s https://api.github.com/repos/krosseye/godotkit/releases/latest | grep 'browser_download_url.*\.whl' | cut -d\" -f4)
     ```

   - **PowerShell/Windows:**

     ```powershell
     pip install ( (Invoke-RestMethod -Uri 'https://api.github.com/repos/krosseye/godotkit/releases/latest').assets | Where-Object { $_.name -like '*.whl' } ).browser_download_url
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
