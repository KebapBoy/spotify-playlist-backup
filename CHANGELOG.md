# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Each archive run records its result in `/data/status.json`; the container healthcheck reports unhealthy while the last run of any job failed, and healthy again after that job succeeds.

### Changed
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
- Spotify-generated playlists may be inaccessible via the API.
- Local files are not archived (see above). Whether the Web API can add them at all is untested; planned: try adding them separately and fall back to skipping.
- A new copy is created even if the playlist is unchanged; only name collisions are deduplicated.
- Source lookup includes followed playlists, which can cause ambiguous-name errors.
