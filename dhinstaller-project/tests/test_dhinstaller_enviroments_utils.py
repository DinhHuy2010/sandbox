from pathlib import Path

from dhinstaller.environments.utils import parse_venv_info


def test_dhinstaller_environments_utils_parse_venv_info(tmp_path: Path):
    # Create a mock pyvenv.cfg file
    venv_dir = tmp_path / "myenv"
    venv_dir.mkdir()
    cfg_file = venv_dir / "pyvenv.cfg"
    cfg_file.write_text(
        """
        home = /usr/bin/python3
        include-system-site-packages = false
        version_info = 3.8.10
        prompt = myenv
        """.strip()
    )

    # Import the function to test

    # Call the function and check the output
    metadata = parse_venv_info(venv_dir)

    assert metadata["home"] == "/usr/bin/python3"
    assert metadata["include-system-site-packages"] == "false"
    assert metadata["version_info"] == "3.8.10"
    assert metadata["prompt"] == "myenv"
