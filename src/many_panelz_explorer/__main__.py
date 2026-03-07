from __future__ import annotations

import sys

from .app_controller import AppController


def main() -> int:
    controller = AppController(argv=sys.argv)
    return controller.run()


if __name__ == "__main__":
    raise SystemExit(main())
