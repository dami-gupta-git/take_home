import json
from pathlib import Path
from typing import Iterator


def load_example_routes():
    data_path = Path(__file__).parent / "data" / "example_routes.json"
    with open(data_path, "r") as f:
        return json.load(f)


def get_routes(smiles: str, batch_size: int = 1) -> Iterator[tuple[list, bool]]:
    # In a real service, we would use the SMILES to compute the routes.
    # Here, we just load a set of example routes.
    all_routes = load_example_routes()
    total_routes = len(all_routes)
    for i in range(0, total_routes, batch_size):
        batch = all_routes[i : i + batch_size]
        is_last = (i + batch_size) >= total_routes
        yield batch, is_last
