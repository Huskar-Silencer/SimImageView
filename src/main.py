from __future__ import annotations

import sys
from pathlib import Path

from app import ImageViewMainWindow, create_app


def main() -> int:
    app = create_app()
    window = ImageViewMainWindow()

    if len(sys.argv) > 1:
        window.load_from_path(Path(sys.argv[1]).expanduser().resolve())

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())