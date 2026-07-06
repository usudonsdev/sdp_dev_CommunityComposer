# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# When this module is started from a different working directory (e.g. via docker
# compose), `from app import ...` could resolve to the repo-root `app` package.
# Force Python to prefer this directory's `app` package (C1 UI).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
