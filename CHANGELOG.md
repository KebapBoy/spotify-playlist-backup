# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Each archive run records its result in `/data/status.json`; the container healthcheck reports unhealthy while the last run of any job failed, and healthy again after that job succeeds.

### Changed
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
- Local files in a playlist likely cause adding tracks to fail.
- A new copy is created even if the playlist is unchanged; only name collisions are deduplicated.
- Source lookup includes followed playlists, which can cause ambiguous-name errors.
