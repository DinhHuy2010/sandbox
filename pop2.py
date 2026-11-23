from random import uniform
from statistics import mean, median

INITIAL = 8 * 10**9
YEARS = 100
RANGE = (-2, 10)
SIMULATIONS = 10_000

results = []

for _ in range(SIMULATIONS):
    population = INITIAL

    for year in range(YEARS):
        rate = uniform(*RANGE)
        population = round(population * (1 + rate / 100))

    results.append(population)

results.sort()

print("--- variables ---")
print(f"Initial population: {INITIAL:,}")
print(f"Years: {YEARS:,}")
print(f"Range: {RANGE[0]}% to {RANGE[1]}%")
print(f"Simulations: {SIMULATIONS:,}")
print("--- results ---")

print(f"Minimum: {min(results):,}")
print(f"Maximum: {max(results):,}")
print(f"Mean: {mean(results):,.0f}")
print(f"Median: {median(results):,.0f}")
print(f"5th percentile: {results[500]:,}")
print(f"95th percentile: {results[9500]:,}")
