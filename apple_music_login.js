document.addEventListener('musickitloaded', function() {
  // MusicKit global is now defined

  const json = fs.readFileSync("./data.json", "utf8");
  const data = JSON.parse(json);

  const music = MusicKit.configure({
      developerToken: data["APPLE_MUSIC_DEVELOPER_TOKEN"],
    app: {
      name: 'My Cool Web App',
      build: '1978.4.1'
    }
  });

  document.getElementById('apple-music-authorize').addEventListener('click', () => {
    /***
      Returns a promise which resolves with a music-user-token when a user successfully authenticates and authorizes
      https://developer.apple.com/documentation/musickitjs/musickit/musickitinstance/2992701-authorize
    ***/
    music.authorize().then(musicUserToken => {
      var url_string = window.location.href;
      var url = new URL(url_string);
      var state = url.searchParams.get("state");

      const Http = new XMLHttpRequest();
      const send_token_url = `https://music.scherbakov.top/api/v1/apple_music_login?code=${musicUserToken}&state=${state}`;
      Http.open("GET", send_token_url);
      Http.send();

      Http.onreadystatechange = function() {
        if (Http.readyState == 4 && Http.status == 200) {
          alert(Http.responseText);
        }
      }
    });
  });

  // expose our instance globally for testing
  window.music = music;

});