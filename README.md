# Taku

Simple script manager for creating, running, and syncing scripts.

[![Publish Package](https://github.com/Tobi-De/taku-cli/actions/workflows/publish.yml/badge.svg)](https://github.com/Tobi-De/taku-cli/actions/workflows/publish.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/taku-cli.svg)](https://pypi.org/project/taku-cli)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/taku-cli.svg)](https://pypi.org/project/taku-cli)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Tobi-De/taku-cli/blob/main/LICENSE.txt)
[![Status](https://img.shields.io/pypi/status/taku-cli.svg)](https://pypi.org/project/taku-cli)

## Installation

```bash
uv tool install taku-cli
```

or

```bash
uv tool install "taku-cli[bling]" # just add some colors
```

## Quick Start

```bash
# Create a new script
taku new hello

# Edit a script
taku edit hello

# Run a script
taku run hello

```

## Commands

- `taku new <name> [--template/-t <name>]` - Create a new script from template
- `taku list` - List all scripts
- `taku get <name>` - Show script details
- `taku edit <name>` - Edit a script
- `taku run <name> [args...]` - Run a script with optional arguments
- `taku rm <name>` - Remove a script
- `taku install <name|all>` - Install script to `~/.local/bin`
- `taku uninstall <name|all>` - Remove script from `~/.local/bin`
- `taku sync --push` - Commit and push changes to git
- `taku sync --pull` - Pull changes from git
- `taku systemd --install` - Install systemd timer for auto-sync
- `taku systemd --remove` - Remove systemd timer

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
