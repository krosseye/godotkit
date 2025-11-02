---
icon: material/rocket-launch
---

# Getting Started

This section details how to install the godotkit package using pip.

## Installation

You have two primary ways to install:

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
