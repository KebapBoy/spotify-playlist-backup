from spotify_auth import has_token, spotify_client

# One-time authorization, run inside the container:
#   docker exec -it <container> python /app/auth.py
# The running app picks up the token on its own.

def main():
    if has_token():
        print("A Spotify token already exists; checking that it works...", flush=True)
    else:
        print("Starting Spotify authorization flow...", flush=True)

    user = spotify_client().current_user()

    print(f"Authenticated as: {user['display_name']} ({user['id']})", flush=True)

if __name__ == "__main__":
    main()
