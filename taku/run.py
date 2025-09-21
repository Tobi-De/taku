import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

from .command_parser import ArgSpec
from .exceptions import MissingScriptName
from .exceptions import ScriptNotFoundError

default_scripts_dir = os.getenv("TAKU_SCRIPTS", Path.home() / "scripts")


def run_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the script to run")],
    args: Annotated[
        list[str] | None,
        "args",
        ArgSpec(nargs=argparse.REMAINDER, help="Arguments to pass to the script"),
    ] = None,
):
    """Run a script"""
    args = args or []
    _, script_path = _resolve_script(scripts, name)
    process = subprocess.run(
        [str(script_path.resolve())] + args,
        stdin=None,
        stdout=None,
        stderr=None,
        check=False,
        text=True,
    )
    return process.returncode


def _resolve_script(
    scripts: Path, name: str, raise_error: bool = True
) -> tuple[str, Path]:
    script_name = name.split(".")[0]
    script_path = scripts / script_name / script_name

    if raise_error and not script_path.exists():
        raise ScriptNotFoundError(f"Script '{name}' not found")

    return script_name, script_path


def main():
    if len(sys.argv) < 2:
        raise MissingScriptName("Missing script name")
    run_script(Path(default_scripts_dir), sys.argv[1], sys.argv[2:])
