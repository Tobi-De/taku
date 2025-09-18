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
    # Check executable
    assert script_path.stat().st_mode & 0o111


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

    new_script(scripts_dir, "test", None, "echo 'hello'")
    get_script(scripts_dir, "test")

    captured = capsys.readouterr()
    assert "test" in captured.out
    assert "echo 'hello'" in captured.out


def test_get_script_with_meta(tmp_path, capsys):
    """Test getting script with metadata."""
    scripts_dir = tmp_path / "scripts"

    new_script(scripts_dir, "test", None, "echo 'hello'")

    # Add metadata manually since there's no function for this yet
    script_dir = scripts_dir / "test"
    meta_file = script_dir / "meta.toml"
    meta_file.write_text('description = "A test script"\nauthor = "Test User"')

    get_script(scripts_dir, "test")

    captured = capsys.readouterr()
    assert "A test script" in captured.out
    assert "Test User" in captured.out


def test_rm_script(tmp_path, capsys):
    """Test removing a script."""
    scripts_dir = tmp_path / "scripts"

    new_script(scripts_dir, "test", None, "echo 'hello'")
    script_dir = scripts_dir / "test"
    assert script_dir.exists()  # Verify it was created

    with patch("taku.uninstall_scripts"), patch("taku.push_scripts"):
        rm_script(scripts_dir, "test")

    assert not script_dir.exists()
    captured = capsys.readouterr()
    assert "removed" in captured.out.lower()


def test_list_scripts(tmp_path, capsys):
    """Test listing available scripts."""
    scripts_dir = tmp_path / "scripts"

    new_script(scripts_dir, "script1", None, "echo 'script1'")
    new_script(scripts_dir, "script2", None, "echo 'script2'")

    # Create .templates directory (should be ignored in listing)
    (scripts_dir / ".templates").mkdir(exist_ok=True)

    list_scripts(scripts_dir)

    captured = capsys.readouterr()
    assert "script1" in captured.out
    assert "script2" in captured.out
    assert ".templates" not in captured.out


# @patch("subprocess.run")
# def test_edit_script(mock_run, tmp_path):
#     """Test editing a script."""

#     scripts_dir = tmp_path / "scripts"
#     script_path = scripts_dir / "test" / "test"
#     new_script(scripts_dir, "test", None, "echo 'hello'")

#     with patch.dict("os.environ", {"EDITOR": "nano"}):
#         edit_script(scripts_dir, "test")

#     args = mock_run.call_args[0][0]
#     breakpoint()
#     assert args[0] == "nano"
#     assert str(script_path.resolve()) in args


def test_edit_script_not_found(tmp_path):
    """Test editing non-existent script."""
    scripts_dir = tmp_path / "scripts"

    with pytest.raises(ScriptNotFoundError):
        with patch(
            "taku.push_scripts"
        ):  # Mock push_scripts since we're testing error case
            edit_script(scripts_dir, "test")


@patch("subprocess.run")
def test_run_script(mock_run, tmp_path):
    """Test running a script."""
    scripts_dir = tmp_path / "scripts"

    # Use the actual new_script function to create the script
    new_script(scripts_dir, "test", None, "echo 'hello'")
    script_path = scripts_dir / "test" / "test"

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

    # Use the actual new_script function to create the script
    new_script(scripts_dir, "test", None, "echo 'hello'")

    with patch("pathlib.Path.home", return_value=tmp_path):
        install_scripts(scripts_dir, "test")

    installed_file = target_dir / "test"
    assert installed_file.exists()

    content = installed_file.read_text()
    assert "#!/usr/bin/env bash" in content
    assert "TAKU_SCRIPTS" in content
    assert "test" in content
    assert installed_file.stat().st_mode & 0o111  # Check executable

    # Check metadata file was created
    meta_file = scripts_dir / "test" / "meta.toml"
    assert meta_file.exists()

    captured = capsys.readouterr()
    assert "Installed" in captured.out and "test" in captured.out


def test_install_scripts_with_custom_name(tmp_path, capsys):
    """Test installing a script with custom install name."""
    scripts_dir = tmp_path / "scripts"
    target_dir = tmp_path / ".local" / "bin"

    # Use the actual new_script function to create the script
    new_script(scripts_dir, "test", None, "echo 'hello'")

    with patch("pathlib.Path.home", return_value=tmp_path):
        install_scripts(scripts_dir, "test", "my-custom-name")

    # Should install with custom name
    installed_file = target_dir / "my-custom-name"
    assert installed_file.exists()
    assert not (target_dir / "test").exists()

    # Check metadata was updated
    meta_file = scripts_dir / "test" / "meta.toml"
    assert meta_file.exists()
    import tomllib

    with open(meta_file, "rb") as f:
        metadata = tomllib.load(f)
    assert metadata["install_name"] == "my-custom-name"

    captured = capsys.readouterr()
    assert "Installed test to" in captured.out and "my-custom-name" in captured.out


def test_install_scripts_already_exists(tmp_path, capsys):
    """Test installing when file already exists."""
    scripts_dir = tmp_path / "scripts"
    target_dir = tmp_path / ".local" / "bin"
    target_dir.mkdir(parents=True)

    # Use the actual new_script function to create the script
    new_script(scripts_dir, "test", None, "echo 'hello'")

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

    # Use the actual new_script function to create multiple scripts
    new_script(scripts_dir, "script1", None, "echo 'script1'")
    new_script(scripts_dir, "script2", None, "echo 'script2'")

    # Create .templates (should be ignored)
    (scripts_dir / ".templates").mkdir(exist_ok=True)

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

    # Use the actual new_script function and install_scripts function
    new_script(scripts_dir, "test", None, "echo 'hello'")

    with patch("pathlib.Path.home", return_value=tmp_path):
        install_scripts(scripts_dir, "test")
        assert (target_dir / "test").exists()  # Verify it was installed

        uninstall_scripts(scripts_dir, "test")

    assert not (target_dir / "test").exists()

    captured = capsys.readouterr()
    assert "uninstall" in captured.out.lower() and "test" in captured.out


def test_uninstall_scripts_with_custom_name(tmp_path, capsys):
    """Test uninstalling script that was installed with custom name."""
    scripts_dir = tmp_path / "scripts"
    target_dir = tmp_path / ".local" / "bin"
    target_dir.mkdir(parents=True)

    # Use the actual new_script function and install with custom name
    new_script(scripts_dir, "test", None, "echo 'hello'")

    with patch("pathlib.Path.home", return_value=tmp_path):
        install_scripts(scripts_dir, "test", "my-custom-name")
        assert (target_dir / "my-custom-name").exists()  # Verify it was installed

        uninstall_scripts(scripts_dir, "test")

    assert not (target_dir / "my-custom-name").exists()

    # Check metadata was cleaned up
    meta_file = scripts_dir / "test" / "meta.toml"
    import tomllib

    with open(meta_file, "rb") as f:
        metadata = tomllib.load(f)
    assert "install_name" not in metadata

    captured = capsys.readouterr()
    assert "uninstall" in captured.out.lower() and "my-custom-name" in captured.out


def test_uninstall_scripts_not_found(tmp_path, capsys):
    """Test uninstalling non-existent script."""
    scripts_dir = tmp_path / "scripts"

    # Use the actual new_script function but don't install it
    new_script(scripts_dir, "test", None, "echo 'hello'")

    with patch("pathlib.Path.home", return_value=tmp_path):
        uninstall_scripts(scripts_dir, "test")

    captured = capsys.readouterr()
    assert "not found" in captured.out.lower()


def test_install_scripts_metadata_handling(tmp_path):
    """Test that metadata is properly handled during install/uninstall."""
    scripts_dir = tmp_path / "scripts"

    # Use the actual new_script function to create script
    new_script(scripts_dir, "test", None, "echo 'hello'")

    # Add existing metadata manually (since there's no function for this yet)
    meta_file = scripts_dir / "test" / "meta.toml"
    meta_file.write_text('description = "Test script"\nauthor = "Test User"')

    with patch("pathlib.Path.home", return_value=tmp_path):
        # Install with custom name
        install_scripts(scripts_dir, "test", "custom-name")

        # Check metadata was preserved and install_name added
        import tomllib

        with open(meta_file, "rb") as f:
            metadata = tomllib.load(f)
        assert metadata["description"] == "Test script"
        assert metadata["author"] == "Test User"
        assert metadata["install_name"] == "custom-name"

        # Uninstall
        uninstall_scripts(scripts_dir, "test")

        # Check install_name was removed but other metadata preserved
        with open(meta_file, "rb") as f:
            metadata = tomllib.load(f)
        assert metadata["description"] == "Test script"
        assert metadata["author"] == "Test User"
        assert "install_name" not in metadata
