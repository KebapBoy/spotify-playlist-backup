# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Removed
- The `SPOTIFY_AUTH_ONLY` environment variable and the auth-only mode of `app.py`.

### Added
- Each archive run records its result in `/data/status.json`; the container healthcheck reports unhealthy while the last run of any job failed, and healthy again after that job succeeds.

### Changed
- Missing Spotify credentials now fail with a message naming the variables to set, instead of a spotipy error about unrelated variable names.
- Authorization is now a separate script, `auth.py`, run inside the running container (`docker exec -it <container> python /app/auth.py`). Without a token the app logs instructions and waits; once the token exists it continues on its own (startup archive, then scheduler). The healthcheck reports unhealthy until a token exists.
- The host path of the data directory is configurable via `SPOTIFY_PLAYLIST_BACKUP_DATA_DIR` (default `./data`), so the shipped compose file can be deployed unchanged, e.g. as a git stack.
- The healthcheck now lives in the image (`HEALTHCHECK` in the Dockerfile, script in `healthcheck.py`) instead of the compose file.
- `app.py` is now baked into the image (`COPY` in the Dockerfile) instead of being mounted via compose `configs`, so the image can be built straight from a git URL.
- The configuration is no longer part of the image or the compose file: `config.yml` is read from `/data/config.yml`, i.e. from the mounted data directory (a bind mount, `./data` in the shipped compose file, instead of a named volume). The Spotify token and `status.json` live there as well. The directory must be writable by uid 1000.
- The example configuration is now `config.example.yml`; `data/` is git-ignored so personal playlists and tokens are not committed.
- A missing `/data/config.yml` now fails with a message explaining how to create it.
- "Source playlist not found" now reports how many playlists the library contains and the closest matching names, to make name typos and missing library entries easy to diagnose.
- Source playlist lookup prefers playlists you own; followed playlists (e.g. Spotify-generated ones) are used only when no owned playlist has that name. An ambiguity error is raised only within the chosen group.
- The "archive already exists" check only considers your own playlists, so a followed playlist with the target name no longer causes a run to be skipped.
- Local files in a source playlist are skipped instead of making the run fail. They are logged as "artist - title" and listed in the archive playlist's description (truncated to Spotify's 300 character limit). `{track_count}` counts only the tracks that were actually archived.
- Restart policy is now `unless-stopped` (was `no`).

### Fixed
- `config.yml` comments documented a default `hour` of 8 for daily and weekly jobs; the actual default is 0.
- Typos ("archieve") in log messages; removed unused `import sys`.
- A failing playlist during the `RUN_ON_STARTUP` run no longer aborts the remaining playlists or prevents the scheduler from starting; the error is logged with a traceback.

## [0.1.0] - 2026-11-01

Initial version, migrated unchanged from the Dockhand `spotify` stack.

### Added
- Scheduled archiving of Spotify playlists into private snapshot playlists (APScheduler cron jobs: `daily`, `weekly`, `monthly`).
- YAML configuration with target name templates (`{source_name}`, `{track_count}`, `{date:<strftime>}`).
- Spotify OAuth login with token cached in `/data`, plus an auth-only mode (`SPOTIFY_AUTH_ONLY`).
- Optional archive run on container start (`RUN_ON_STARTUP`).
- Dockerfile and standalone `compose.yaml`.

### Known issues
- Spotify-generated playlists may be inaccessible via the API. Both startup runs so far (2026-10-30, 2026-10-31) failed with "Source playlist not found: Mein Mix der Woche"; cause still to be determined (name, library membership or API restriction).
- Local files are not archived (see above). Whether the Web API can add them at all is untested; planned: try adding them separately and fall back to skipping.
- A new copy is created even if the playlist is unchanged; only name collisions are deduplicated.
