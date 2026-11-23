import datetime
import json
import subprocess
from time import sleep

with subprocess.Popen(["journalctl", "-b", "-o", "json"], stdout=subprocess.PIPE) as p:
    previous_ts = -1
    for line in p.stdout:
        data = json.loads(line)
        if data.get("SYSLOG_IDENTIFIER") == "cloudflared":
            continue
        realtime_timestamp = int(data["__REALTIME_TIMESTAMP"])
        if previous_ts != -1:
            sleep(max(0, (realtime_timestamp - previous_ts) / 1_000_000))
        realtime_ts_sec = realtime_timestamp // 1_000_000
        realtime_dt = datetime.datetime.fromtimestamp(realtime_ts_sec)
        print(
            f"{realtime_dt.strftime('%b %d %H:%M:%S')} {data['_HOSTNAME']} {data.get('SYSLOG_IDENTIFIER', 'unknown')}: {data['MESSAGE']}"
        )
        previous_ts = realtime_timestamp
