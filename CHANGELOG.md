# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.1.0] - 2026-11-01

Initial version, migrated unchanged from the Dockhand `spotify` stack.

### Added
- Scheduled archiving of Spotify playlists into private snapshot playlists (APScheduler cron jobs: `daily`, `weekly`, `monthly`).
- YAML configuration with target name templates (`{source_name}`, `{track_count}`, `{date:<strftime>}`).
- Spotify OAuth login with token cached in `/data`, plus an auth-only mode (`SPOTIFY_AUTH_ONLY`).
- Optional archive run on container start (`RUN_ON_STARTUP`).
- Dockerfile and standalone `compose.yaml`.

### Known issues
- Documented `hour` default of 8 in `config.yml` comments differs from the code default of 0.
- Spotify-generated playlists may be inaccessible via the API.
- Local files in a playlist likely cause adding tracks to fail.
- A failed job only logs; container has no restart policy or healthcheck.
- An exception in the `RUN_ON_STARTUP` loop aborts remaining playlists and the scheduler start.
- A new copy is created even if the playlist is unchanged; only name collisions are deduplicated.
- Source lookup includes followed playlists, which can cause ambiguous-name errors.
- Typos ("archieve") in log messages; unused `import sys`.
