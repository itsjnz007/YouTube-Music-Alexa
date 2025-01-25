import asyncio
import time
import yt_dlp, re
from ytmusicapi import YTMusic
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

class Supporting:
    async def get_radiolist(song_name: str):
        ytmusic = YTMusic()
        search_results = await asyncio.to_thread(ytmusic.search, query=song_name, filter='songs', ignore_spelling=True)
        if not search_results:
            return None

        video_id = search_results[0].get('videoId')
        if not video_id:
            return None

        radio_results = await asyncio.to_thread(ytmusic.get_watch_playlist, videoId=video_id, radio=True)
        songs = radio_results.get('tracks', [])
        if not songs:
            return None

        return [
            {
                'title': track["title"],
                'artist': " and ".join([artist["name"] for artist in track.get("artists", [])]),
                'video_id': track["videoId"],
                'thumbnail': track['thumbnail'][-1] if track.get('thumbnail') else None
            }
            for track in songs
        ]

    async def get_artist(artist_name: str):
        ytmusic = YTMusic()
        search_results = await asyncio.to_thread(ytmusic.search, query=artist_name, filter='songs', ignore_spelling=True)
        if not search_results:
            return None

        return [
            {
                'title': track["title"],
                'artist': " and ".join([artist["name"] for artist in track.get("artists", [])]),
                'video_id': track["videoId"],
                'thumbnail': track['thumbnails'][-1] if track.get('thumbnails') else None
            }
            for track in search_results
        ]

    async def get_album(album_name: str):
        ytmusic = YTMusic()
        search_results = await asyncio.to_thread(ytmusic.search, query=album_name, filter='albums', ignore_spelling=True)
        if not search_results:
            return None

        browse_id = search_results[0].get('browseId')
        if not browse_id:
            return None

        album_results = await asyncio.to_thread(ytmusic.get_album, browseId=browse_id)
        songs = album_results.get("tracks", [])
        if not songs:
            return None

        return [
            {
                'title': track["title"],
                'artist': " and ".join([artist["name"] for artist in track.get("artists", [])]),
                'video_id': track["videoId"],
                'thumbnail': track['thumbnails'][-1] if track.get('thumbnails') else None
            }
            for track in songs
        ]
    
    async def stream_playlist(playlist_id: str):
        ytmusic = YTMusic()
        search_results = await asyncio.to_thread(ytmusic.get_playlist, playlistId=playlist_id)
        playlist_raw = search_results['tracks']
        if not playlist_raw:
            return None

        playlist = [
            {
                'title': track["title"],
                'artist': " and ".join([artist["name"] for artist in track.get("artists", [])]),
                'video_id': track["videoId"],
                'thumbnail': track['thumbnails'][-1] if track.get('thumbnails') else None
            }
            for track in playlist_raw
        ]
        stream = await Supporting.get_stream(playlist[0]['video_id'])
        return {'song_info': {'metadata': playlist[0], 'stream': stream}, 'playlist': playlist}

    async def get_stream(video_id: str):
        ydl_opts = {
            "default_search": "ytsearch",
            "ignoreerrors": True,
            "format": "m4a/bestaudio/best",
            "noplaylist": True,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "quiet": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, video_id, download=False)
            if not info:
                return None

            for fmt in info.get("formats", []):
                if fmt.get("ext") == "m4a":
                    return {'audio_url': fmt["url"]}
        return None

    async def find_stream_list(query: str, filter: str = 'songs'):
        if filter == 'songs':
            playlist = await Supporting.get_radiolist(query)
        elif filter == 'artists':
            playlist = await Supporting.get_artist(query)
        elif filter == 'albums':
            playlist = await Supporting.get_album(query)
        else:
            raise Exception(f'Unknown filter "{filter}"')

        if not playlist:
            return None

        stream = await Supporting.get_stream(playlist[0]['video_id'])
        return {'song_info': {'metadata': playlist[0], 'stream': stream}, 'playlist': playlist}

    def playlist_url_to_encoded_id(url):
        playlist_id = re.match(r"^[\w]+", url.split('list=')[-1]).group()
        return Supporting.encode_to_hex(playlist_id)
    
    def encode_to_hex(string):
        return ''.join([hex(ord(c))[2:].zfill(2) for c in string])

    async def get_playlist_info(playlist_id: str):
        ytmusic = YTMusic()
        playlist_raw = await asyncio.to_thread(ytmusic.get_playlist, playlist_id)
        if not playlist_raw:
            return None

        return {'id': playlist_raw['id'], 'title': playlist_raw['title']}
    
@app.route("/get_playlist_info/", methods=["GET"])
async def get_playlist_info():
    start_time = time.time()
    playlist_id = request.args.get("id")
    response = await Supporting.get_playlist_info(playlist_id)
    print(f'Completed request in {time.time() - start_time:.2f} seconds.')
    return jsonify(response)

@app.route("/stream_playlist/", methods=["GET"])
async def stream_playlist():
    start_time = time.time()
    playlist_id = request.args.get("id")
    response = await Supporting.stream_playlist(playlist_id)
    print(f'Completed request in {time.time() - start_time:.2f} seconds.')
    return jsonify(response)


@app.route("/get_stream/", methods=["GET"])
async def get_stream():
    start_time = time.time()
    video_id = request.args.get("video_id")
    response = await Supporting.get_stream(video_id)
    print(f'Completed request in {time.time() - start_time:.2f} seconds.')
    return jsonify(response)


@app.route("/find_stream_list/", methods=["GET"])
async def find_stream_list():
    start_time = time.time()
    query = request.args.get("query")
    filter = request.args.get("filter")
    response = await Supporting.find_stream_list(query, filter)
    print(f'Completed request in {time.time() - start_time:.2f} seconds.')
    return jsonify(response)


@app.route("/", methods=["GET", "POST"])
def index():
    hex_value = ""
    if request.method == "POST":
        apiurl_input = request.form["apiurl_input"]
        playlist_input = request.form["playlist_input"]
        if apiurl_input: hex_value = Supporting.encode_to_hex(apiurl_input)
        elif playlist_input: hex_value = Supporting.playlist_url_to_encoded_id(playlist_input)
        else: hex_value = 'Please fill the form to get encoded output.'
    return render_template("index.html", hex_value=hex_value)


# Main entry point
if __name__ == "__main__":
    app.run(port=5000)
