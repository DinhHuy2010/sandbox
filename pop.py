from random import uniform

# import faker

# f = faker.Faker()


def p(number: float, percentage: float, exponent: float) -> float:
    return number * (1 + percentage / 100) ** exponent


value = 1000
YEARS = 100
RANGE = (-2, 10)
AVG_PERCENT_RAGE = sum(RANGE) / len(RANGE)
MINIMUM_POPULATION = p(value, RANGE[0], YEARS)
MAXIUM_POPULATION = p(value, RANGE[1], YEARS)
AVG_POPULATION = p(value, AVG_PERCENT_RAGE, YEARS)
AVG_POP2 = (MINIMUM_POPULATION + MAXIUM_POPULATION) / 2
print(
    f"initial population: {value} people, range of change: {RANGE[0]}% to {RANGE[1]}%"
)
print("--- predicted population ---")
print(f"minimum population: {MINIMUM_POPULATION:.0f} people")
print(f"maximum population: {MAXIUM_POPULATION:.0f} people")
print(
    f"average population: {AVG_POPULATION:.0f} people (by average percentage of {AVG_PERCENT_RAGE:.0f}%)"
)
print(f"average population: {AVG_POP2:.0f} people (by (min+max)/2)")
for i in range(YEARS):
    selected_pct = uniform(*RANGE)
    value = round(p(value, selected_pct, 1))
    print(f"population at year {i + 1}: {value} people ({selected_pct:.0f}%)")
