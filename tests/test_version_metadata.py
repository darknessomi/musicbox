import re
from pathlib import Path

from NEMbox import __version__

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.5.3"


def test_release_version_sources_are_synchronized():
    pyproject = (ROOT / "pyproject.toml").read_text()
    lockfile = (ROOT / "uv.lock").read_text()
    package_init = (ROOT / "NEMbox" / "__init__.py").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()
    issue_template = (
        ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"
    ).read_text()

    project_version = re.search(
        r'\[project\].*?^version = "([^"]+)"', pyproject, re.MULTILINE | re.DOTALL
    )
    locked_version = re.search(
        r'\[\[package\]\]\s+name = "netease-musicbox"\s+version = "([^"]+)"',
        lockfile,
    )

    assert project_version and project_version.group(1) == EXPECTED_VERSION
    assert locked_version and locked_version.group(1) == EXPECTED_VERSION
    assert f'else "{EXPECTED_VERSION}"' in package_init
    assert changelog.startswith(f"# 更新日志\n\n2026-08-27 版本 {EXPECTED_VERSION} ")
    assert f'placeholder: "{EXPECTED_VERSION}"' in issue_template
    assert __version__ == EXPECTED_VERSION
