from itertools import permutations
import math
import os
import sys
from typing import Sequence

import polars as pl
from tqdm import tqdm

# Expects the file in the local directory
FILE_NAME = "airports.csv"


def check_local_file():
    """Checks if the airports.csv file exists locally."""
    if not os.path.exists(FILE_NAME):
        print(f"❌ Error: '{FILE_NAME}' not found in the current directory.")
        print("\nTo run this script, please manually download the CSV:")
        print("🔗 https://davidmegginson.github.io/ourairports-data/airports.csv")
        print(f"Save it in this exact folder as '{FILE_NAME}' and try again.\n")
        sys.exit(1)


def load_airports_df(types: Sequence[str]) -> pl.DataFrame:
    """Reads the CSV directly into a clean Polars DataFrame."""
    print("⚡ Loading and processing CSV with Polars...")

    # Read only the essential columns to keep it efficient
    df = pl.read_csv(FILE_NAME)

    # Clean the code columns (convert to uppercase, handle nulls/missing values)
    # and drop any rows that are missing latitude or longitude
    df = df.with_columns(
        [
            pl.col("ident").str.to_uppercase().fill_null(""),
            pl.col("iata_code").str.to_uppercase().fill_null(""),
        ]
    ).filter(
        pl.col("latitude_deg").is_not_null() & pl.col("longitude_deg").is_not_null(),
        pl.col("type").is_in(types),
    )

    return df


def find_airport(df: pl.DataFrame, code: str):
    """Queries the Polars DataFrame directly to find an airport by ICAO or IATA code."""
    # Filter rows where either 'ident' or 'iata_code' matches our search code
    match = df.filter((pl.col("ident") == code) | (pl.col("iata_code") == code))

    if match.is_empty():
        return None

    # Return the first match as a dictionary
    return match.row(0, named=True)


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates the Great Circle distance in kilometers between two coordinates."""
    R = 6371.0  # Earth's radius in kilometers

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def compute_ncombs(n: int, r: int) -> int:
    """Computes the number of combinations (n choose r)."""
    if r > n or n < 0 or r < 0:
        return 0
    return math.comb(n, r)


def compute_nperms(n: int, r: int) -> int:
    """Computes the number of permutations (n P r)."""
    if r > n or n < 0 or r < 0:
        return 0
    return math.perm(n, r)


def compute_total_distance(*coords: tuple[float, float]) -> float:
    """Computes the total distance for a sequence of airport coordinates."""
    total_distance = 0.0
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        total_distance += haversine_distance(lat1, lon1, lat2, lon2)
    return total_distance


def main():
    N = 3
    # Ensure the file exists locally
    check_local_file()

    # Load DataFrame
    df = load_airports_df(types=["large_airport"])
    df = df.filter(pl.col("scheduled_service") == "yes")
    total = compute_nperms(df.height, N)
    print(total, "airport routes to compute distances for.")
    codes = df.select(["ident", "latitude_deg", "longitude_deg"]).to_dicts()
    longest_pairs_known = []
    for comb in tqdm(permutations(codes, N), total=total, desc="Computing distances"):
        codes = tuple(airport["ident"] for airport in comb)
        coords = [
            (airport["latitude_deg"], airport["longitude_deg"]) for airport in comb
        ]
        total_distance = compute_total_distance(*coords)
        current_winner = longest_pairs_known[-1] if longest_pairs_known else (0, None)
        if total_distance > current_winner[0]:
            longest_pairs_known.append((total_distance, codes))
            # print(
            #     f"🏆 New longest route found: {' -> '.join(codes)} with distance {total_distance:.2f} km"
            # )

if __name__ == "__main__":
    main()
