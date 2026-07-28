import time
from dataclasses import dataclass

import numpy as np
import polars as pl

FILE_NAME = "airports.csv"
EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class Route:
    path: tuple[int, ...]
    distance: float


def canonical_path(path: tuple[int, ...]) -> tuple[int, ...]:
    """Treat a route and its exact reverse as the same route."""
    reversed_path = path[::-1]
    return min(path, reversed_path)


def top_one_leg_routes(dist_matrix: np.ndarray, top_n: int) -> list[Route]:
    """Return the exact top-N unique airport pairs."""
    row_idx, col_idx = np.triu_indices(dist_matrix.shape[0], k=1)
    distances = dist_matrix[row_idx, col_idx]

    top_n = min(top_n, distances.size)
    candidate_idx = np.argpartition(distances, -top_n)[-top_n:]
    candidate_idx = candidate_idx[np.argsort(distances[candidate_idx])[::-1]]

    return [
        Route(
            path=(int(row_idx[i]), int(col_idx[i])),
            distance=float(distances[i]),
        )
        for i in candidate_idx
    ]


def top_multi_leg_routes(
    dist_matrix: np.ndarray,
    k_legs: int,
    top_n: int,
    *,
    beam_width: int | None = None,
    branch_factor: int = 12,
) -> list[Route]:
    """
    Approximate the top-N simple routes using beam search.

    Every airport is considered as a starting point. At each leg, each partial
    route expands to several of its farthest unvisited airports, after which
    only the strongest partial routes are retained.
    """
    n_airports = dist_matrix.shape[0]
    beam_width = beam_width or max(1500, top_n * 100)
    branch_factor = min(branch_factor, n_airports - 1)

    beam: list[Route] = [Route((start,), 0.0) for start in range(n_airports)]

    for _ in range(k_legs):
        expanded: list[Route] = []

        for route in beam:
            current = route.path[-1]
            scores = dist_matrix[current].copy()
            scores[list(route.path)] = -np.inf

            valid_count = n_airports - len(route.path)
            take = min(branch_factor, valid_count)
            if take <= 0:
                continue

            candidate_nodes = np.argpartition(scores, -take)[-take:]
            candidate_nodes = candidate_nodes[np.argsort(scores[candidate_nodes])[::-1]]

            for next_node in candidate_nodes:
                leg_distance = float(scores[next_node])
                if not np.isfinite(leg_distance):
                    continue
                expanded.append(
                    Route(
                        path=route.path + (int(next_node),),
                        distance=route.distance + leg_distance,
                    )
                )

        if not expanded:
            break

        expanded.sort(key=lambda route: route.distance, reverse=True)

        # Remove exact duplicates and reverse-equivalent duplicates.
        unique: dict[tuple[int, ...], Route] = {}
        for route in expanded:
            key = canonical_path(route.path)
            if key not in unique:
                unique[key] = route
            if len(unique) >= beam_width:
                break

        beam = list(unique.values())

    beam.sort(key=lambda route: route.distance, reverse=True)
    return beam[:top_n]


def calculate_distance_matrix(df: pl.DataFrame) -> np.ndarray:
    coords = df.select(["latitude_deg", "longitude_deg"]).to_numpy()
    lat = np.radians(coords[:, 0])
    lon = np.radians(coords[:, 1])

    dlat = lat[:, np.newaxis] - lat
    dlon = lon[:, np.newaxis] - lon

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat[:, np.newaxis]) * np.cos(lat) * np.sin(dlon / 2) ** 2
    )
    a = np.clip(a, 0.0, 1.0)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def read_positive_int(prompt: str, default: int) -> int:
    try:
        value = int(input(prompt))
        return value if value > 0 else default
    except ValueError:
        return default


def main() -> None:
    print("⚡ Loading airports data from OurAirport...")
    df = (
        pl.read_csv(FILE_NAME)
        .filter(pl.col("type").is_in(["large_airport"]))
        # .filter(pl.col("scheduled_service") == "yes")
    )
    print(f"✅ Loaded {len(df)} airports from {FILE_NAME}!")

    k_legs = read_positive_int(
        "Enter number of flight legs (e.g., 2 for a 3-airport route): ",
        default=2,
    )
    top_n = read_positive_int("How many top routes should be shown? ", default=10)

    if k_legs >= len(df):
        raise ValueError(
            f"A route with {k_legs} legs needs {k_legs + 1} distinct airports, "
            f"but only {len(df)} airports are loaded."
        )

    start_time = time.perf_counter()
    dist_matrix = calculate_distance_matrix(df)

    if k_legs == 1:
        routes = top_one_leg_routes(dist_matrix, top_n)
        method = "EXACT"
    else:
        routes = top_multi_leg_routes(dist_matrix, k_legs, top_n)
        method = "APPROXIMATE BEAM SEARCH"

    print(f"\n🏆 TOP {len(routes)} {k_legs}-LEG ROUTES ({method})")

    for rank, route in enumerate(routes, start=1):
        print(f"\n#{rank} — {route.distance:,.2f} km")
        for stop_number, airport_idx in enumerate(route.path, start=1):
            airport = df.row(airport_idx, named=True)
            print(f"  {stop_number}. {airport['name']} ({airport['ident']})")

    elapsed = time.perf_counter() - start_time
    print(f"\n⏱️ Calculated in: {elapsed:.4f} seconds")
    print("Variables:")
    print(f"  - Number of airports: {len(df)}")
    print(f"  - Number of legs: {k_legs}")
    print(f"  - Number of routes requested: {top_n}")
    print(f"  - Distance matrix shape: {dist_matrix.shape}")


if __name__ == "__main__":
    main()
