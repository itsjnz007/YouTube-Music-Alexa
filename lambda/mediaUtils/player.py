from typing import Dict, List, Tuple
from ask_sdk_model import Request, Response
from ask_sdk_model.interfaces.audioplayer import PlayDirective, PlayBehavior, AudioItem, Stream, AudioItemMetadata, StopDirective
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.response_helper import ResponseFactory
from ask_sdk_model.services.directive import (SendDirectiveRequest, Header, SpeakDirective)
import logging, random, urllib3, json, data, logging
from ask_sdk_model.interfaces import display
from dacite import from_dict
from dataclasses import asdict
from models import player_models
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
http = urllib3.PoolManager()

def send_progressive_response(handler_input: HandlerInput, message: str):
    request_id_holder = handler_input.request_envelope.request.request_id
    directive_header = Header(request_id=request_id_holder)
    speech = SpeakDirective(speech=message)
    directive_request = SendDirectiveRequest(header=directive_header, directive=speech)
    directive_service_client = handler_input.service_client_factory.get_directive_service()
    directive_service_client.enqueue(directive_request)
    return

def decode_hex(encoded_string: str) -> str:
    lower_encoded_string = encoded_string.lower()
    return ''.join([chr(int(lower_encoded_string[i:i+2], 16)) for i in range(0, len(lower_encoded_string), 2)])

def get_similarity(x: str, y: str):
    x, y = x.lower(), y.lower()
    intersection_cardinality = len(set.intersection(*[set(x), set(y)]))
    union_cardinality = len(set.union(*[set(x), set(y)]))
    return intersection_cardinality/float(union_cardinality)


class Attributes:
    @staticmethod
    def log_attributes(handler_input: HandlerInput):
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        logger.info(f'persistent_attributes -> {persistent_attr}')

    @staticmethod
    def get_user_id(handler_input: HandlerInput) -> str:
        user_id = handler_input.request_envelope.context.system.user.user_id
        return user_id

    @staticmethod
    def get_user_attributes(handler_input: HandlerInput) -> Dict:
        persistent_attr = handler_input.attributes_manager.persistent_attributes
        user_attr = persistent_attr.get(Attributes.get_user_id(handler_input))
        return user_attr
    
    @staticmethod
    def get_playback_info(handler_input: HandlerInput) -> Dict:
        user_attr = Attributes.get_user_attributes(handler_input)
        playback_info = user_attr.get('playback_info')
        return playback_info
    
    @staticmethod
    def get_playback_setting(handler_input: HandlerInput) -> Dict:
        user_attr = Attributes.get_user_attributes(handler_input)
        playback_setting = user_attr.get("playback_setting")
        return playback_setting

    @staticmethod
    def get_playlist(handler_input: HandlerInput) -> List[player_models.Metadata]:
        user_attr = Attributes.get_user_attributes(handler_input)
        playlist = [from_dict(player_models.Metadata, i) for i in user_attr.get('playlist')]
        return playlist
    
    @staticmethod
    def set_playlist(handler_input: HandlerInput, playlist: List[player_models.Metadata]) -> None:
        user_attr = Attributes.get_user_attributes(handler_input)
        user_attr['playlist'] = [asdict(i) for i in playlist]

    @staticmethod
    def get_play_order(handler_input: HandlerInput):
        playback_info = Attributes.get_playback_info(handler_input)
        return playback_info['play_order']

    @staticmethod
    def set_play_order(handler_input: HandlerInput) -> None:
        playback_setting = Attributes.get_playback_setting(handler_input)
        playback_info = Attributes.get_playback_info(handler_input)
        playlist = Attributes.get_playlist(handler_input)
        shuffle = playback_setting['shuffle']

        if shuffle:
            shuffled_play_order = Attributes.shuffle_order(handler_input)
            playback_info['play_order'] = shuffled_play_order
            shuffled_index_adjusted_play_order = Attributes.rotate_to_match_index(handler_input)
            playback_info["play_order"] = shuffled_index_adjusted_play_order
        else:
            playback_info["play_order"] = [l for l in range(0, len(playlist))]

    @staticmethod
    def get_from_saved_playlists(handler_input: HandlerInput, playlist_name: str) -> player_models.Playlist:
        user_attr = Attributes.get_user_attributes(handler_input)
        saved_playlists = user_attr['saved_playlists']
        playlist = saved_playlists.get(playlist_name)
        logger.info(f'saved_playlists -> {saved_playlists}, playlist -> {playlist}, playlist_name -> {playlist_name}')
        if playlist: return from_dict(player_models.Playlist, playlist)

    @staticmethod
    def get_offset_in_ms(handler_input: HandlerInput):
        return handler_input.request_envelope.request.offset_in_milliseconds

    @staticmethod
    def get_token(handler_input: HandlerInput):
        return handler_input.request_envelope.request.token

    @staticmethod
    def get_metadata_by_play_order(handler_input: HandlerInput, index: int = None) -> player_models.Metadata: 
        playback_info = Attributes.get_playback_info(handler_input)
        if not index: index = playback_info["index"]
        play_order_index = playback_info['play_order'][index]
        playlist = Attributes.get_playlist(handler_input)
        return playlist[play_order_index]

    @staticmethod
    def shuffle_order(handler_input: HandlerInput) -> List[int]:
        play_order = [l for l in range(0, len(Attributes.get_playlist(handler_input)))]
        random.shuffle(play_order)
        return play_order
    
    @staticmethod
    def rotate_to_match_index(handler_input: HandlerInput) -> List[int]:
        playback_info = Attributes.get_playback_info(handler_input)
        play_order = playback_info['play_order']
        current_index = playback_info['index']
        diff = play_order.index(current_index)-current_index
        return play_order[diff:]+play_order[:diff]
    
    @staticmethod
    def match_playlist_name(handler_input: HandlerInput, playlist_name: str, match_similarity: float = 0.7) -> str:
        user_attr = Attributes.get_user_attributes(handler_input)
        saved_playlists = user_attr['saved_playlists']
        all_list = list(saved_playlists.keys())
        for name in all_list:
            similarity = get_similarity(name, playlist_name)
            logger.info(f'similarity -> {similarity}, left -> {name}, right -> {playlist_name}')
            if similarity > match_similarity: return name
        return None
    
    @staticmethod
    def get_audio_item_metadata(metadata: player_models.Metadata) -> AudioItemMetadata:
        return AudioItemMetadata(
            title=metadata.title,
            subtitle=metadata.artist,
            art=metadata.thumbnail.url
        )
    
    @staticmethod
    def get_audio_item_metadata(metadata: player_models.Metadata) -> AudioItemMetadata:
        metadata = AudioItemMetadata(
            title=metadata.title,
            subtitle=metadata.artist,
            art=display.Image(
                content_description=metadata.title,
                sources=[
                    display.ImageInstance(
                        url=metadata.thumbnail.url)
                ]
            )
            , background_image=display.Image(
                content_description=metadata.title,
                sources=[
                    display.ImageInstance(
                        url=metadata.thumbnail.url)
                ]
            )
        )
        return metadata
    
    @staticmethod
    def get_calculated_index(handler_input: HandlerInput) -> int:
        current_video_id = handler_input.request_envelope.request.token
        playlist = Attributes.get_playlist(handler_input)
        play_order = Attributes.get_play_order(handler_input)
        playlist_tokens = [i.video_id for i in playlist]
        playlist_index = playlist_tokens.index(current_video_id)
        index = play_order.index(playlist_index)
        return index
    
    @staticmethod
    def get_api_url(handler_input: HandlerInput) -> Tuple[str, Exception]:
        user_attr = Attributes.get_user_attributes(handler_input)
        api_url = user_attr.get('api_url')
        if not api_url: return None, Exception(data.API_URL_NOT_SET)
        return api_url, None


class Api:
    @staticmethod
    def find_stream_list(handler_input: HandlerInput, query: str, filter: player_models.Filter) -> Tuple[player_models.SongInfoList, Exception]:
        api_url, error = Attributes.get_api_url(handler_input)
        if error: return None, error
        url = f"{api_url}/find_stream_list/?query={query}&filter={filter.value}"
        response = http.request("GET", url)
        if response.status == 200: 
            song_info_list = json.loads(response.data.decode("utf-8"))
            return from_dict(player_models.SongInfoList, song_info_list), None
        else: 
            return None, Exception(data.API_CONNECTION_ISSUE)

    @staticmethod  
    def stream_playlist(handler_input: HandlerInput, playlist_id: str) -> Tuple[player_models.SongInfoList, Exception]:
        api_url, error = Attributes.get_api_url(handler_input)
        if error: return None, error
        url = f"{api_url}/stream_playlist/?id={playlist_id}"
        response = http.request("GET", url)
        if response.status == 200: 
            song_info_list = json.loads(response.data.decode("utf-8"))
            return from_dict(player_models.SongInfoList, song_info_list), None
        else: return None, Exception(data.API_CONNECTION_ISSUE)
        
    @staticmethod
    def get_stream(handler_input: HandlerInput, video_id: str) -> Tuple[player_models.Stream, None]:
        api_url, error = Attributes.get_api_url(handler_input)
        if error: return None, error
        url = f"{api_url}/get_stream/?video_id={video_id}"
        response = http.request("GET", url)
        if response.status == 200: 
            response_json = json.loads(response.data.decode("utf-8"))
            stream = from_dict(player_models.Stream, response_json)
            player_info = Attributes.get_playback_info(handler_input)
            player_info['stream_url'] = stream.audio_url
            return stream, None
        else: return None, Exception(data.API_CONNECTION_ISSUE)
        
    @staticmethod
    def get_playlist_info(handler_input: HandlerInput, playlist_id: str) -> Tuple[player_models.Playlist, None]:
        api_url, error = Attributes.get_api_url(handler_input)
        if error: return None, error
        url = f"{api_url}/get_playlist_info/?id={playlist_id}"
        response = http.request("GET", url)
        if response.status == 200:
            response_json = json.loads(response.data.decode("utf-8"))
            return player_models.Playlist(response_json['id'], response_json['title']), None
        else: return None, Exception(data.API_CONNECTION_ISSUE)


class Controller:
    @staticmethod
    def fetch(
        handler_input: HandlerInput, 
        query: str = None,
        playlist_id: str = None, 
        filter: player_models.Filter = player_models.Filter.SONGS, 
        is_playback: bool = True
    ) -> Response:
        if query:
            song_info_list, error = Api.find_stream_list(handler_input, query, filter)
            if error: return handler_input.response_builder.speak(str(error)).response
            playlist = song_info_list.playlist
            song_info = song_info_list.song_info
        else:
            song_info_list, error = Api.stream_playlist(handler_input, playlist_id)
            if error: return handler_input.response_builder.speak(str(error)).response
            playlist = song_info_list.playlist
            song_info = song_info_list.song_info

        user_attr = Attributes.get_user_attributes(handler_input)
        Attributes.set_playlist(handler_input, playlist)
        user_attr['playback_info'] = {
            'index': 0,
            'offset_in_ms': 0,
            'play_order': [l for l in range(0, len(playlist))],
            'stream_url': song_info.stream.audio_url
        }
        Attributes.set_play_order(handler_input)
        return Controller.play(handler_input, song_info, is_playback)

    @staticmethod
    def play(
        handler_input: HandlerInput, 
        song_info: player_models.SongInfo, 
        is_playback: bool = False,
        play_behavior: PlayBehavior = PlayBehavior.REPLACE_ALL
    ) -> Response:
        response_builder = handler_input.response_builder

        playback_info = Attributes.get_playback_info(handler_input)
        offset_in_ms = playback_info.get('offset_in_ms')
        if play_behavior == PlayBehavior.REPLACE_ALL: playback_info['next_stream_enqueued'] = False
        else: playback_info['next_stream_enqueued'] = True

        # Log all attrubutes ----------------------------------
        Attributes.log_attributes(handler_input)
        # -----------------------------------------------------

        response_builder.add_directive(
            PlayDirective(
                play_behavior=play_behavior,
                audio_item=AudioItem(
                    stream=Stream(
                        token=song_info.metadata.video_id,
                        url=song_info.stream.audio_url,
                        offset_in_milliseconds=offset_in_ms,
                        expected_previous_token=None),
                    metadata=Attributes.get_audio_item_metadata(song_info.metadata)))
        ).set_should_end_session(True)
        if not is_playback:
            response_builder.speak(data.PLAYBACK_PLAY.format(song_info.metadata.title, song_info.metadata.artist))
        return response_builder.response

    @staticmethod
    def stop(handler_input: HandlerInput) -> Response:
        playback_info = Attributes.get_playback_info(handler_input)
        playback_info['in_playback_session'] = False

        handler_input.response_builder.add_directive(StopDirective())
        return handler_input.response_builder.response
    
    @staticmethod
    def pause(handler_input: HandlerInput) -> Response:
        return Controller.stop(handler_input)

    
    @staticmethod
    def resume(handler_input: HandlerInput, is_playback=False) -> Response:
        playback_info = Attributes.get_playback_info(handler_input)
        playback_info["next_stream_enqueued"] = False

        metadata = Attributes.get_metadata_by_play_order(handler_input)
        if playback_info.get('stream_url') and metadata: stream = player_models.Stream(playback_info.get('stream_url'))
        else: 
            stream, error = Api.get_stream(handler_input, metadata.video_id)
            if error: return handler_input.response_builder.speak(str(error)).response
        song_info = player_models.SongInfo(metadata, stream)

        return Controller.play(handler_input, song_info, is_playback=is_playback)

    @staticmethod
    def play_next(handler_input: HandlerInput, is_playback=False) -> Response:
        playlist = Attributes.get_playlist(handler_input)
        playback_info = Attributes.get_playback_info(handler_input)
        playback_setting = Attributes.get_playback_setting(handler_input)
        next_index = (playback_info.get("index") + 1) % len(playlist)

        if next_index == 0 and not playback_setting.get("loop"):
            if not is_playback:
                handler_input.response_builder.speak(data.PLAYBACK_NEXT_END)

            return handler_input.response_builder.add_directive(
                StopDirective()).response

        playback_info["index"] = next_index
        playback_info["offset_in_ms"] = 0
        playback_info["next_stream_enqueued"] = False

        metadata = Attributes.get_metadata_by_play_order(handler_input)
        stream, error = Api.get_stream(handler_input, metadata.video_id)
        if error: return handler_input.response_builder.speak(str(error)).response
        song_info = player_models.SongInfo(metadata, stream)

        return Controller.play(handler_input, song_info, is_playback=is_playback)

    @staticmethod
    def play_previous(handler_input: HandlerInput, is_playback=False) -> Response:
        playlist = Attributes.get_playlist(handler_input)
        playback_info = Attributes.get_playback_info(handler_input)
        playback_setting = Attributes.get_playback_setting(handler_input)
        prev_index = playback_info.get("index") - 1

        if prev_index == -1:
            if playback_setting.get("loop"):
                prev_index += len(playlist)
            else:
                if not is_playback:
                    handler_input.response_builder.speak(
                        data.PLAYBACK_PREVIOUS_END)

                return handler_input.response_builder.add_directive(
                    StopDirective()).response

        playback_info["index"] = prev_index
        playback_info["offset_in_ms"] = 0
        playback_info["next_stream_enqueued"] = False

        metadata = Attributes.get_metadata_by_play_order(handler_input)
        stream, error = Api.get_stream(handler_input, metadata.video_id)
        if error: return handler_input.response_builder.speak(str(error)).response
        song_info = player_models.SongInfo(metadata, stream)

        return Controller.play(handler_input, song_info, is_playback=is_playback)



# def play(url, token, offset, response_builder, text=None, card_data=None):
#     """Function to play audio.

#     Using the function to begin playing audio when:
#         - Play Audio Intent is invoked.
#         - Resuming audio when stopped / paused.
#         - Next / Previous commands issues.

#     https://developer.amazon.com/docs/custom-skills/audioplayer-interface-reference.html#play
#     REPLACE_ALL: Immediately begin playback of the specified stream,
#     and replace current and enqueued streams.
#     """
#     # type: (str, int, str, Dict, ResponseFactory) -> Response
#     if card_data:
#         response_builder.set_card(
#             StandardCard(
#                 title=card_data["title"], text=card_data["text"],
#                 image=Image(
#                     small_image_url=card_data["small_image_url"],
#                     large_image_url=card_data["large_image_url"])
#             )
#         )

#     # Using URL as token as they are all unique
#     response_builder.add_directive(
#         PlayDirective(
#             play_behavior=PlayBehavior.REPLACE_ALL,
#             audio_item=AudioItem(
#                 stream=Stream(
#                     token=token,
#                     url=url,
#                     offset_in_milliseconds=offset,
#                     expected_previous_token=None),
#                 metadata=add_screen_background(card_data) if card_data else None
#             )
#         )
#     ).set_should_end_session(True)

#     if text:
#         response_builder.speak(text)

#     return response_builder.response

# def play_later(url, card_data, response_builder):
#     """Play the stream later.

#     https://developer.amazon.com/docs/custom-skills/audioplayer-interface-reference.html#play
#     REPLACE_ENQUEUED: Replace all streams in the queue. This does not impact the currently playing stream.
#     """
#     # type: (str, Dict, ResponseFactory) -> Response
#     if card_data:
#         # Using URL as token as they are all unique
#         response_builder.add_directive(
#             PlayDirective(
#                 play_behavior=PlayBehavior.REPLACE_ENQUEUED,
#                 audio_item=AudioItem(
#                     stream=Stream(
#                         token=url,
#                         url=url,
#                         offset_in_milliseconds=0,
#                         expected_previous_token=None),
#                     metadata=add_screen_background(card_data)))
#         ).set_should_end_session(True)

#         return response_builder.response

# def stop(text, response_builder):
#     """Issue stop directive to stop the audio.

#     Issuing AudioPlayer.Stop directive to stop the audio.
#     Attributes already stored when AudioPlayer.Stopped request received.
#     """
#     # type: (str, ResponseFactory) -> Response
#     response_builder.add_directive(StopDirective())
#     if text:
#         response_builder.speak(text)

#     return response_builder.response

# def clear(response_builder):
#     """Clear the queue amd stop the player."""
#     # type: (ResponseFactory) -> Response
#     response_builder.add_directive(ClearQueueDirective(
#         clear_behavior=ClearBehavior.CLEAR_ENQUEUED))
#     return response_builder.response
