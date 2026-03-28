from __future__ import annotations

import os
import sys


def resolve_env_or_cli(
    cli_value: str | None,
    env_name: str,
    *,
    cli_flag: str | None = None,
    sensitive: bool = False,
) -> str | None:
    if cli_value is not None and cli_value.strip() != "":
        if sensitive:
            flag = cli_flag or env_name
            print(
                f"Warning: received {flag} via the command line. Prefer {env_name} in the environment so the value is not stored in shell history.",
                file=sys.stderr,
            )
        return cli_value
    return os.environ.get(env_name)
