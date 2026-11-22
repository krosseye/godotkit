---
icon: material/tag
---

# Version Format

godotkit writes every Godot version in one canonical form, the one the engine
uses itself (`GODOT_VERSION_FULL_CONFIG`). It's what `str(GodotVersion)` returns
and what goes into a project's `.godot-version` file.

| Version | Canonical | `display_name` | `to_tag()` |
| --- | --- | --- | --- |
| 4.3 | `4.3.stable` | 4.3 | `4.3-stable` |
| 4.3.1 | `4.3.1.stable` | 4.3.1 | `4.3.1-stable` |
| 4.4 RC 2 | `4.4.rc2` | 4.4-rc2 | `4.4-rc2` |
| 3.2.4 beta 5 | `3.2.4.beta5` | 3.2.4-beta5 | `3.2.4-beta5` |
| 4.3, C# | `4.3.stable.mono` | 4.3 (.NET) | `4.3-stable` |
| 3.6, C# | `3.6.stable.mono` | 3.6 (Mono) | `3.6-stable` |
| 4.4 RC 2, C# | `4.4.rc2.mono` | 4.4-rc2 (.NET) | `4.4-rc2` |

The canonical form is also the name of the editor's export templates folder,
the start of `godot --version` output (`4.3.stable.mono.official.77dcf97d8`),
and a feature tag that `project.godot` accepts. It's lowercase with only dots,
so it needs no quoting in a shell and is safe in file names.

A version is always exact, never a range: `4.3.stable` means 4.3.0 stable, not
"the latest 4.3.x".

## Grammar

What godotkit writes:

```ebnf
version = number "." status [ ".mono" ] ;
number  = int "." int [ "." pos ] ;          (* patch left out when it is 0 *)
status  = "stable" | pre [ pos ] ;           (* no number on stable *)
pre     = "dev" | "alpha" | "beta" | "rc" ;
int     = "0" | pos ;
pos     = digit1-9 { digit } ;               (* ASCII digits only *)
```

`mono` marks the C# build. Godot's version strings and download file names
call it mono in both Godot 3 and Godot 4, so godotkit does too. ".NET" and
"Mono" only appear in `display_name`, picked by major version.

## What readers accept

`GodotVersion.parse` accepts more than godotkit writes, so a version can be
typed the short way. Matching ignores case and surrounding whitespace.

- An optional `v` prefix: `v4.3`.
- `-` or `.` before the channel: `4.4-rc2`, `4.4.rc2`.
- No channel, meaning stable: `4.3`.
- A zero patch: `4.3.0`.
- A C# marker, `mono` or `dotnet`, after `.`, `-`, `_`, `+` or a space:
  `4.3 mono`, `4.3-dotnet`, `4.3-stable_mono`.
- The `display_name` form: `4.3 (.NET)`, `3.6 (Mono)`.

It rejects anything else: an unknown channel, a number on stable
(`4.3-stable2`), a channel number of 0 (`4.4-rc0`), four-part versions
(`2.0.4.1`), and anything left over after the version, such as `.double` or a
build name and hash from `godot --version`.

## The `.godot-version` file

A project pins its engine version in a `.godot-version` file next to
`project.godot`.

- **Writing:** one line in the canonical form, UTF-8, ending in a single LF.
- **Reading:**
  - The version is the first line that isn't blank or a `#` comment.
  - Later lines are ignored, which leaves room for `key=value` lines in future.
  - Files saved by Windows editors are fine: a byte order mark at the start
    (an invisible marker some editors add) and Windows `\r\n` line endings
    are both ignored.
- **Errors:** a file with no valid version raises
  [`VersionFileError`](api_reference/exceptions.md). It is also a `ValueError`.

```text
# Pinned for the game jam build
4.3.stable.mono
```

Use `godotkit.project.parse.read_engine_version` and `set_engine_version`
rather than reading the file yourself.
