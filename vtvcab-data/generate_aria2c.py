from datetime import date

MAX_DATE = date.fromisoformat("2026-11-01")
MIN_DATE = date.fromisoformat("2022-12-31")
BASE_URI = "https://apigateway.vtvcab.vn/mycab/api/v2/landing-page/broadcast_list"


def generate_uri(date):
    return f"{BASE_URI}?date={date}"


def generate_aria2c_input_instr(date):
    uri = generate_uri(date)
    output = []
    output.append(f"# For {date}")
    output.append(f"{uri}")
    output.append("  dir=out/raw/")
    output.append(f"  out={date}.json")
    return "\n".join(output)


print("# Generated aria2c input instructions for all dates in the supported range")
print("# Base URI:", BASE_URI + "?date=$DATE")
for d in range(MIN_DATE.toordinal(), MAX_DATE.toordinal() + 1):
    print(generate_aria2c_input_instr(date.fromordinal(d)))
