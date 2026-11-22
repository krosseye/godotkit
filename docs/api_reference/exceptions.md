# Exceptions

godotkit raises errors by one rule:

| Situation | Exception |
| --- | --- |
| A bad argument (an invalid version string, an unknown option) | `ValueError` |
| A path that doesn't exist (an engine folder, a binary, `project.godot`) | `FileNotFoundError` |
| The current OS or CPU isn't supported | `NotImplementedError` |
| An operation that failed (a download, an extraction, a git command, a release lookup) | a `GodotkitError` subclass |

Catch `GodotkitError` to handle every failed operation in one place. The engine errors can also be imported from `godotkit.engine`, and `VersionFileError` from `godotkit.project`.

::: godotkit.exceptions.GodotkitError

::: godotkit.exceptions.DownloadError

::: godotkit.exceptions.DownloadCancelled

::: godotkit.exceptions.ExtractError

::: godotkit.exceptions.ReleaseNotFoundError

::: godotkit.exceptions.AssetNotFoundError

::: godotkit.exceptions.VersionFileError

::: godotkit.exceptions.GitError
