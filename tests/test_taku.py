from unittest.mock import Mock
from unittest.mock import patch

import pytest
from taku import edit_script
from taku import get_script
from taku import install_scripts
from taku import list_scripts
from taku import new_script
from taku import rm_script
from taku import run_script
from taku import sync_scripts
from taku import systemd_manage
from taku import uninstall_scripts
from taku.exceptions import ScriptAlreadyExistsError
from taku.exceptions import ScriptNotFoundError
from taku.exceptions import TemplateNotFoundError


def test_new_script_basic(tmp_path):
    """Test creating a new script."""
    scripts_dir = tmp_path / "scripts"

    new_script(scripts_dir, "test")

    script_path = scripts_dir / "test" / "test"
    assert script_path.exists()

    content = script_path.read_text()
    assert content.startswith("#!/usr/bin/env bash")
    assert "hello from test" in content
    assert script_path.stat().st_mode & 0o111  # Check executable


def test_new_script_already_exists(tmp_path):
    """Test error when script already exists."""
    scripts_dir = tmp_path / "scripts"
    script_dir = scripts_dir / "test"
    script_dir.mkdir(parents=True)

    with pytest.raises(ScriptAlreadyExistsError):
        new_script(scripts_dir, "test")


def test_new_script_with_template(tmp_path):
    """Test creating a script with template."""
    scripts_dir = tmp_path / "scripts"
    templates_dir = scripts_dir / ".templates"
    templates_dir.mkdir(parents=True)

    # Create a template
    template_file = templates_dir / "python"
    template_file.write_text("#!/usr/bin/env python3\nprint('Hello ${script_name}')")

    new_script(scripts_dir, "myapp", "python", None)

    script_path = scripts_dir / "myapp" / "myapp"
    content = script_path.read_text()
    assert "#!/usr/bin/env python3" in content
    assert "print('Hello myapp')" in content


def test_new_script_with_content(tmp_path):
    """Test creating a script with custom content."""
    scripts_dir = tmp_path / "scripts"
    custom_content = (
        "#!/usr/bin/env python3\nprint('Custom script content')\nprint('Hello world!')"
    )

    new_script(scripts_dir, "custom", None, custom_content)

    script_path = scripts_dir / "custom" / "custom"
    content = script_path.read_text()
    assert content == custom_content
    assert script_path.stat().st_mode & 0o111  # Check executable


def test_new_script_content_and_template_exclusive(tmp_path):
    """Test that content and template parameters are mutually exclusive."""
    scripts_dir = tmp_path / "scripts"
    templates_dir = scripts_dir / ".templates"
    templates_dir.mkdir(parents=True)

    # Create a template
    template_file = templates_dir / "python"
    template_file.write_text("#!/usr/bin/env python3\nprint('Template content')")

    custom_content = "#!/usr/bin/env bash\necho 'Custom content'"

    with pytest.raises(AssertionError):
        new_script(scripts_dir, "test", "python", custom_content)


def test_new_script_template_not_found(tmp_path):
    """Test error when template doesn't exist."""
    scripts_dir = tmp_path / "scripts"

    with pytest.raises(TemplateNotFoundError):
        new_script(scripts_dir, "test", "nonexistent", None)


def test_get_script_basic(tmp_path, capsys):
    """Test getting script details."""
    scripts_dir = tmp_path / "scripts"
    script_dir = scripts_dir / "test"
    script_dir.mkdir(parents=True)

    script_file = script_dir / "test"
    script_file.write_text("echo 'hello'")

    get_script(scripts_dir, "test")

    captured = capsys.readouterr()
    assert "test" in captured.out
    assert "echo 'hello'" in captured.out


def test_get_script_with_meta(tmp_path, capsys):
    """Test getting script with metadata."""
    scripts_dir = tmp_path / "scripts"
    script_dir = scripts_dir / "test"
    script_dir.mkdir(parents=True)

    script_file = script_dir / "test"
    script_file.write_text("echo 'hello'")

    meta_file = script_dir / "meta.toml"
    meta_file.write_text('description = "A test script"\nauthor = "Test User"')

    get_script(scripts_dir, "test")

    captured = capsys.readouterr()
    assert "A test script" in captured.out
    assert "Test User" in captured.out


def test_rm_script(tmp_path, capsys):
    """Test removing a script."""
    scripts_dir = tmp_path / "scripts"
    script_dir = scripts_dir / "test"
    script_dir.mkdir(parents=True)

    script_file = script_dir / "test"
    script_file.write_text("echo 'hello'")

    with patch("taku.uninstall_scripts"):
        rm_script(scripts_dir, "test")

    assert not script_dir.exists()
    captured = capsys.readouterr()
    assert "removed" in captured.out.lower()


def test_list_scripts(tmp_path, capsys):
    """Test listing available scripts."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    (scripts_dir / "script1").mkdir()
    (scripts_dir / "script2").mkdir()
    (scripts_dir / ".templates").mkdir()  # Should be ignored

    list_scripts(scripts_dir)

    captured = capsys.readouterr()
    assert "script1" in captured.out
    assert "script2" in captured.out
    assert ".templates" not in captured.out


@patch("subprocess.run")
def test_edit_script(mock_run, tmp_path):
    """Test editing a script."""
    scripts_dir = tmp_path / "scripts"
    script_path = scripts_dir / "test" / "test"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("echo 'hello'")

    with patch.dict("os.environ", {"EDITOR": "nano"}):
        edit_script(scripts_dir, "test")

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "nano"
    assert str(script_path.resolve()) in args


def test_edit_script_not_found(tmp_path):
    """Test editing non-existent script."""
    scripts_dir = tmp_path / "scripts"

    with pytest.raises(ScriptNotFoundError):
        edit_script(scripts_dir, "test")


@patch("subprocess.run")
def test_run_script(mock_run, tmp_path):
    """Test running a script."""
    scripts_dir = tmp_path / "scripts"
    script_path = scripts_dir / "test" / "test"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("echo 'hello'")

    mock_process = Mock(returncode=0)
    mock_run.return_value = mock_process

    result = run_script(scripts_dir, "test", ["arg1", "arg2"])

    assert result == 0
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert str(script_path.resolve()) == args[0]
    assert args[1:] == ["arg1", "arg2"]


def test_install_scripts_single(tmp_path, capsys):
    """Test installing a single script."""
    scripts_dir = tmp_path / "scripts"
    target_dir = tmp_path / ".local" / "bin"

    # Create script
    script_dir = scripts_dir / "test"
    script_dir.mkdir(parents=True)
    script_file = script_dir / "test"
    script_file.write_text("echo 'hello'")

    with patch("pathlib.Path.home", return_value=tmp_path):
        install_scripts(scripts_dir, "test")

    installed_file = target_dir / "test"
    assert installed_file.exists()

    content = installed_file.read_text()
    assert "#!/usr/bin/env bash" in content
    assert "TAKU_SCRIPTS" in content
    assert "test" in content
    assert installed_file.stat().st_mode & 0o111  # Check executable

    captured = capsys.readouterr()
    assert "Installed" in captured.out and "test" in captured.out


def test_install_scripts_already_exists(tmp_path, capsys):
    """Test installing when file already exists."""
    scripts_dir = tmp_path / "scripts"
    target_dir = tmp_path / ".local" / "bin"
    target_dir.mkdir(parents=True)

    # Create script
    script_dir = scripts_dir / "test"
    script_dir.mkdir(parents=True)
    script_file = script_dir / "test"
    script_file.write_text("echo 'hello'")

    # Create existing file
    existing_file = target_dir / "test"
    existing_file.write_text("existing content")

    with patch("pathlib.Path.home", return_value=tmp_path):
        install_scripts(scripts_dir, "test")

    # Should skip installation
    assert existing_file.read_text() == "existing content"

    captured = capsys.readouterr()
    assert "exists" in captured.out.lower() and "skip" in captured.out.lower()


def test_install_scripts_all(tmp_path, capsys):
    """Test installing all scripts."""
    scripts_dir = tmp_path / "scripts"
    target_dir = tmp_path / ".local" / "bin"

    # Create multiple scripts
    for name in ["script1", "script2"]:
        script_dir = scripts_dir / name
        script_dir.mkdir(parents=True)
        (script_dir / name).write_text(f"echo '{name}'")

    # Create .templates (should be ignored)
    (scripts_dir / ".templates").mkdir()

    with patch("pathlib.Path.home", return_value=tmp_path):
        install_scripts(scripts_dir, "all")

    assert (target_dir / "script1").exists()
    assert (target_dir / "script2").exists()
    assert not (target_dir / ".templates").exists()

    captured = capsys.readouterr()
    assert "script1" in captured.out
    assert "script2" in captured.out


def test_uninstall_scripts_exists(tmp_path, capsys):
    """Test uninstalling existing script."""
    scripts_dir = tmp_path / "scripts"
    target_dir = tmp_path / ".local" / "bin"
    target_dir.mkdir(parents=True)

    # Create script directory
    script_dir = scripts_dir / "test"
    script_dir.mkdir(parents=True)

    # Create installed file
    installed_file = target_dir / "test"
    installed_file.write_text("#!/usr/bin/env bash\necho test")

    with patch("pathlib.Path.home", return_value=tmp_path):
        uninstall_scripts(scripts_dir, "test")

    assert not installed_file.exists()

    captured = capsys.readouterr()
    assert "uninstall" in captured.out.lower() and "test" in captured.out


def test_uninstall_scripts_not_found(tmp_path, capsys):
    """Test uninstalling non-existent script."""
    scripts_dir = tmp_path / "scripts"
    tmp_path / ".local" / "bin"

    # Create script directory but no installed file
    script_dir = scripts_dir / "test"
    script_dir.mkdir(parents=True)

    with patch("pathlib.Path.home", return_value=tmp_path):
        uninstall_scripts(scripts_dir, "test")

    captured = capsys.readouterr()
    assert "not found" in captured.out.lower()


@patch("taku.push_scripts")
@patch("taku.pull_scripts")
def test_sync_scripts_push(mock_pull, mock_push, tmp_path):
    """Test sync with push option."""
    scripts_dir = tmp_path / "scripts"

    sync_scripts(scripts_dir, push=True)

    mock_push.assert_called_once_with(scripts_dir)
    mock_pull.assert_not_called()


@patch("taku.push_scripts")
@patch("taku.pull_scripts")
def test_sync_scripts_pull(mock_pull, mock_push, tmp_path):
    """Test sync with pull option."""
    scripts_dir = tmp_path / "scripts"

    sync_scripts(scripts_dir)

    mock_pull.assert_called_once_with(scripts_dir)
    mock_push.assert_not_called()


@patch("taku.systemd_install")
@patch("taku.systemd_remove")
def test_systemd_manage_install(mock_remove, mock_install, tmp_path):
    """Test systemd management with install."""
    scripts_dir = tmp_path / "scripts"

    systemd_manage(scripts_dir, install=True, remove=False)

    mock_install.assert_called_once_with(scripts_dir)
    mock_remove.assert_not_called()


@patch("taku.systemd_install")
@patch("taku.systemd_remove")
def test_systemd_manage_remove(mock_remove, mock_install, tmp_path):
    """Test systemd management with remove."""
    scripts_dir = tmp_path / "scripts"

    systemd_manage(scripts_dir, install=False, remove=True)

    mock_remove.assert_called_once()
    mock_install.assert_not_called()
