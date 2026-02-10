#!/usr/bin/env python3
"""Version management script

Version format: X.Y.YYYY
- X: Major version (1 = pre-production, 2+ = production)
- Y: Minor version (feature increments)
- YYYY: Year
"""

from pathlib import Path


def get_version():
    """Get current version from VERSION file"""
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "1.0.2026"


def main():
    """Print current version (no auto-increment for year-based versioning)"""
    print(get_version())


if __name__ == "__main__":
    main()
