# Spotify Playlist Backup

A small containerized service that archives Spotify playlists on a schedule. Playlists like "Mein Mix der Woche" or "Release Radar" change constantly; this keeps dated snapshot copies as private playlists in your own account.

## How it works

1. `config.yml` lists the playlists to archive, each with a schedule (`daily`, `weekly`, `monthly`) and a target name template.
2. For each entry, an APScheduler cron job:
   - looks up the source playlist by exact name (fails if missing or ambiguous),
   - collects all track URIs (podcast episodes are skipped),
   - renders the target name from the template,
   - skips the run if a playlist with that name already exists,
   - otherwise creates a new **private** playlist and adds the tracks in batches of 100.
3. With `RUN_ON_STARTUP=true`, every configured playlist is archived once on container start before the scheduler begins.

## Configuration

### `config.yml`

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
| `SPOTIFY_PLAYLIST_BACKUP_AUTH_ONLY` | Only run the login flow, then exit |

## Setup

1. Create an app at the Spotify developer dashboard and register the redirect URI.
2. `cp .env.example .env` and fill in the values.
3. Authorize once: set `SPOTIFY_PLAYLIST_BACKUP_AUTH_ONLY=true`, run `docker compose run --rm spotify-playlist-backup`, open the printed URL, and paste the redirected URL back. The token is cached in the `spotify-playlist-backup` volume (`/data/.spotify-token`).
4. Set `AUTH_ONLY=false` and start with `docker compose up -d`.

## Known limitations

See [CHANGELOG.md](CHANGELOG.md) for the current state. Notably, Spotify-generated playlists (e.g. Release Radar, Discover Weekly) may not be readable through the API for newer Spotify apps.

## License

See [LICENSE](LICENSE).
