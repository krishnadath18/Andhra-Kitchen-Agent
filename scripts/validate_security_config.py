"""
Pre-deployment validation for security-sensitive configuration.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.env import Config


def main() -> int:
    Config.validate_cors_config()
    if not Config.validate():
        return 1

    print("Security configuration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
