import time
from dataclasses import dataclass

import numpy as np
import polars as pl

FILE_NAME = "airports.csv"
EARTH_RADIUS_KM = 6371.0088
DEFAULT_DIVERSITY_KM = 300.0


@dataclass(frozen=True)
class Route:
    path: tuple[int, ...]
    distance: float


def canonical_path(path: tuple[int, ...]) -> tuple[int, ...]:
    """Treat a route and its exact reverse as the same route."""
    reversed_path = path[::-1]
    return min(path, reversed_path)


def route_separation_km(
    first: Route,
    second: Route,
    dist_matrix: np.ndarray,
) -> float:
    """
    Measure how different two same-length routes are geographically.

    Routes may be read in either direction. For each alignment, calculate the
    largest distance between corresponding stops. The smaller alignment score
    is returned. Thus, a score below 300 km means every corresponding stop is
    within 300 km of the other route.
    """
    forward = max(
        float(dist_matrix[a, b]) for a, b in zip(first.path, second.path)
    )
    reverse = max(
        float(dist_matrix[a, b])
        for a, b in zip(first.path, reversed(second.path))
    )
    return min(forward, reverse)


def select_diverse_routes(
    candidates: list[Route],
    top_n: int,
    dist_matrix: np.ndarray,
    min_separation_km: float,
) -> list[Route]:
    """Greedily keep the highest-ranked routes that are geographically distinct."""
    if min_separation_km <= 0:
        return candidates[:top_n]

    selected: list[Route] = []
    for candidate in candidates:
        if all(
            route_separation_km(candidate, existing, dist_matrix)
            >= min_separation_km
            for existing in selected
        ):
            selected.append(candidate)
            if len(selected) >= top_n:
                break
    return selected


def top_one_leg_routes(
    dist_matrix: np.ndarray,
    top_n: int,
    min_separation_km: float,
) -> list[Route]:
    """
    Return exact-distance airport pairs with an optional diversity filter.

    Candidate-pool growth is adaptive. Once enough diverse routes are found
    inside the globally highest M pairs, lower-ranked pairs cannot displace
    them, so the greedy diversity ranking is exact.
    """
    row_idx, col_idx = np.triu_indices(dist_matrix.shape[0], k=1)
    distances = dist_matrix[row_idx, col_idx]
    total_pairs = distances.size

    pool_size = min(total_pairs, max(10_000, top_n * 1_000))

    while True:
        candidate_idx = np.argpartition(distances, -pool_size)[-pool_size:]
        candidate_idx = candidate_idx[np.argsort(distances[candidate_idx])[::-1]]

        candidates = [
            Route(
                path=(int(row_idx[i]), int(col_idx[i])),
                distance=float(distances[i]),
            )
            for i in candidate_idx
        ]
        selected = select_diverse_routes(
            candidates,
            top_n,
            dist_matrix,
            min_separation_km,
        )

        if len(selected) >= top_n or pool_size == total_pairs:
            return selected

        pool_size = min(total_pairs, pool_size * 2)


def top_multi_leg_candidates(
    dist_matrix: np.ndarray,
    k_legs: int,
    candidate_count: int,
    *,
    beam_width: int | None = None,
    branch_factor: int = 12,
) -> list[Route]:
    """Generate strong multi-leg route candidates using beam search."""
    n_airports = dist_matrix.shape[0]
    beam_width = beam_width or max(3_000, candidate_count * 5)
    branch_factor = min(branch_factor, n_airports - 1)

    beam: list[Route] = [Route((start,), 0.0) for start in range(n_airports)]

    for _ in range(k_legs):
        expanded: list[Route] = []

        for route in beam:
            current = route.path[-1]
            scores = dist_matrix[current].copy()
            scores[list(route.path)] = -np.inf

            take = min(branch_factor, n_airports - len(route.path))
            if take <= 0:
                continue

            candidate_nodes = np.argpartition(scores, -take)[-take:]
            candidate_nodes = candidate_nodes[
                np.argsort(scores[candidate_nodes])[::-1]
            ]

            for next_node in candidate_nodes:
                leg_distance = float(scores[next_node])
                if np.isfinite(leg_distance):
                    expanded.append(
                        Route(
                            path=route.path + (int(next_node),),
                            distance=route.distance + leg_distance,
                        )
                    )

        if not expanded:
            break

        expanded.sort(key=lambda route: route.distance, reverse=True)

        unique: dict[tuple[int, ...], Route] = {}
        for route in expanded:
            key = canonical_path(route.path)
            if key not in unique:
                unique[key] = route
            if len(unique) >= beam_width:
                break

        beam = list(unique.values())

    beam.sort(key=lambda route: route.distance, reverse=True)
    return beam[:candidate_count]


def top_multi_leg_routes(
    dist_matrix: np.ndarray,
    k_legs: int,
    top_n: int,
    min_separation_km: float,
) -> list[Route]:
    """Return diverse multi-leg routes from a larger beam-search candidate pool."""
    candidate_count = max(2_000, top_n * 300)
    candidates = top_multi_leg_candidates(
        dist_matrix,
        k_legs,
        candidate_count,
        beam_width=max(10_000, candidate_count * 3),
    )
    return select_diverse_routes(
        candidates,
        top_n,
        dist_matrix,
        min_separation_km,
    )


def calculate_distance_matrix(df: pl.DataFrame) -> np.ndarray:
    coords = df.select(["latitude_deg", "longitude_deg"]).to_numpy()
    lat = np.radians(coords[:, 0])
    lon = np.radians(coords[:, 1])

    dlat = lat[:, np.newaxis] - lat
    dlon = lon[:, np.newaxis] - lon

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat[:, np.newaxis])
        * np.cos(lat)
        * np.sin(dlon / 2) ** 2
    )
    a = np.clip(a, 0.0, 1.0)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def read_positive_int(prompt: str, default: int) -> int:
    try:
        value = int(input(prompt))
        return value if value > 0 else default
    except ValueError:
        return default


def read_nonnegative_float(prompt: str, default: float) -> float:
    try:
        value = float(input(prompt))
        return value if value >= 0 else default
    except ValueError:
        return default


def main() -> None:
    print("⚡ Loading airports data from OurAirport...")
    df = pl.read_csv(FILE_NAME).filter(pl.col("type") == "large_airport")
    print(f"✅ Loaded {len(df)} airports from {FILE_NAME}!")

    k_legs = read_positive_int(
        "Enter number of flight legs (e.g., 2 for a 3-airport route): ",
        default=2,
    )
    top_n = read_positive_int("How many top routes should be shown? ", default=10)
    min_separation_km = read_nonnegative_float(
        "Minimum separation between similar routes in km [300, 0 disables]: ",
        default=DEFAULT_DIVERSITY_KM,
    )

    if k_legs >= len(df):
        raise ValueError(
            f"A route with {k_legs} legs needs {k_legs + 1} distinct airports, "
            f"but only {len(df)} airports are loaded."
        )

    start_time = time.perf_counter()
    dist_matrix = calculate_distance_matrix(df)

    if k_legs == 1:
        routes = top_one_leg_routes(dist_matrix, top_n, min_separation_km)
        method = "EXACT + DIVERSITY FILTER"
    else:
        routes = top_multi_leg_routes(
            dist_matrix,
            k_legs,
            top_n,
            min_separation_km,
        )
        method = "APPROXIMATE BEAM SEARCH + DIVERSITY FILTER"

    print(f"\n🏆 TOP {len(routes)} {k_legs}-LEG ROUTES ({method})")
    print(f"🌍 Minimum route separation: {min_separation_km:,.0f} km")

    for rank, route in enumerate(routes, start=1):
        print(f"\n#{rank} — {route.distance:,.2f} km")
        for stop_number, airport_idx in enumerate(route.path, start=1):
            airport = df.row(airport_idx, named=True)
            print(f"  {stop_number}. {airport['name']}, {airport['municipality']}, {airport['iso_country']} ({airport['ident']}{'/' + airport['iata_code'] if airport['iata_code'] else ''})")

    elapsed = time.perf_counter() - start_time
    print(f"\n⏱️ Calculated in: {elapsed:.4f} seconds")
    print("Variables:")
    print(f"  - Number of airports: {len(df)}")
    print(f"  - Number of legs: {k_legs}")
    print(f"  - Number of routes requested: {top_n}")
    print(f"  - Minimum route separation: {min_separation_km:,.0f} km")
    print(f"  - Distance matrix shape: {dist_matrix.shape}")


if __name__ == "__main__":
    main()
