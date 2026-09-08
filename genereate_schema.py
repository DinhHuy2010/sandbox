import fileinput

import orjson as json
from tqdm import tqdm

all_keys = set()
likely_required = None

for line in tqdm(fileinput.input()):  # noqa: SIM115
    data = json.loads(line)
    if not isinstance(data, dict):
        raise ValueError("each line must contain a JSON object")  # noqa: TRY004

    keys = set(data)
    all_keys.update(keys)
    likely_required = keys if likely_required is None else likely_required & keys

likely_required = likely_required or set()
likely_optional = all_keys - likely_required

print("Likely required keys:", sorted(likely_required))
print("Optional keys:", sorted(likely_optional))
