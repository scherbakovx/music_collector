import json
import requests


def add_track_to_apple_music_playlist(uri: str, telegram_user_id: str) -> bool:

    f = open('users/%s.json' % telegram_user_id, 'r')
    current_user_data = json.load(f)

    playlist_id = current_user_data['user_apple_music_playlist_id']

    url = "https://api.music.apple.com/v1/me/library/playlists/%s/tracks" % playlist_id
    song_data = {
       "data": [
          {
             "id": uri,
             "type": "songs"
          }
       ]
    }
    response = requests.post(
        url,
        data=json.dumps(song_data),
        headers={
            'Authorization': 'Bearer %s' % current_user_data['apple_music_credentials']['developer_token'],
            'Music-User-Token': current_user_data['apple_music_credentials']['music_user_token']
        }
    )
    if response.status_code == 204:
        return True

    return False


def create_playlist_for_user_in_apple_music(music_user_token: str, developer_token: str) -> str:

    playlist_data = {
        "attributes": {
            "name": "Music Collector Playlist",
            "description": "Here are all the track your friends sent you :)"
        }
    }

    response = requests.post(
        "https://api.music.apple.com/v1/me/library/playlists",
        data=json.dumps(playlist_data),
        headers={
            'Authorization': 'Bearer %s' % developer_token,
            'Music-User-Token': music_user_token
        }
    )
    if response.status_code == 201:
        return response.json()['data'][0]['id']
