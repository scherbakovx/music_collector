import requests


def analyze_link(url: str, songlink_token: str, service: str = 'spotify') -> str:
    url = "https://api.song.link/v1-alpha.1/links?url=%s&key=%s" % (url, songlink_token)
    response = requests.get(url)
    if response.status_code == 200:
        response_json = response.json()
        if service == 'spotify':
            return response_json.get('linksByPlatform', {}).get(service, {}).get('nativeAppUriDesktop', {})
        elif service == 'apple_music':
            return response_json.get('linksByPlatform', {}).get('appleMusic', {}).get('entityUniqueId', '').replace('ITUNES_SONG::', '')
        else:
            return None
    else:
        return None
