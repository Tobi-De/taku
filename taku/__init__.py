import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import tomllib
from pathlib import Path
from string import Template
from typing import Annotated

import tomli_w

# Ensure unbuffered output for immediate display
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from .command_parser import ArgSpec
from .command_parser import command
from .exceptions import ScriptAlreadyExistsError
from .exceptions import TemplateNotFoundError
from .run import run_script, _resolve_script, default_scripts_dir, _list_scripts

try:
    from rich_argparse import ArgumentDefaultsRichHelpFormatter

    # from rich import print as rprint

    formatter_class = ArgumentDefaultsRichHelpFormatter
    # print = lambda *args, **kwargs: rprint(*args, **kwargs)  # type: ignore
except ImportError:
    formatter_class = argparse.ArgumentDefaultsHelpFormatter


parser = argparse.ArgumentParser(
    prog="taku",
    description="Manage and execute scripts with ease",
    epilog="For more information, visit https://github.com/Tobi-De/taku",
    formatter_class=formatter_class,
)

parser.add_argument(
    "--scripts",
    "-s",
    type=Path,
    default=default_scripts_dir,
    help="Scripts directory",
)
parser.add_argument("--version", action="version", version="%(prog)s 0.4.12")
subparsers = parser.add_subparsers(dest="command", required=True)

cmd = command(subparsers)


def main() -> None:
    args = parser.parse_args()
    args.func(**vars(args))


cmd("run", formatter_class=formatter_class)(run_script)


@cmd("list", aliases=["ls"], formatter_class=formatter_class)
def list_scripts(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    templates: Annotated[
        bool,
        "--templates",
        "-t",
        ArgSpec(action="store_true", help="List templates too"),
    ] = False,
):
    """List all available scripts"""
    if templates:
        tpl_list = list((scripts / ".templates").iterdir())
        tpl_list.sort()
        templates_list = [f"- {f.name}" for f in tpl_list if f.is_file()]
        print(f"Available templates ({len(templates_list)}):")
        print("\n".join(templates_list))

    def _script_display(name):
        metadata_file = scripts / name / "meta.toml"
        if not metadata_file.exists():
            return name
        metadata = tomllib.loads(metadata_file.read_text())
        tags = metadata.get("tags", [])
        if not tags:
            return name
        return f"{name} ({' - '.join(tags)})"

    scripts_list = _list_scripts(scripts)
    scripts_list.sort()
    scripts_list = [f"- {_script_display(s)}" for s in scripts_list]
    print(f"Available scripts ({len(scripts_list)}):")
    print("\n".join(scripts_list))


@cmd("new", formatter_class=formatter_class)
def new_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the new script")],
    template_name: Annotated[
        str | None,
        "--template",
        "-t",
        ArgSpec(help="Optional template for the script", dest="template_name"),
    ] = None,
    content: Annotated[
        str | None,
        "--content",
        "-c",
        ArgSpec(help="Content for the new script"),
    ] = None,
):
    """Create a new script"""

    assert not (content and template_name), (
        "Cannot specify both --content and --template options"
    )

    scripts.mkdir(parents=True, exist_ok=True)
    script_name, script_path = _resolve_script(scripts, name, raise_error=False)
    script_folder = script_path.parent
    if script_folder.exists():
        raise ScriptAlreadyExistsError(f"The script {script_name} already exists")

    if content:
        content = (
            content if content.startswith("#!") else f"#!/usr/bin/env bash\n{content}"
        )
        script_content = content
    elif template_name:
        if not (template := scripts / ".templates" / template_name).exists():
            if not (template := Path() / template_name).exists():
                raise TemplateNotFoundError(f"Template {template} does not exists")
        script_content = Template(template.read_text()).substitute(script_name=name)
    else:
        script_content = f"#!/usr/bin/env bash\n\necho 'hello from {script_name}'"
    script_folder.mkdir(parents=True, exist_ok=True)
    script = script_folder / name
    script.touch()
    script.write_text(script_content)
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if "." in name:
        (script.parent / script_name).symlink_to(script.name)
    print(f"script {name} created")


@cmd("get", formatter_class=formatter_class)
def get_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the script")],
    script: Annotated[
        bool,
        "--script",
        "-s",
        ArgSpec(action="store_true", help="Print only script content"),
    ] = False,
    metadata: Annotated[
        bool,
        "--metadata",
        "-m",
        ArgSpec(action="store_true", help="Print only script metadata"),
    ] = False,
):
    """Get details about an existing script"""

    assert not (script and metadata), (
        "Cannot specify both --script and --metadata options"
    )

    _, script_path = _resolve_script(scripts, name)
    content = script_path.read_text()
    if script:
        print(content)
        return
    meta = script_path.parent / "meta.toml"
    data = {"name": name}
    if meta.exists():
        data |= tomllib.loads(meta.read_text())
    if not metadata:
        data["content"] = content
    print("---")
    for key, value in data.items():
        print(key, ":", value)


@cmd("rm", formatter_class=formatter_class)
def rm_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the script")],
):
    """Remove an existing script"""
    script_name, script_path = _resolve_script(scripts, name)
    script_folder = script_path.parent
    uninstall_scripts(scripts, name, push=False)
    shutil.rmtree(script_folder, ignore_errors=True)
    print(f"Script {script_name} removed")
    push_scripts(scripts)


@cmd("edit", formatter_class=formatter_class)
def edit_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the script to edit")],
    metadata: Annotated[
        bool,
        "--metadata",
        "-m",
        ArgSpec(action="store_true", help="Edit script metadata"),
    ] = False,
):
    """Edit an existing script"""

    _, script_path = _resolve_script(scripts, name)
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    if metadata:
        subprocess.run([editor, (script_path.parent / "meta.toml").resolve()])
    else:
        subprocess.run([editor, script_path.resolve()])
    push_scripts(scripts)


@cmd("install", formatter_class=formatter_class)
def install_scripts(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[
        str, ArgSpec(help="Name of the script to install, use 'all' for all scripts")
    ],
    install_name: Annotated[
        str | None,
        "--install-name",
        "-i",
        ArgSpec(
            help="Optional name when installed in PATH, only used when installing a single script"
        ),
    ] = None,
    target_dir: Annotated[
        Path,
        "--target-dir",
        "-t",
        ArgSpec(help="Target directory, should be in the PATH"),
    ] = Path.home() / ".local/bin",
):
    """Install a script to the specified target directory"""
    target_dir.mkdir(parents=True, exist_ok=True)

    install_name = install_name or name

    if name != "all":
        _resolve_script(scripts, name)

    to_install = (
        {name: install_name}
        if name != "all"
        else {s: s for s in _list_scripts(scripts)}
    )
    exec_path = Path(sys.executable).parent / "tax"
    host = platform.node()
    for script_name, script_install_name in to_install.items():
        target_file = target_dir / script_install_name
        metadata_file = scripts / script_name / "meta.toml"

        if target_file.exists():
            print(
                f"Error: File '{target_file}' already exists. Skipping {script_name}."
            )
            continue

        # Create shim script
        content = f"""#!/usr/bin/env bash
# Shim for taku script {script_name}
export TAKU_SCRIPTS="{scripts.resolve()}"
exec {exec_path} "{script_name}" "$@"
"""
        target_file.write_text(content)
        target_file.chmod(
            target_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
        metadata = (
            tomllib.loads(metadata_file.read_text()) if metadata_file.exists() else {}
        )
        metadata[host] = {
            "install_name": script_install_name,
            "target_dir": str(target_dir),
        }
        metadata_file.write_text(tomli_w.dumps(metadata))
        print(f"Installed {script_name} to {target_file}")
    push_scripts(scripts)


@cmd("uninstall", formatter_class=formatter_class)
def uninstall_scripts(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[
        str, ArgSpec(help="Name of the script to uninstall, use 'all' for all scripts")
    ],
    push: Annotated[bool, ArgSpec(ignore=True, help="Auto-push changes to git")] = True,
):
    """Uninstall a script using its metadata"""

    if name != "all":
        _resolve_script(scripts, name)

    to_uninstall = [name] if name != "all" else _list_scripts(scripts)
    host = platform.node()
    for script_name in to_uninstall:
        metadata_file = scripts / script_name / "meta.toml"
        if not metadata_file.exists():
            print(f"Skipping {script_name}, no metadata file found")
            continue

        metadata = tomllib.loads(metadata_file.read_text())

        # Check if host has metadata
        if host not in metadata:
            print(f"No installation metadata found for {script_name} on host {host}")
            continue

        host_metadata = metadata[host]
        target_dir = Path(host_metadata["target_dir"])
        target_file = target_dir / host_metadata["install_name"]

        if target_file.exists():
            metadata.pop(host, None)
            metadata_file.write_text(tomli_w.dumps(metadata))
            target_file.unlink()
            print(f"Uninstalled {script_name} from {target_file}")
        else:
            print(f"Warning: {script_name} not found in {target_dir}")
    if push:
        push_scripts(scripts)


def push_scripts(scripts: Path):
    """Auto-push changes to git if it's a git repo with changes"""
    result = subprocess.run(
        ["git", "-C", str(scripts), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    # not a git repo, we do nothing
    if result.returncode != 0:
        return

    # If no output, no changes to commit
    if not result.stdout.strip():
        return

    try:
        # Add, commit, and push
        subprocess.run(["git", "-C", str(scripts), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(scripts), "commit", "-m", "Auto-sync: Update scripts"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
        print("Please check your git configuration and resolve any issues manually.")
        return
    subprocess.Popen(
        ["git", "-C", str(scripts), "push"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == "__main__":
    main()
