#!/usr/bin/env python3
"""Version management script

Version format: X.Y.YYYY
- X: Major version (1 = pre-production, 2+ = production)
- Y: Minor version (incremented on each deploy)
- YYYY: Year
"""

import sys
from datetime import datetime
from pathlib import Path


def get_version():
    """Get current version from VERSION file"""
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "1.0.2026"


def increment_version(version: str) -> str:
    """Increment minor version, keep year updated"""
    parts = version.split(".")
    if len(parts) >= 3:
        major = parts[0]
        minor = int(parts[1]) + 1
        year = datetime.now().year
        return f"{major}.{minor}.{year}"
    return version


def main():
    version_file = Path(__file__).parent.parent / "VERSION"
    current = get_version()

    if "--deploy" in sys.argv:
        new_version = increment_version(current)
        version_file.write_text(new_version + "\n")
        print(new_version)
    else:
        print(current)


if __name__ == "__main__":
    main()
