import json
import requests


def refresh_spotify_token(refresh_token: str, bearer_token: str):
    response = requests.post(
        'https://accounts.spotify.com/api/token',
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        },
        headers={
            'Authorization': f'Basic {bearer_token}'
        }
    )
    if response.status_code == 200:
        return response.json()
    else:
        return {}


def check_if_track_in_playlist(uri: str, playlist_id: str, access_token: str) -> bool:
    url = "https://api.spotify.com/v1/playlists/%s/tracks?limit=20" % playlist_id
    response = requests.get(
        url,
        headers={
            'Authorization': 'Bearer %s' % access_token
        }
    )
    if response.status_code == 401:
        return 401

    response_json = response.json()
    for track in response_json.get('items', []):
        if track.get('track', {}).get('uri') == uri:
            return True
    return False


def add_track_to_spotify_playlist(uri: str, telegram_user_id: str, bearer_token: str) -> bool:
    f = open('users/%s.json' % telegram_user_id, 'r')
    current_user_data = json.load(f)

    playlist_id = current_user_data['user_spotify_playlist_id']

    track_already_added = check_if_track_in_playlist(uri, playlist_id, current_user_data['spotify_credentials']['access_token'])
    if isinstance(track_already_added, int) and track_already_added == 401:
        refresh_token = current_user_data['spotify_credentials']['refresh_token']
        current_user_data['spotify_credentials'] = refresh_spotify_token(refresh_token, bearer_token)
        current_user_data['spotify_credentials']['refresh_token'] = refresh_token
        with open('users/%s.json' % telegram_user_id, 'w') as f:
            json.dump(current_user_data, f)
        track_already_added = check_if_track_in_playlist(uri, playlist_id, current_user_data['spotify_credentials']['access_token'])

    if not track_already_added:
        url = "https://api.spotify.com/v1/playlists/%s/tracks?uris=%s" % (playlist_id, uri)
        requests.post(
            url,
            headers={
                'Authorization': 'Bearer %s' % current_user_data['spotify_credentials']['access_token']
            }
        )
        return True

    return False


def get_user_spotify_id(access_token: str) -> str:
    response = requests.get(
        'https://api.spotify.com/v1/me',
        headers={
            'Authorization': 'Bearer %s' % access_token
        }
    )
    if response.status_code == 200:
        return response.json().get('id')


def create_playlist_for_user(user_id: str, access_token: str) -> str:
    playlist_data = {
      "name": "Music Collector Playlist",
      "description": "Here are all the track your friends sent you :)",
      "public": False
    }

    response = requests.post(
        "https://api.spotify.com/v1/users/%s/playlists" % user_id,
        data=json.dumps(playlist_data),
        headers={
            'Authorization': 'Bearer %s' % access_token
        }
    )
    if response.status_code == 201:
        return response.json().get('id')


def get_access_refresh_token(code: str, bearer_token: str) -> dict:
    response = requests.post(
        'https://accounts.spotify.com/api/token',
        data={
            'grant_type': 'authorization_code',
            'redirect_uri': 'https://music.scherbakov.top/api/v1/spotify_login',
            'code': code
        },
        headers={
            'Authorization': f'Basic {bearer_token}'
        }
    )
    if response.status_code == 200:
        return response.json()
    else:
        return {}
