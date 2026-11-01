import os
import re
import yaml
from datetime import datetime
from zoneinfo import ZoneInfo

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from apscheduler.schedulers.blocking import BlockingScheduler

TIMEZONE = ZoneInfo(os.environ.get("TZ", "Europe/Berlin"))

def authenticate_only():
    print("Starting Spotify authorization flow...", flush=True)

    sp = spotify_client()
    user = sp.current_user()

    print(f"Authenticated as: {user['display_name']} ({user['id']})", flush=True)

def spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope=(
            "playlist-read-private "
            "playlist-read-collaborative "
            "playlist-modify-private "
            "playlist-modify-public"
        ),
        cache_path="/data/.spotify-token",
        open_browser=False
    ))

def load_config():
    with open("/app/config.yml", "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def get_all_user_playlists(sp):
    playlists = []
    result = sp.current_user_playlists(limit=50)

    while result:
        playlists.extend(result["items"])
        result = sp.next(result) if result["next"] else None

    return playlists

def find_playlist_by_name(playlists, name):
    matches = [playlist for playlist in playlists if playlist["name"] == name]

    if not matches:
        raise RuntimeError(f"Source playlist not found: {name}")

    if len(matches) > 1:
        raise RuntimeError(f"Multiple playlists with the same name found: {name}")

    return matches[0]

def playlist_exists(playlists, name):
    return any(playlist["name"] == name for playlist in playlists)

def get_track_uris(sp, playlist_id):
    uris = []
    result = sp.playlist_items(
        playlist_id,
        additional_types=("track",),
        fields="items(track(uri,type)),next"
    )

    while result:
        for item in result["items"]:
            track = item.get("track")
            if track and track.get("uri") and track.get("type") == "track":
                uris.append(track["uri"])

        result = sp.next(result) if result["next"] else None

    return uris

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

def archive_playlist(job_config):
    source_name = job_config["source_name"]
    target_template = job_config["target_name"]

    print(f"Start archiving playlist: {source_name}")

    sp = spotify_client()
    user_id = sp.current_user()["id"]

    playlists = get_all_user_playlists(sp)
    source_playlist = find_playlist_by_name(playlists, source_name)

    track_uris = get_track_uris(sp, source_playlist["id"])

    if not track_uris:
        raise RuntimeError(f"Source playlist doesn't contain any tracks: {source_name}")

    target_name = render_name(
        template=target_template,
        source_name=source_name,
        track_count=len(track_uris)
    )

    if playlist_exists(playlists, target_name):
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

    print(f"Archived playlist: {target_name}, Tracks: {len(track_uris)}")

def add_schedule(scheduler, playlist_config):
    schedule = playlist_config["schedule"]

    common_args = {
        "func": archive_playlist,
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

    if os.environ.get("RUN_ON_STARTUP", "false").lower() == "true":
        for playlist_config in config.get("playlists", []):
            archive_playlist(playlist_config)

    scheduler.start()

if __name__ == "__main__":
    if os.environ.get("SPOTIFY_AUTH_ONLY") == "true":
        authenticate_only()
        exit(0)

    main()
