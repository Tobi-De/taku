import argparse
import os
import shutil
import stat
import subprocess
import sys
import tomllib
from pathlib import Path
from string import Template
from typing import Annotated

from .command_parser import ArgSpec
from .command_parser import command
from .exceptions import ScriptAlreadyExistsError
from .exceptions import ScriptNotFoundError
from .exceptions import TemplateNotFoundError


parser = argparse.ArgumentParser(
    prog="taku",
    description="Manage and execute scripts with ease",
    epilog="For more information, visit https://github.com/Tobi-De/taku",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

default_scripts_dir = os.getenv("TAKU_SCRIPTS", Path.home() / "scripts")
parser.add_argument(
    "--scripts",
    "-s",
    type=Path,
    default=default_scripts_dir,
    help=f"Scripts directory, default to {default_scripts_dir}",
)
parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
subparsers = parser.add_subparsers(dest="command", required=True)

cmd = command(subparsers)


def main() -> None:
    args = parser.parse_args()
    args.func(**vars(args))


def _resolve_script(
    scripts: Path, name: str, raise_error: bool = False
) -> tuple[str, Path]:
    script_name = name.split(".")[0]
    script_path = scripts / script_name / script_name

    if raise_error and not script_path.exists():
        raise ScriptNotFoundError(f"Script '{name}' not found")

    return script_name, script_path


def _list_scripts(scripts: Path) -> list[str]:
    return [s.name for s in scripts.iterdir() if s.name != ".templates"]


@cmd("list")
def list_scripts(scripts: Annotated[Path, ArgSpec(ignore=True)]):
    """List all available scripts"""
    print("Available scripts:")
    print("\n".join(f"- {name}" for name in _list_scripts(scripts)))


@cmd("new")
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
    script_name, script_path = _resolve_script(scripts, name)
    script_folder = script_path.parent
    if script_folder.exists():
        raise ScriptAlreadyExistsError(f"The script {script_name} already exists")

    if content:
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


@cmd("get")
def get_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the script")],
):
    """Get details about an existing script"""
    _, script_path = _resolve_script(scripts, name, raise_error=True)
    meta = script_path.parent / "meta.toml"
    data = {"name": name}
    if meta.exists():
        data |= tomllib.loads(meta.read_text())
    data["content"] = script_path.read_text()
    print("---")
    for key, value in data.items():
        print(key, ":", value)


@cmd("rm")
def rm_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the script")],
):
    """Remove an existing script"""
    script_name, script_path = _resolve_script(scripts, name, raise_error=True)
    script_folder = script_path.parent
    uninstall_scripts(scripts, name)
    shutil.rmtree(script_folder, ignore_errors=True)
    print(f"Script {script_name} removed")


@cmd("edit")
def edit_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the script to edit")],
):
    """Edit an existing script"""
    script_path = scripts / name / name

    if not script_path.exists():
        raise ScriptNotFoundError(f"Script '{name}' not found")

    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    subprocess.run([editor, str(script_path.resolve())])


@cmd("run")
def run_script(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[str, ArgSpec(help="Name of the script to run")],
    args: Annotated[
        list[str],
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


@cmd("install")
def install_scripts(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[
        str, ArgSpec(help="Name of the script to install, use 'all' for all scripts")
    ],
):
    """Install a script to ~/.local/bin"""
    target_dir = Path.home() / ".local/bin"
    target_dir.mkdir(parents=True, exist_ok=True)

    if name != "all":
        _resolve_script(scripts, name, raise_error=True)

    to_install = [name] if name != "all" else _list_scripts(scripts)
    exec_path = Path(sys.executable).parent / "taku"

    for script_name in to_install:
        target_file = target_dir / script_name

        if target_file.exists():
            print(
                f"Error: File '{target_file}' already exists. Skipping {script_name}."
            )
            continue

        # Create shim script
        content = f"""#!/usr/bin/env bash
# Shim for taku script {script_name}
export TAKU_SCRIPTS="{scripts.resolve()}"
exec {exec_path} run "{script_name}" "$@"
"""
        target_file.write_text(content)
        target_file.chmod(
            target_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
        print(f"Installed {script_name} to {target_file}")


@cmd("uninstall")
def uninstall_scripts(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    name: Annotated[
        str, ArgSpec(help="Name of the script to uninstall, use 'all' for all scripts")
    ],
):
    """Uninstall a script from ~/.local/bin"""
    target_dir = Path.home() / ".local/bin"

    if name != "all":
        _resolve_script(scripts, name)

    to_uninstall = [name] if name != "all" else _list_scripts(scripts)

    for script_name in to_uninstall:
        target_file = target_dir / script_name

        if target_file.exists():
            target_file.unlink()
            print(f"Uninstalled {script_name} from {target_file}")
        else:
            print(f"Warning: {script_name} not found in {target_dir}")


@cmd("sync")
def sync_scripts(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    push: Annotated[
        bool,
        "--push",
        ArgSpec(action="store_true", help="Push local changes to remote"),
    ] = False,
    pull: Annotated[
        bool,
        "--pull",
        ArgSpec(action="store_true", help="Pull remote changes to local"),
    ] = False,
):
    """Sync scripts"""
    if push:
        push_scripts(scripts)
    if pull:
        pull_scripts(scripts)


def push_scripts(scripts: Path):
    if not is_git_repo(scripts):
        print(f"{scripts} is not a git repo, nothing to sync")
        return

    try:
        result = subprocess.run(
            ["git", "-C", str(scripts), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout.strip():
            subprocess.run(["git", "-C", str(scripts), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(scripts),
                    "commit",
                    "-m",
                    "Auto-sync: Update scripts",
                ],
                check=True,
            )
            print("Committed local changes")
        else:
            print("No local changes to commit")

        subprocess.run(["git", "-C", str(scripts), "push"], check=True)
        print("Successfully pushed changes to remote")

    except subprocess.CalledProcessError as e:
        print(f"Error during push: {e}")
        return


def pull_scripts(scripts: Path):
    if not is_git_repo(scripts):
        print(f"{scripts} is not a git repo, nothing to sync")
        return

    try:
        result = subprocess.run(
            ["git", "-C", str(scripts), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip():
            print(
                "Warning: You have uncommitted local changes. Stashing them before pull."
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(scripts),
                    "stash",
                    "push",
                    "-m",
                    "Auto-stash before pull",
                ],
                check=True,
            )
            stashed = True
        else:
            stashed = False

        if subprocess.run(["git", "-C", str(scripts), "pull"]).returncode == 0:
            print("Successfully pulled changes from remote")

        if stashed:
            try:
                subprocess.run(["git", "-C", str(scripts), "stash", "pop"], check=True)
                print("Restored stashed local changes")
            except subprocess.CalledProcessError:
                print(
                    "Warning: Could not restore stashed changes. Check 'git stash list' manually."
                )

    except subprocess.CalledProcessError as e:
        print(f"Error during pull: {e}")
        return


@cmd("systemd")
def systemd_manage(
    scripts: Annotated[Path, ArgSpec(ignore=True)],
    install: Annotated[
        bool, "--install", ArgSpec(action="store_true", help="Install systemd service")
    ] = False,
    remove: Annotated[
        bool, "--remove", ArgSpec(action="store_true", help="Remove systemd service")
    ] = False,
):
    """Systemd install and remove service"""
    if install:
        systemd_install(scripts)
    if remove:
        systemd_remove()


systemd_user_dir = Path.home() / ".config/systemd/user"
service_file = systemd_user_dir / "taku-sync.service"
timer_file = systemd_user_dir / "taku-sync.timer"


def systemd_install(scripts: Path):
    if not is_git_repo(scripts):
        print(f"{scripts} is not a git repo, nothing to sync")
        return

    systemd_user_dir.mkdir(parents=True, exist_ok=True)

    service_content = """\
[Unit]
Description=Taku automatic script sync

[Service]
Type=oneshot
ExecStart={exec_path} --scripts {scripts} sync --pull

"""

    timer_content = """\
[Unit]
Description=Taku automatic script sync timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
"""

    service_file.write_text(
        service_content.format(
            scripts=scripts, exec_path=Path(sys.executable).parent / "taku"
        )
    )
    timer_file.write_text(timer_content)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(
        ["systemctl", "--user", "enable", "--now", service_file.name], check=True
    )
    subprocess.run(
        ["systemctl", "--user", "enable", "--now", timer_file.name], check=True
    )
    print("Taku systemd service and timer installed and enabled.")


def systemd_remove():
    for name, f in {"timer": timer_file, "service": service_file}.items():
        if not f.exists():
            print(f"Taku {name} does not exist.")
            continue
        subprocess.run(["systemctl", "--user", "disable", "--now", f.name], check=False)
        f.unlink()
        print(f"Taku {name} removed.")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)


def is_git_repo(dir_path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(dir_path), "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        output = result.stdout.decode().strip()
        return output == "true"
    except subprocess.CalledProcessError:
        return False


if __name__ == "__main__":
    main()
