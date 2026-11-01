# Spotify Playlist Backup

A small containerized service that archives Spotify playlists on a schedule. Playlists like "Mein Mix der Woche" or "Release Radar" change constantly; this keeps dated snapshot copies as private playlists in your own account.

## How it works

1. `/data/config.yml` (created from [config.example.yml](config.example.yml)) lists the playlists to archive, each with a schedule (`daily`, `weekly`, `monthly`) and a target name template.
2. For each entry, an APScheduler cron job:
   - looks up the source playlist by exact name (fails if missing or ambiguous),
   - collects all track URIs (podcast episodes are skipped),
   - renders the target name from the template,
   - skips the run if a playlist with that name already exists,
   - otherwise creates a new **private** playlist and adds the tracks in batches of 100.
3. With `RUN_ON_STARTUP=true`, every configured playlist is archived once on container start before the scheduler begins.

## Configuration

### `config.yml`

Start from [config.example.yml](config.example.yml), which also documents every option. The file has to be named `config.yml` and live in the data directory, which is mounted to `/data` in the container. It is not part of the image or the repository.

```yaml
playlists:
  - source_name: "Mein Mix der Woche"
    schedule: weekly
    day_of_week: mon
    hour: 6
    minute: 0
    target_name: "{date:%d.%m.%y} - {source_name}"
```

| Field | Applies to | Default | Notes |
|---|---|---|---|
| `source_name` | all | required | Exact playlist name, must be unique |
| `schedule` | all | required | `daily`, `weekly` or `monthly` |
| `day_of_week` | weekly | `mon` | `mon`..`sun` |
| `day` | monthly | `1` | Day of month |
| `hour`, `minute` | all | `0`, `0` | |
| `target_name` | all | required | Template, see below |

Template placeholders: `{source_name}`, `{track_count}`, `{date:<strftime>}` (e.g. `{date:%Y-%m-%d}`).

### Environment variables

See [.env.example](.env.example).

| Variable | Description |
|---|---|
| `TZ` | Timezone for schedules and `{date:...}` |
| `SPOTIFY_PLAYLIST_BACKUP_CLIENT_ID` / `_CLIENT_SECRET` | Credentials of your app in the Spotify developer dashboard |
| `SPOTIFY_PLAYLIST_BACKUP_REDIRECT_URI` | Must match the redirect URI registered for the Spotify app |
| `SPOTIFY_PLAYLIST_BACKUP_RUN_ON_STARTUP` | Archive all configured playlists once on start |

## Setup

1. Create an app at the Spotify developer dashboard and register the redirect URI.
2. `cp .env.example .env`, `mkdir data` and `cp config.example.yml data/config.yml`, then fill in the values and list your playlists. The data directory (`SPOTIFY_PLAYLIST_BACKUP_DATA_DIR`, default `./data`) is mounted to `/data` and holds the config, the cached Spotify token and `status.json`; it must be writable by uid 1000 (`chown 1000:1000 data`).
3. Start with `docker compose up -d --build`. Without a Spotify token the container logs how to authorize and waits.
4. Authorize once from a terminal in the running container: `docker compose exec spotify-playlist-backup python /app/auth.py` (in a stack manager like Dockhand: open the container's terminal and run `python /app/auth.py`). Open the printed URL, approve, and paste the URL you were redirected to (the page itself won't load, that is expected). The token is stored in the data directory (`/data/.spotify-token`).

The container notices the token on its own and continues: it runs the optional startup archive (`RUN_ON_STARTUP`) and starts the scheduler. No restart is needed.

To use the image from another compose file (e.g. a stack manager), build straight from git and mount your data directory, which contains `config.yml`:

```yaml
services:
  spotify-playlist-backup:
    build: https://github.com/<user>/spotify-playlist-backup.git#main
    volumes:
      - /path/to/data:/data
```

The image contains only the application code; configuration and state stay in the data directory.

## Monitoring

Each archive run writes its result (`ok`, time, error) per playlist to `status.json` in the data directory. The container healthcheck (built into the image, see `healthcheck.py`) turns **unhealthy** until the one-time authorization is done and then while the most recent run of any playlist failed and recovers once that playlist succeeds again, so failures show up in Docker/Dockhand. The container restarts automatically (`unless-stopped`). No notifications are sent.

## Known limitations

- **Local files** are not copied into the archive. They are logged and listed in the archive playlist's description.

See [CHANGELOG.md](CHANGELOG.md) for the current state. Notably, Spotify-generated playlists (e.g. Release Radar, Discover Weekly) may not be readable through the API for newer Spotify apps.

## License

See [LICENSE](LICENSE).
