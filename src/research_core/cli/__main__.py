"""Allow running the CLI as a module: python -m research_core.cli"""

from __future__ import annotations

import sys

from research_core.cli.app import main

sys.exit(main())
