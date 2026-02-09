#!/usr/bin/env python3
"""Version management script"""

import sys
from pathlib import Path


def get_version():
    """Get current version from VERSION file"""
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "1.0.0"


def increment_version(version: str) -> str:
    """Increment patch version"""
    parts = version.split(".")
    if len(parts) >= 3:
        parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


def main():
    version_file = Path(__file__).parent.parent / "VERSION"
    current = get_version()

    if "--deploy" in sys.argv:
        new_version = increment_version(current)
        version_file.write_text(new_version)
        print(f"Version: {current} -> {new_version}")
    else:
        print(current)


if __name__ == "__main__":
    main()
