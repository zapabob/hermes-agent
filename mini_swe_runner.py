"""Compatibility import for the standalone Mini-SWE runner.

The implementation lives under ``scripts/standalone``.  Keep the historical
root import working for callers and downstream tests while the script remains
usable from its documented location.
"""

from scripts.standalone.mini_swe_runner import MiniSWERunner, main

__all__ = ["MiniSWERunner", "main"]


if __name__ == "__main__":
    main()
