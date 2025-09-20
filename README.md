# Taku

Simple script manager for creating, running, and syncing scripts.

[![Publish to PyPI](https://github.com/Tobi-De/taku/actions/workflows/publish.yml/badge.svg)](https://github.com/Tobi-De/taku/actions/workflows/publish.yml)[![PyPI - Version](https://img.shields.io/pypi/v/taku-cli.svg)](https://pypi.org/project/taku-cli)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/taku-cli.svg)](https://pypi.org/project/taku-cli)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Tobi-De/taku-cli/blob/main/LICENSE.txt)
[![Status](https://img.shields.io/pypi/status/taku-cli.svg)](https://pypi.org/project/taku-cli)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

## Installation

```bash
uv tool install taku-cli
```

or

```bash
uv tool install "taku-cli[bling]" # just adds some colors
```

## Quick Start

```bash
# Create a new script
taku new hello

# Edit a script
taku edit hello

# Run a script
taku run hello

# Shortcut to running a script, tax stands for takux
tax hello

```

## Commands

- `taku new <name> [--template/-t <name>]` - Create a new script from template
- `taku list` - List all scripts, add `-t` to also list templates
- `taku get <name>` - Show script details
- `taku edit <name>` - Edit a script (auto-pushes to git if repository)
- `taku run <name> [args...]` - Run a script with optional arguments
- `taku rm <name>` - Remove a script (auto-pushes to git if repository)
- `taku install <name|all>` - Install script to `~/.local/bin`
- `taku uninstall <name|all>` - Remove script from `~/.local/bin`

## Configuration

Set the scripts directory:
```bash
export TAKU_SCRIPTS=~/my-scripts
```

Default: `~/scripts`

## Templates

Create templates in `<scripts-dir>/.templates/` and use with:
```bash
taku new myapp --template python
```

Template resolution order:
1. `<scripts-dir>/.templates/<template-name>`
2. `./<template-name>` (current directory)

Templates can use `${script_name}` variable for substitution.

Example Python template (`~/.scripts/.templates/python`):

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///


def main() -> None:
    print("Hello from $script_name!")


if __name__ == "__main__":
    main()
```

## Git Integration

If your `scripts` directory is a Git repository, **taku** will automatically commit and push changes whenever you edit or remove scripts.
This keeps your changes synced, but to complete the auto-sync feature you also need to set up each machine to regularly pull the latest scripts.

1. Open your crontab:

   ```bash
   crontab -e
   ```

2. Add a line to pull updates every 15 minutes (adjust the path to your scripts directory):

   ```bash
   */15 * * * * cd /home/tobi/scripts && git pull --rebase >/dev/null 2>&1
   ```
