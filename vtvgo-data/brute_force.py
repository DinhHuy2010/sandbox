import logging
from datetime import date

import vtvgo_epg
from brute_force_max_ids import ids as TEST

TODAY = date.today()
f = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(f)
logger.addHandler(sh)

fh = logging.FileHandler("brute_force.log")
fh.setLevel(logging.DEBUG)
fh.setFormatter(f)
logger.addHandler(fh)

MAXIUM_BATCH = 20


def audit(dt: date):
    logger.debug("Probing EPG for %s", dt.isoformat())

    output = {
        "date": dt.isoformat(),
        "batch_result": [],
    }

    for i in range(0, len(TEST), MAXIUM_BATCH):
        batch = TEST[i : i + MAXIUM_BATCH]

        # Let HTTP errors propagate rather than treating
        # rejected requests as dates without EPG.
        response = vtvgo_epg.get_channel_epg(batch, dt)

        has_epg = any(
            entry.get("programs")
            for entries in response.get("data", {}).values()
            for entry in entries
        )

        output["batch_result"].append(
            {
                "channels": batch,
                "count": len(batch),
                "has_epg": bool(has_epg),
            }
        )

    return output


def probe(dt: date):
    output = audit(dt)

    return any(batch["has_epg"] for batch in output["batch_result"])


def search_lower_bound_exponential(good_known: date):
    if not probe(good_known):
        raise ValueError("good_known must return data")

    last_good = good_known
    step = 1

    while True:
        ordinal = good_known.toordinal() - step

        if ordinal < date.min.toordinal():
            raise RuntimeError("No lower boundary found")

        candidate = date.fromordinal(ordinal)

        logger.info("--> Trying %s", candidate.isoformat())

        if not probe(candidate):
            return candidate, last_good

        last_good = candidate
        step *= 2


def bulkscan(start: date, end: date):
    logger.info("Bulk scanning from %s to %s", start.isoformat(), end.isoformat())
    for ordinal in range(start.toordinal(), end.toordinal() + 1):
        candidate = date.fromordinal(ordinal)
        output = audit(candidate)
        if any(batch["has_epg"] for batch in output["batch_result"]):
            logger.info("EPG exists on %s", candidate.isoformat())


cand_lower_bound, last_good_lower_bound = search_lower_bound_exponential(TODAY)
print(
    f"Lower bound: {cand_lower_bound.isoformat()} - {last_good_lower_bound.isoformat()}"
)
bulkscan(cand_lower_bound, last_good_lower_bound)
