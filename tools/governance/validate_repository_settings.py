#!/usr/bin/env python3
"""Require repository merge settings that preserve validated commit identities."""

import json
import sys
from typing import Dict, List


REQUIRED_SETTINGS = {
    "allow_merge_commit": True,
    "allow_squash_merge": False,
    "allow_rebase_merge": False,
}


def validate_settings(settings: Dict[str, object]) -> List[str]:
    errors: List[str] = []
    for name, expected in REQUIRED_SETTINGS.items():
        actual = settings.get(name)
        if actual is not expected:
            errors.append("{} must be {}, got {}".format(name, expected, actual))
    return errors


def main() -> int:
    try:
        settings = json.load(sys.stdin)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("repository settings validation could not run: {}".format(error), file=sys.stderr)
        return 2

    if not isinstance(settings, dict):
        print("repository settings response must be a JSON object", file=sys.stderr)
        return 2

    errors = validate_settings(settings)
    if errors:
        print("repository merge settings validation failed:", file=sys.stderr)
        for error in errors:
            print("- {}".format(error), file=sys.stderr)
        return 1

    print("repository merge settings preserve validated commit identities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
