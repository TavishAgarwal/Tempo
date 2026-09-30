"""`make data` step: fetch CVRPLIB benchmark files (data/ is gitignored)."""

from __future__ import annotations

import logging

from taqpso.bench import cvrplib

NAMES = ["A-n32-k5", "B-n31-k5", "P-n16-k8", "F-n72-k4", "X-n101-k25"]


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    for n in NAMES:
        cvrplib.fetch(n)


if __name__ == "__main__":
    main()
