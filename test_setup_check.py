import os
import plistlib
import shutil
import subprocess

import pytest

REPO = os.path.dirname(os.path.abspath(__file__))


def _scripts():
    scripts = []
    for sub in ("", "homebrew.sh-master"):
        directory = os.path.join(REPO, sub)
        for name in sorted(os.listdir(directory)):
            if name.endswith(".sh"):
                scripts.append(os.path.join(directory, name))
    return scripts


def _shell(path):
    with open(path, "rb") as fh:
        first = fh.readline().decode("utf-8", "replace").rstrip("\n")
    first = first.lstrip("\ufeff")
    if first.startswith("#!"):
        first = first[2:]
    return os.path.basename(first.split(" ", 1)[0])


@pytest.mark.parametrize("path", _scripts(), ids=lambda p: os.path.relpath(p, REPO))
def test_script_parses_with_its_own_shell(path):
    shell = _shell(path)
    if shutil.which(shell) is None:
        pytest.skip(f"{shell} not installed")
    result = subprocess.run([shell, "-n", path], capture_output=True, text=True)
    assert result.returncode == 0, (
        f"{shell} -n failed for {os.path.relpath(path, REPO)}:\n{result.stderr}"
    )


def test_launchdaemon_is_a_valid_plist():
    path = os.path.join(REPO, "com.company.reconafterupdate")
    with open(path, "rb") as fh:
        data = plistlib.load(fh)
    assert data["Label"] == "com.company.reconafterupdate"


def test_setup_check_fenced_block_extracts_and_is_valid_bash():
    setup = os.path.join(REPO, "docs", "SETUP.md")
    with open(setup) as fh:
        lines = fh.readlines()

    block = []
    in_block = False
    for line in lines:
        if line.startswith("```") and "setup-check" in line:
            in_block = True
            continue
        if line.startswith("```") and in_block:
            in_block = False
        elif in_block:
            block.append(line)

    assert block, "no setup-check fenced block found in docs/SETUP.md"

    script = "".join(block)
    assert "apt-get install -y -qq zsh ||" in script

    result = subprocess.run(
        ["bash", "-n", "-c", script], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
