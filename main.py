import re
import json
import asyncio
from aiohttp import web
import json
import requests

try:
    tokens = json.loads(open('credentials.json').read())
except FileNotFoundError:
    print("There is no credentials.json file. Please, create one.")
    exit(1)
else:
    try:
        TELEGRAM_TOKEN = tokens["TELEGRAM_TOKEN"]
        SPOTIFY_CLIENT_ID = tokens["SPOTIFY_CLIENT_ID"]
        APPLE_MUSIC_DEVELOPER_TOKEN = tokens["APPLE_MUSIC_DEVELOPER_TOKEN"]
        SONGLINK_KEY = tokens["SONGLINK_KEY"]
        SPOTIFY_BEARER_TOKEN = tokens["SPOTIFY_BEARER_TOKEN"]
    except KeyError as exc:
        print(f"There is no {str(exc)} in credentials.json")
        exit(1)

from api import analyze_link
from spotify import (
    add_track_to_spotify_playlist,
    get_user_spotify_id,
    create_playlist_for_user,
    get_access_refresh_token
)
from apple_music import (
    create_playlist_for_user_in_apple_music,
    add_track_to_apple_music_playlist
)

TOKEN = TELEGRAM_TOKEN
API_URL = 'https://api.telegram.org/bot%s/sendMessage' % TOKEN


TELEGRAM_HEADERS = {
    'Content-Type': 'application/json'
}


def send_message_to_telegram(message):
    message['parse_mode'] = 'markdown'
    requests.post(API_URL, data=json.dumps(message), headers=TELEGRAM_HEADERS)


def find_links_in_message(message: str) -> list:
    urls = re.findall('(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-&?=%.]+', message)
    return urls


async def handler(request):
    try:
        data = await request.json()
    except json.decoder.JSONDecodeError:
        data = None
    else:
        if data['message'].get('text', '') == '/start':
            try:
                _ = open('users/%s.json' % data['message']['chat']['id'], 'r')
            except IOError:
                message = {
                    'chat_id': data['message']['chat']['id'],
                    'text': "Привет! Если ты отправишь мне ссылку на трек (из любого сервиса) я добавлю его в твой плейлист. Пока я работаю только в Spotify и Apple Music, но дальше — больше!"
                }
                send_message_to_telegram(message)

                message = {
                    'chat_id': data['message']['chat']['id'],
                    'text': "Пожалуйста, перейди по этой [ссылке](https://accounts.spotify.com/authorize?client_id=%s&response_type=code&scope=playlist-modify-private&redirect_uri=https://music.scherbakov.top/api/v1/spotify_login&state=%s), если у тебя Spotify и по [этой](https://music.scherbakov.top/apple_music_login?state=%s), если у тебя Apple Music: это нужно, чтобы я мог управлять твоими приватными плейлистами." % (SPOTIFY_CLIENT_ID, data['message']['chat']['id'], data['message']['chat']['id'])
                }
                send_message_to_telegram(message)
            else:
                message = {
                    'chat_id': data['message']['chat']['id'],
                    'text': "Ты уже залогинен!"
                }
                send_message_to_telegram(message)
        else:
            links_in_message = find_links_in_message(data['message'].get('text', ''))
            if links_in_message:
                f = open('users/%s.json' % str(data['message']['chat']['id']), 'r')
                current_user_data = json.load(f)
                service = 'spotify' if current_user_data.get('spotify_credentials') else 'apple_music'
                song_uri = analyze_link(links_in_message[0], SONGLINK_KEY, service=service)
            else:
                song_uri = None
            if song_uri:
                if 'album' in song_uri or 'ALBUM' in song_uri:
                    message = {
                        'chat_id': data['message']['chat']['id'],
                        'text': "Извини, я пока не работаю с альбомами :("
                    }
                    send_message_to_telegram(message)
                else:
                    if service == 'spotify':
                        added = add_track_to_spotify_playlist(song_uri, str(data['message']['chat']['id']), SPOTIFY_BEARER_TOKEN)
                    else:
                        added = add_track_to_apple_music_playlist(song_uri, str(data['message']['chat']['id']))
                    if added:
                        message = {
                            'chat_id': data['message']['chat']['id'],
                            'text': "Плейлист обновлён!"
                        }
                        send_message_to_telegram(message)
                    else:
                        message = {
                            'chat_id': data['message']['chat']['id'],
                            'text': "Трек уже был добавлен, беги слушать!"
                        }
                        send_message_to_telegram(message)
            else:
                message = {
                    'chat_id': data['message']['chat']['id'],
                    'text': "Что-то пошло не так (скорее всего трек на нашёлся в Spotify или Apple Music)"
                }
                send_message_to_telegram(message)
    return web.Response(status=200)


async def spotify_start_flow(request):
    user_code = request.rel_url.query['code']
    user_telegram_id = request.rel_url.query['state']

    try:
        _ = open('users/%s.json' % user_telegram_id, 'r')
    except IOError:
        current_user_data = {}
        user_spotify_data = get_access_refresh_token(user_code, SPOTIFY_BEARER_TOKEN)

        current_user_data['spotify_credentials'] = user_spotify_data
        access_token = user_spotify_data['access_token']

        user_spotify_id = get_user_spotify_id(access_token)

        current_user_data['user_spotify_id'] = user_spotify_id

        playlist_id = create_playlist_for_user(user_spotify_id, access_token)
        if playlist_id:
            current_user_data['user_spotify_playlist_id'] = playlist_id

            with open('users/%s.json' % user_telegram_id, 'w') as f:
                json.dump(current_user_data, f)

            message = {
                'chat_id': user_telegram_id,
                'text': "Всё готово к работе, как и твой новый чистенький плейлист :)"
            }
            send_message_to_telegram(message)
    else:
        message = {
            'chat_id': user_telegram_id,
            'text': "Ты уже залогинен!"
        }
        send_message_to_telegram(message)

    return web.Response(status=200, text='Всё кайф!')


async def apple_music_start_flow(request):
    user_code = request.rel_url.query['code'].replace(' ', '+')
    user_telegram_id = request.rel_url.query['state']

    try:
        _ = open('users/%s.json' % user_telegram_id, 'r')
    except IOError:
        current_user_data = {}

        current_user_data['apple_music_credentials'] = {
            "music_user_token": user_code,
            "developer_token": APPLE_MUSIC_DEVELOPER_TOKEN
        }

        playlist_id = create_playlist_for_user_in_apple_music(
            user_code,
            APPLE_MUSIC_DEVELOPER_TOKEN
        )
        if playlist_id:
            current_user_data['user_apple_music_playlist_id'] = playlist_id

            with open('users/%s.json' % user_telegram_id, 'w') as f:
                json.dump(current_user_data, f)

            message = {
                'chat_id': user_telegram_id,
                'text': "Всё готово к работе, как и твой новый чистенький плейлист :)"
            }
            send_message_to_telegram(message)
    else:
        message = {
            'chat_id': user_telegram_id,
            'text': "Ты уже залогинен!"
        }
        send_message_to_telegram(message)

    return web.Response(status=200, text='Всё кайф!')


async def init_app(loop):
    app = web.Application(loop=loop, middlewares=[])
    app.router.add_post('/api/v1', handler)
    app.router.add_get('/api/v1/spotify_login', spotify_start_flow)
    app.router.add_get('/api/v1/apple_music_login', apple_music_start_flow)
    return app


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        app = loop.run_until_complete(init_app(loop))
        web.run_app(app, host='0.0.0.0', port=12345)
    except Exception as e:
        print('Error create server: %r' % e)
    finally:
        pass
    loop.close()
