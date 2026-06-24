#!/usr/bin/env python
"""Entry point. Same as `python -m pitchgrill.cli`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pitchgrill.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
