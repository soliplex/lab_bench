"""Write the room-volume fixture this experiment set measures against.

Deterministic: seed 1319, 60 rows, 17 of them in the 'Southeast' region.
The expected answer for the data task is a Southeast total of 40935.89.

Committed as a generator rather than as a CSV: it is smaller, it documents
itself, and there is no question about whether the data may be published.
"""

import argparse
import csv
import pathlib
import random

SEED = 1319
ROWS = 60
REGIONS = ("Northeast", "Southeast", "Midwest", "West")
PRODUCTS = ("widget", "gadget", "sprocket", "flange")
EXPECTED_SOUTHEAST_TOTAL = "40935.89"


class FixtureDrifted(Exception):
    """The generator no longer produces the total the experiment expects.

    Raised rather than warned about: every recorded result is scored
    against this number, so a silent change would invalidate comparisons
    with runs already in the archive.
    """

    def __init__(self, produced: str, expected: str):
        self.produced = produced
        self.expected = expected
        super().__init__(
            f"fixture produced {produced}, expected {expected}"
        )


def rows() -> list[dict[str, object]]:
    random.seed(SEED)
    out = []
    for index in range(ROWS):
        region = (
            REGIONS[index % 4]
            if index < 20
            else random.choice(REGIONS)
        )
        units = random.randint(1, 40)
        unit_price = round(random.uniform(4.5, 250.0), 2)
        out.append(
            {
                "order_id": f"SO-{1000 + index}",
                "region": region,
                "product": random.choice(PRODUCTS),
                "units": units,
                "unit_price": f"{unit_price:.2f}",
                "amount": f"{round(units * unit_price, 2):.2f}",
            }
        )
    return out


def write(destination: pathlib.Path) -> str:
    """Write 'orders.csv' under ``destination``; return the expected total."""
    destination.mkdir(parents=True, exist_ok=True)
    data = rows()
    with (destination / "orders.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    total = sum(
        float(row["amount"])
        for row in data
        if row["region"] == "Southeast"
    )
    return f"{total:.2f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=pathlib.Path)
    args = parser.parse_args()
    total = write(args.destination)
    print(f"wrote {args.destination / 'orders.csv'}")
    print(f"Southeast total: {total}")
    if total != EXPECTED_SOUTHEAST_TOTAL:
        raise FixtureDrifted(total, EXPECTED_SOUTHEAST_TOTAL)


if __name__ == "__main__":
    main()
