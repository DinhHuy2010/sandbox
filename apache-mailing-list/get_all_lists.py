import niquests

APACHE_LISTS_BASE_URL = "https://lists.apache.org"

session = niquests.Session()
resp = session.get(f"{APACHE_LISTS_BASE_URL}/api/preferences.lua")
data = resp.raise_for_status().json()
lists = data["lists"]
out = {}
for name, ls in lists.items():
    the_lists = [f"{n}@{name}" for n in ls]
    out[name] = the_lists
with open("lists.json", "w") as f:
    import json

    json.dump(out, f, indent=2)
