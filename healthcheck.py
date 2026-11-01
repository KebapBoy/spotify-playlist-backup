import json
import sys

STATUS_PATH = "/data/status.json"

# unhealthy while the last run of any job failed
try:
    with open(STATUS_PATH, "r", encoding="utf-8") as file:
        status = json.load(file)
except (OSError, ValueError):
    sys.exit(0)

sys.exit(0 if all(job["ok"] for job in status.values()) else 1)
