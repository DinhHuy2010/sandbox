# import time
import time

import numpy as np
import polars as pl

FILE_NAME = "airports.csv"


def solve_longest_path(dist_matrix, k_legs, num_restarts=500):
    """Finds the longest path of k_legs using a greedy heuristic."""
    N = dist_matrix.shape[0]
    best_path = None
    max_total_dist = 0.0

    # Test multiple starting points to find a robust global maximum
    start_nodes = np.random.choice(N, size=min(num_restarts, N), replace=False)

    for start in start_nodes:
        path = [start]
        total_dist = 0.0
        visited = {start}

        for _ in range(k_legs):
            curr = path[-1]
            possible_dists = dist_matrix[curr].copy()
            possible_dists[list(visited)] = -1  # Mask visited

            next_node = np.argmax(possible_dists)
            if possible_dists[next_node] < 0:
                break

            total_dist += possible_dists[next_node]
            path.append(next_node)
            visited.add(next_node)

        if total_dist > max_total_dist:
            max_total_dist = total_dist
            best_path = path

    return best_path, max_total_dist


# 1. Load Data
print("⚡ Loading airports data from OurAirport...")
df = pl.read_csv(FILE_NAME)
df = df.filter(pl.col("type") == "large_airport")
print(f"✅ Loaded {len(df)} airports from {FILE_NAME}!")

# 2. Get User Input
try:
    k_input = int(
        input("Enter number of flight legs (e.g., 2 for a 3-airport route): ")
    )
except ValueError:
    k_input = 2

start_time = time.time()

# 3. Calculate Distance Matrix
coords = df.select(["latitude_deg", "longitude_deg"]).to_numpy()
lat, lon = np.radians(coords[:, 0]), np.radians(coords[:, 1])
dlat = lat[:, np.newaxis] - lat
dlon = lon[:, np.newaxis] - lon
a = (
    np.sin(dlat / 2) ** 2
    + np.cos(lat[:, np.newaxis]) * np.cos(lat) * np.sin(dlon / 2) ** 2
)
dist_matrix = 2 * 6371.0088 * np.arcsin(np.sqrt(a))

# 4. Solve
# num_restart = dist_matrix.shape[0]
num_restart = 500  # Limit the number of restarts for performance
path, total_dist = solve_longest_path(dist_matrix, k_input, num_restarts=num_restart)

# 5. Output time
print(f"\n🏆 LONGEST {k_input}-LEG ROUTE FOUND")
for i, idx in enumerate(path):
    ap = df.row(idx, named=True)
    print(f"{i + 1}. {ap['name']} ({ap['ident']})")
print(f"🔥 Total Distance: {total_dist:,.2f} km")
print(f"⏱️ Calculated in: {time.time() - start_time:.4f} seconds!")

print("Variables:")
print(f"  - Number of airports: {len(df)}")
print(f"  - Number of legs: {k_input}")
print(f"  - Distance matrix shape: {num_restart}")
