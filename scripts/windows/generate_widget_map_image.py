from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _common import ensure_venv, get_python


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    rc = ensure_venv(repo_root)
    if rc != 0:
        return rc

    python_exe = get_python(repo_root)
    if not python_exe.exists():
        print(
            "ERROR: local interpreter not found at .venv\\Scripts\\python.exe.",
            file=sys.stderr,
        )
        print("Run: python scripts\\windows\\setup_env.py", file=sys.stderr)
        return 1

    default_output = repo_root / "docs" / "images" / "ui-04-widget-map.png"
    output_arg = str(default_output if len(sys.argv) < 2 else Path(sys.argv[1]))
    source_root_arg = str(repo_root if len(sys.argv) < 3 else Path(sys.argv[2]))
    cmd = [
        str(python_exe),
        "-m",
        "many_panelz_explorer.widget_map_snapshot",
        output_arg,
        source_root_arg,
    ]
    return subprocess.run(cmd, cwd=repo_root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
