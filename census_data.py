import string

import faker

f = faker.Faker()
GROUPS = [f.bothify(text="?%%%", letters=string.ascii_uppercase) for _ in range(10)]
print("Categories:", ", ".join(GROUPS))
RANGE_PLACE = (10000, 20000)
RANGE_TOTAL_PLACES_PER_CITY = (1, 50)
RANGE_TOTAL_CITIES_PER_DIVISION = (1, 20)
RANGE_TOTAL_DIVISIONS = (50, 50)


def place_census_synatic():
    return {c: f.random_int(*RANGE_PLACE) for c in GROUPS}


def city_census_synatic():
    return {
        f.bothify(text="?%%%", letters=string.ascii_uppercase): place_census_synatic()
        for _ in range(f.random_int(*RANGE_TOTAL_PLACES_PER_CITY))
    }


def division_census_synatic():
    return {
        f.bothify(
            text="".join(f.random_elements("?%", length=5)),
            letters=string.ascii_uppercase,
        ): city_census_synatic()
        for _ in range(f.random_int(*RANGE_TOTAL_CITIES_PER_DIVISION))
    }


def census_synatic():
    return {
        f.bothify(
            text="".join(f.random_elements("?%", length=5))
        ): division_census_synatic()
        for _ in range(f.random_int(*RANGE_TOTAL_DIVISIONS))
    }


# schema
# {division: {city: {place: {group: count}}}}
print("Census schema: {division: {city: {place: {group: count}}}}")

with open("fake_census.json", "w") as fp:
    import json

    json.dump(census_synatic(), fp, indent=4)
