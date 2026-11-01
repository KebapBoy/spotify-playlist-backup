import difflib
import json
import os
import re
import time
import traceback
import yaml
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from spotify_auth import has_token, spotify_client

TIMEZONE = ZoneInfo(os.environ.get("TZ", "Europe/Berlin"))
CONFIG_PATH = "/data/config.yml"
STATUS_PATH = "/data/status.json"

def wait_for_token():
    if has_token():
        return

    waited = 0

    while not has_token():
        if waited % 1800 == 0:
            print(
                "No Spotify token found. Authorize once from a terminal in this container:\n"
                "    docker exec -it <container> python /app/auth.py\n"
                "(in Dockhand: open the container's terminal and run: python /app/auth.py)\n"
                "Waiting for the token...",
                flush=True
            )

        time.sleep(10)
        waited += 10

    print("Spotify token found, continuing.", flush=True)

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise RuntimeError(f"Config not found: {CONFIG_PATH}. Copy config.example.yml into the data directory as config.yml.")

def get_all_user_playlists(sp):
    playlists = []
    result = sp.current_user_playlists(limit=50)

    while result:
        playlists.extend(result["items"])
        result = sp.next(result) if result["next"] else None

    return playlists

def is_owned(playlist, user_id):
    return playlist["owner"]["id"] == user_id

def find_playlist_by_name(playlists, name, user_id):
    matches = [playlist for playlist in playlists if playlist["name"] == name]

    if not matches:
        similar = difflib.get_close_matches(name, [playlist["name"] for playlist in playlists], n=5, cutoff=0.4)
        hint = f" Similar names: {similar}." if similar else ""

        raise RuntimeError(f"Source playlist not found: {name} ({len(playlists)} playlists in library).{hint}")

    # prefer own playlists; followed ones (e.g. Spotify-generated) are the fallback
    owned_matches = [playlist for playlist in matches if is_owned(playlist, user_id)]
    candidates = owned_matches or matches

    if len(candidates) > 1:
        raise RuntimeError(f"Multiple playlists with the same name found: {name}")

    return candidates[0]

def playlist_exists(playlists, name, user_id):
    return any(
        playlist["name"] == name and is_owned(playlist, user_id)
        for playlist in playlists
    )

def describe_track(track):
    artists = ", ".join(artist["name"] for artist in track.get("artists") or [] if artist.get("name"))
    name = track.get("name") or "Unknown title"

    return f"{artists} - {name}" if artists else name

def get_track_uris(sp, playlist_id):
    uris = []
    local_tracks = []
    result = sp.playlist_items(
        playlist_id,
        additional_types=("track",),
        fields="items(track(uri,type,name,artists(name))),next"
    )

    while result:
        for item in result["items"]:
            track = item.get("track")
            if track and track.get("uri") and track.get("type") == "track":
                # local files can't be added to playlists through the Web API
                if track["uri"].startswith("spotify:local:"):
                    local_tracks.append(describe_track(track))
                else:
                    uris.append(track["uri"])

        result = sp.next(result) if result["next"] else None

    return uris, local_tracks

def render_local_tracks_description(local_tracks):
    description = f"Skipped {len(local_tracks)} local file(s): " + "; ".join(local_tracks)

    # Spotify limits playlist descriptions to 300 characters
    if len(description) > 300:
        description = description[:299] + "…"

    return description

def render_name(template, source_name, track_count):
    now = datetime.now(TIMEZONE)

    def replace_date(match):
        date_format = match.group(1)
        return now.strftime(date_format)

    name = re.sub(r"\{date:([^}]+)\}", replace_date, template)

    return (
        name
        .replace("{source_name}", source_name)
        .replace("{track_count}", str(track_count))
    )

def record_status(source_name, ok, error=None):
    try:
        with open(STATUS_PATH, "r", encoding="utf-8") as file:
            status = json.load(file)
    except (OSError, ValueError):
        status = {}

    status[source_name] = {
        "ok": ok,
        "time": datetime.now(TIMEZONE).isoformat(timespec="seconds"),
        "error": error,
    }

    with open(STATUS_PATH, "w", encoding="utf-8") as file:
        json.dump(status, file, indent=2)

def run_archive(job_config):
    source_name = job_config["source_name"]

    try:
        archive_playlist(job_config)
    except Exception as error:
        record_status(source_name, False, str(error))
        raise

    record_status(source_name, True)

def archive_playlist(job_config):
    source_name = job_config["source_name"]
    target_template = job_config["target_name"]

    print(f"Start archiving playlist: {source_name}")

    sp = spotify_client()
    user_id = sp.current_user()["id"]

    playlists = get_all_user_playlists(sp)
    source_playlist = find_playlist_by_name(playlists, source_name, user_id)

    track_uris, local_tracks = get_track_uris(sp, source_playlist["id"])

    if not track_uris:
        raise RuntimeError(f"Source playlist doesn't contain any tracks: {source_name}")

    target_name = render_name(
        template=target_template,
        source_name=source_name,
        track_count=len(track_uris)
    )

    if playlist_exists(playlists, target_name, user_id):
        print(f"Archive playlist already exists: {target_name}")
        return

    archive_playlist_result = sp.user_playlist_create(
        user=user_id,
        name=target_name,
        public=False
    )

    for i in range(0, len(track_uris), 100):
        sp.playlist_add_items(
            archive_playlist_result["id"],
            track_uris[i:i + 100]
        )

    if local_tracks:
        print(f"Skipped {len(local_tracks)} local file(s) in {source_name}:")
        for local_track in local_tracks:
            print(f"  {local_track}")

        sp.playlist_change_details(
            archive_playlist_result["id"],
            description=render_local_tracks_description(local_tracks)
        )

    print(f"Archived playlist: {target_name}, Tracks: {len(track_uris)}")

def add_schedule(scheduler, playlist_config):
    schedule = playlist_config["schedule"]

    common_args = {
        "func": run_archive,
        "args": [playlist_config],
        "id": f"backup_{playlist_config['source_name']}",
        "replace_existing": True,
    }

    if schedule == "daily":
        scheduler.add_job(
            trigger="cron",
            hour=playlist_config.get("hour", 0),
            minute=playlist_config.get("minute", 0),
            **common_args
        )

    elif schedule == "weekly":
        scheduler.add_job(
            trigger="cron",
            day_of_week=playlist_config.get("day_of_week", "mon"),
            hour=playlist_config.get("hour", 0),
            minute=playlist_config.get("minute", 0),
            **common_args
        )

    elif schedule == "monthly":
        scheduler.add_job(
            trigger="cron",
            day=playlist_config.get("day", 1),
            hour=playlist_config.get("hour", 0),
            minute=playlist_config.get("minute", 0),
            **common_args
        )

    else:
        raise RuntimeError(f"Unknown schedule interval: {schedule}")

def main():
    config = load_config()

    scheduler = BlockingScheduler(timezone=str(TIMEZONE))

    for playlist_config in config.get("playlists", []):
        add_schedule(scheduler, playlist_config)

    print("Running Spotify Playlist Archiver.")

    wait_for_token()

    if os.environ.get("RUN_ON_STARTUP", "false").lower() == "true":
        for playlist_config in config.get("playlists", []):
            try:
                run_archive(playlist_config)
            except Exception:
                print(f"Startup archive failed: {playlist_config.get('source_name')}", flush=True)
                traceback.print_exc()

    scheduler.start()

if __name__ == "__main__":
    main()
