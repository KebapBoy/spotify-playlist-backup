import os
import pwd

from spotify_auth import has_token, spotify_client

# One-time authorization, run inside the container:
#   docker exec -it <container> python /app/auth.py
# The running app picks up the token on its own.

APP_USER = "appuser"

def drop_privileges():
    # some terminals open a root shell; the token must belong to the app user
    if os.geteuid() != 0:
        return

    user = pwd.getpwnam(APP_USER)

    os.initgroups(user.pw_name, user.pw_gid)
    os.setgid(user.pw_gid)
    os.setuid(user.pw_uid)

    os.environ["HOME"] = user.pw_dir

def main():
    drop_privileges()

    if has_token():
        print("A Spotify token already exists; checking that it works...", flush=True)
    else:
        print("Starting Spotify authorization flow...", flush=True)

    user = spotify_client().current_user()

    print(f"Authenticated as: {user['display_name']} ({user['id']})", flush=True)

if __name__ == "__main__":
    main()
