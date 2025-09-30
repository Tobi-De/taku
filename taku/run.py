import sys
from argparse import REMAINDER
from os import getenv
from pathlib import Path
from subprocess import run as subprocess_run
from typing import Annotated

from .command_parser import ArgSpec
from .exceptions import MissingScriptName
from .exceptions import ScriptNotFoundError

default_scripts_dir = getenv("TAKU_SCRIPTS", Path.home() / "scripts")


def run_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the script to run")],
    args: Annotated[
        list[str] | None,
        "args",
        ArgSpec(nargs=REMAINDER, help="Arguments to pass to the script"),
    ] = None,
):
    """Run a script"""
    args = args or []
    _, script_path = _resolve_script(scripts, name)
    try:
        process = subprocess_run(
            [str(script_path.resolve())] + args,
            stdin=None,
            stdout=None,
            stderr=None,
            check=False,
            text=True,
        )
    except KeyboardInterrupt:
        sys.exit(0)
    sys.exit(process.returncode)


def complete(prefix: str | None = None):
    try:
        names = _list_scripts(Path(default_scripts_dir))
    except FileNotFoundError:
        return
    if prefix:
        names = [name for name in names if name.startswith(prefix)]
    print("\n".join(names))


def _list_scripts(scripts: Path) -> list[str]:
    return [
        s.name for s in scripts.iterdir() if not s.name.startswith(".") and s.is_dir()
    ]


def _resolve_script(
    scripts: Path, name: str, raise_error: bool = True
) -> tuple[str, Path]:
    script_name = name.split(".")[0]
    script_path = scripts / script_name / script_name

    if raise_error and not script_path.exists():
        raise ScriptNotFoundError(f"Script '{name}' not found")

    return script_name, script_path


def main():
    arg_size = len(sys.argv)
    if arg_size >= 2 and sys.argv[1] == "_complete":
        complete(sys.argv[2] if arg_size > 2 else None)
        sys.exit(0)
    if arg_size < 2:
        raise MissingScriptName("Missing script name")
    run_script(Path(default_scripts_dir), sys.argv[1], sys.argv[2:])
