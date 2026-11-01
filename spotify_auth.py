import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

TOKEN_PATH = "/data/.spotify-token"

def auth_manager():
    return SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope=(
            "playlist-read-private "
            "playlist-read-collaborative "
            "playlist-modify-private "
            "playlist-modify-public"
        ),
        cache_path=TOKEN_PATH,
        open_browser=False
    )

def spotify_client():
    return spotipy.Spotify(auth_manager=auth_manager())

def has_token():
    return auth_manager().cache_handler.get_cached_token() is not None
