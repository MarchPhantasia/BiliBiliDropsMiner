from __future__ import annotations

import sys


def main() -> int:
    from bilibili_drops_miner.native_messaging import (
        is_native_messaging_invocation,
        run_native_messaging_host,
    )

    if is_native_messaging_invocation(sys.argv):
        return run_native_messaging_host()

    from bilibili_drops_miner.gui import run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
