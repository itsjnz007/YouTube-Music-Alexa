import logging, os, boto3, data, re
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler, AbstractResponseInterceptor, AbstractRequestInterceptor
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model.interfaces.audioplayer import PlayDirective, PlayBehavior, AudioItem, Stream
from ask_sdk_dynamodb.adapter import DynamoDbAdapter
from ask_sdk_model import Response
from mediaUtils import player
from dataclasses import asdict
from models import player_models

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ddb_region = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
ddb_table_name = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')
ddb_resource = boto3.resource('dynamodb', region_name=ddb_region)
dynamodb_adapter = DynamoDbAdapter(table_name=ddb_table_name, create_table=False, dynamodb_resource=ddb_resource)

sb = CustomSkillBuilder(persistence_adapter = dynamodb_adapter, api_client=DefaultApiClient())

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In LaunchRequestHandler")
        speak_output = "This is your d. j. Say 'help' to know how I can help."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
    
class PlaySongIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput):
        return ask_utils.is_intent_name("PlaySongIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput):
        logger.info("In PlaySongIntentHandler")
        slots = handler_input.request_envelope.request.intent.slots
        song_name = slots['songName'].value

        
        # Check if the said song is actually a playlist
        playlist_name = player.Attributes.match_playlist_name(handler_input, song_name)
        if playlist_name: 
            playlist = player.Attributes.get_from_saved_playlists(handler_input, playlist_name)
            if playlist: 
                player.send_progressive_response(handler_input, f'Starting playlist {playlist_name}.')
                return player.Controller.fetch(handler_input, playlist_id=playlist.id)
            
        player.send_progressive_response(handler_input, 'Searching...')
        return player.Controller.fetch(
            handler_input=handler_input, 
            query=song_name,
            filter=player_models.Filter.SONGS,
            is_playback=False
        )
    
class PlayArtistIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput):
        return ask_utils.is_intent_name("PlayArtistIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput):
        logger.info("In PlayArtistIntentHandler")
        slots = handler_input.request_envelope.request.intent.slots
        query = slots.get('artistName').value
        if not query: return handler_input.response_builder.speak('For artists, say, "Alexa, ask DJ to play song by The Weekend"').response
        player.send_progressive_response(handler_input, 'Searching artist...')
        return player.Controller.fetch(
            handler_input=handler_input, 
            query=query,
            filter=player_models.Filter.ARTISTS,
            is_playback=False
        )
    
class PlayAlbumIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput):
        return ask_utils.is_intent_name("PlayAlbumIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput):
        logger.info("In PlaySongIntentHandler")
        slots = handler_input.request_envelope.request.intent.slots
        query = slots.get('albumName').value
        if not query: return handler_input.response_builder.speak('For albums, say, "Alexa, ask DJ to play album Thriller"').response
        player.send_progressive_response(handler_input, 'Searching album...')
        return player.Controller.fetch(
            handler_input=handler_input, 
            query=query,
            filter=player_models.Filter.ALBUMS,
            is_playback=False
        )
    
class StartPlaybackHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return (ask_utils.is_intent_name("AMAZON.ResumeIntent")(handler_input)
                or ask_utils.is_intent_name("PlayAudio")(handler_input))

    def handle(self, handler_input):
        logger.info("In StartPlaybackHandler")
        player.send_progressive_response(handler_input, 'Resuming...')
        return player.Controller.resume(handler_input=handler_input, is_playback=True)
    
class PausePlaybackHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_intent_name("AMAZON.PauseIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In PausePlaybackHandler")
        return player.Controller.pause(handler_input)
    
class StopPlaybackHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return (ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)
                     or ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input))

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In StopPlaybackHandler")
        return player.Controller.pause(handler_input)
    
class NextPlaybackHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.NextIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In NextPlaybackHandler")
        return player.Controller.play_next(handler_input, is_playback=player.Attributes.get_playback_info(handler_input).get('in_playback_session'))
    
class PreviousPlaybackHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.PreviousIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("In PreviousPlaybackHandler")
        return player.Controller.play_previous(handler_input, is_playback=player.Attributes.get_playback_info(handler_input).get('in_playback_session'))

class LoopOnHandler(AbstractRequestHandler):
    """Handler for setting the audio loop on."""
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_intent_name("AMAZON.LoopOnIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In LoopOnHandler")
        playback_setting = player.Attributes.get_playback_info(handler_input)
        playback_setting["loop"] = True

        return handler_input.response_builder.speak(data.LOOP_ON_MSG).response

class LoopOffHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_intent_name("AMAZON.LoopOffIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In LoopOffHandler")
        playback_setting = player.Attributes.get_playback_info(handler_input)
        playback_setting["loop"] = False

        return handler_input.response_builder.speak(data.LOOP_OFF_MSG).response

class ShuffleOnHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.ShuffleOnIntent")(handler_input)

    def handle(self, handler_input: HandlerInput):
        logger.info("In ShuffleOnHandler")
        playback_setting = player.Attributes.get_playback_setting(handler_input)

        playback_setting["shuffle"] = True
        player.Attributes.set_play_order(handler_input)
        return handler_input.response_builder.speak('Shuffle On').response

class ShuffleOffHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):

        return ask_utils.is_intent_name("AMAZON.ShuffleOffIntent")(handler_input)

    def handle(self, handler_input: HandlerInput):
        logger.info("In ShuffleOffHandler")
        playback_setting = player.Attributes.get_playback_setting(handler_input)

        playback_setting["shuffle"] = False
        player.Attributes.set_play_order(handler_input)

        return handler_input.response_builder.speak('Shuffle Off').response

class StartOverHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.StartOverIntent")(handler_input)

    def handle(self, handler_input: HandlerInput):
        logger.info("In StartOverHandler")
        playback_info = player.Attributes.get_playback_info(handler_input)
        playback_info["offset_in_ms"] = 0
        player.send_progressive_response(handler_input, 'Starting over...')
        # return player.Controller.fetch(
        #     handler_input=handler_input
        # )
        return handler_input.response_builder.speak('This feature is not available yet.').response
    
class AnnounceNowPlayingHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput):
        return ask_utils.is_intent_name("AnnounceNowPlayingIntent")(handler_input)

    def handle(self, handler_input: HandlerInput):
        logger.info("In AnnounceNowPlayingHandler")

        metadata = player.Attributes.get_metadata_by_play_order(handler_input)
        return handler_input.response_builder.speak(f'This is {metadata.title} by {metadata.artist}').response
    
class CreatePlaylistHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_intent_name("CreatePlaylistIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In CreatePlaylistHandler")

        slots = handler_input.request_envelope.request.intent.slots
        playlist_id_encoded = slots['encodedPlaylistId'].value

        logger.info(f'playlist_id_encoded -> {playlist_id_encoded}')

        if not playlist_id_encoded or re.search(r'[^a-zA-Z0-9]', playlist_id_encoded): 
            return handler_input.response_builder.speak(f'Please provide encoded url in hexadecimal format.').response

        playlist_id = player.decode_hex(playlist_id_encoded.lower())
        playlist, error = player.Api.get_playlist_info(handler_input, playlist_id)
        if error: return handler_input.response_builder.speak(str(error)).response
        playlist_name_original = playlist.title

        user_attr = player.Attributes.get_user_attributes(handler_input)
        if not user_attr.get('saved_playlists'): user_attr['saved_playlists'] = {}
        user_attr['saved_playlists'][playlist_name_original] = asdict(playlist)

        return handler_input.response_builder.speak(f'Playlist {playlist_name_original} saved.').response
    
class DeletePlaylistHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_intent_name("DeletePlaylistIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In DeletePlaylistHandler")

        slots = handler_input.request_envelope.request.intent.slots
        playlist_name = slots.get('playlistName').value

        if not playlist_name: return handler_input.response_builder.speak('Please provide playlist name.').response

        # fuzzy match on name to get key
        actual_playlist_name = player.Attributes.match_playlist_name(handler_input, playlist_name)

        user_attr = player.Attributes.get_user_attributes(handler_input)
        if actual_playlist_name in user_attr['saved_playlists']: user_attr['saved_playlists'].pop(actual_playlist_name.lower(), None)
        return handler_input.response_builder.speak(f'Playlist {actual_playlist_name} deleted.').response

class StartPlaylistHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_intent_name("StartPlaylistIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In StartPlaylistHandler")

        # player.send_progressive_response(handler_input, 'Searching...')
        slots = handler_input.request_envelope.request.intent.slots
        playlist_name = slots['playlistName'].value
        if not playlist_name: return handler_input.response_builder.speak('To play from saved playlists, say, "Alexa, ask DJ to play Favourites"').response
        
        # fuzzy match on name to get key
        actual_playlist_name = player.Attributes.match_playlist_name(handler_input, playlist_name)
        playlist = player.Attributes.get_from_saved_playlists(handler_input, actual_playlist_name)
        if not playlist: return handler_input.response_builder.speak(f'Could not find the playlist {playlist_name} in saved playlists.').response
        player.send_progressive_response(handler_input, f'Starting playlist {playlist_name}.')
        
        return player.Controller.fetch(handler_input, playlist_id=playlist.id)
    
class FindPlaylistHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_intent_name("FindPlaylistIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In FindPlaylistHandler")

        user_attr = player.Attributes.get_user_attributes(handler_input)
        saved_playlists = user_attr.get('saved_playlists')
        if saved_playlists: 
            to_string = ', '.join(list(saved_playlists.keys()))
            return handler_input.response_builder.speak(f'You have {to_string} in saved playlists.').response
        return handler_input.response_builder.speak(f'You do not have any playlists saved. To add playlists, say, "Alexa, ask DJ to add Playlist".').response
    
class SetApiurlHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_intent_name("SetApiurlIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("In SetApiurlHandler")

        slots = handler_input.request_envelope.request.intent.slots
        api_url = slots['apiUrl'].value

        logger.info(f'api_url -> {api_url}')
        if not api_url or re.search(r'[^a-zA-Z0-9]', api_url): 
            return handler_input.response_builder.speak(f'Please provide encoded url in hexadeximal format.').response
        api_url_decoded = player.decode_hex(api_url.lower())
        logger.info(f'api_url_decoded -> {api_url_decoded}')
        user_attr = player.Attributes.get_user_attributes(handler_input)
        user_attr['api_url'] = api_url_decoded
        return handler_input.response_builder.speak('Api url added.').response
# ###################################################################


# ########## Additional Helper HANDLERS #########################
# Contains some extra helpers

class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speak_output = "You can say 'Play Looks like me' or 'Ask DJ to play Looks like me'. You can add or delete playlists by saying 'Add playlist' or 'Delete playlist'. To access saved playlists, say 'Start playlist Favourites' or 'What are my playlists?' to find saved playlists."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input: HandlerInput) -> Response:
        speak_output = "Goodbye!"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. Try asking for help?"

        return handler_input.response_builder.speak(speech).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> Response:
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."
        logger.info(speak_output)

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask(speak_output)
                .response
        )
# ###################################################################

    
# ########## AUDIOPLAYER INTERFACE HANDLERS #########################
# This section contains handlers related to Audioplayer interface

class PlaybackStartedEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AudioPlayer.PlaybackStarted")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackStartedHandler")

        playback_info = player.Attributes.get_playback_info(handler_input)
        playback_info["index"] = player.Attributes.get_calculated_index(handler_input)
        playback_info["in_playback_session"] = True
        playback_info["has_previous_playback_session"] = True

        logger.info(f'playback_info -> {playback_info}')

        return handler_input.response_builder.response

class PlaybackFinishedEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AudioPlayer.PlaybackFinished")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackFinishedHandler")

        playback_info = player.Attributes.get_playback_info(handler_input)

        playback_info["in_playback_session"] = False
        playback_info["has_previous_playback_session"] = False
        playback_info["next_stream_enqueued"] = False

        return handler_input.response_builder.response


class PlaybackStoppedEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AudioPlayer.PlaybackStopped")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackStoppedHandler")

        playback_info = player.Attributes.get_playback_info(handler_input)
        # playback_info["index"] = player.Attributes.get_index(handler_input)
        playback_info["offset_in_ms"] = player.Attributes.get_offset_in_ms(
            handler_input)
        
        return handler_input.response_builder.response


class PlaybackNearlyFinishedEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("AudioPlayer.PlaybackNearlyFinished")(handler_input)

    def handle(self, handler_input: HandlerInput):
        logger.info("In PlaybackNearlyFinishedHandler")

        persistent_attr = handler_input.attributes_manager.persistent_attributes
        playback_info = player.Attributes.get_playback_info(handler_input)
        playlist = player.Attributes.get_playlist(handler_input)
        playback_setting = persistent_attr.get("playback_setting")

        if playback_info.get("next_stream_enqueued"):
            return handler_input.response_builder.response

        current_index = playback_info.get("index")
        enqueue_index = (current_index + 1) % len(playlist)

        if enqueue_index == 0 and not playback_setting.get("loop"):
            return handler_input.response_builder.response

        playback_info["next_stream_enqueued"] = True

        current_metadata = player.Attributes.get_metadata_by_play_order(handler_input, current_index)
        current_video_id = current_metadata.video_id

        enqueue_metadata = player.Attributes.get_metadata_by_play_order(handler_input, enqueue_index) # playlist[enqueue_index]
        enqueue_video_id = enqueue_metadata.video_id
        enqueue_stream, error = player.Api.get_stream(handler_input, enqueue_video_id)
        if error: return handler_input.response_builder.speak(str(error)).response

        # Log all attrubutes ----------------------------------
        player.Attributes.log_attributes(handler_input)
        # -----------------------------------------------------

        handler_input.response_builder.add_directive(
            PlayDirective(
                play_behavior=PlayBehavior.ENQUEUE,
                audio_item=AudioItem(
                    stream=Stream(
                        token=enqueue_video_id,
                        url=enqueue_stream.audio_url,
                        offset_in_milliseconds=0,
                        expected_previous_token=current_video_id),
                    metadata=player.Attributes.get_audio_item_metadata(enqueue_metadata))))
        
        logger.info(f'current_video_id -> {current_video_id}, enqueue_video_id -> {enqueue_video_id}, current_index -> {current_index}, enqueue_index -> {enqueue_index}')


        return handler_input.response_builder.response


class PlaybackFailedEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AudioPlayer.PlaybackFailed")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackFailedHandler")

        playback_info = player.Attributes.get_playback_info(handler_input)
        playback_info["in_playback_session"] = False

        logger.info("Playback Failed: {}".format(
            handler_input.request_envelope.request.error))

        return handler_input.response_builder.response

# ###################################################################
    

# ############# REQUEST / RESPONSE INTERCEPTORS #####################
class LogRequestInterceptor(AbstractRequestInterceptor):
    def process(self, handler_input: HandlerInput):
        logger.info(f"Request type: {handler_input.request_envelope.request.object_type}")

class LoadPersistenceAttributesRequestInterceptor(AbstractRequestInterceptor):
    def process(self, handler_input: HandlerInput):
        persistence_attr = handler_input.attributes_manager.persistent_attributes

        user_id = player.Attributes.get_user_id(handler_input)

        if not persistence_attr.get(user_id):
            persistence_attr[user_id] = {
                'playback_setting': {
                    "loop": False,
                    "shuffle": False
                },
                'playback_info': {
                    "play_order": [],
                    "index": 0,
                    "offset_in_ms": 0,
                    "next_stream_enqueued": False,
                    "in_playback_session": False,
                    "has_previous_playback_session": False,
                    "stream_url": None
                },
                'playlist': [],
                'saved_playlists': {},
                'api_url': None
            }

        else:
            # Convert decimals to integers, because of AWS SDK DynamoDB issue
            # https://github.com/boto/boto3/issues/369
            
            playback_info = player.Attributes.get_user_attributes(handler_input).get("playback_info")
            playback_info["index"] = int(playback_info.get("index", 0))
            playback_info["play_order"] = [int(i) for i in playback_info.get("play_order", [])]
            playback_info["offset_in_ms"] = int(playback_info.get("offset_in_ms", 0))

            playlist = player.Attributes.get_user_attributes(handler_input).get("playlist")
            for metadata in playlist:
                thumbnail = metadata['thumbnail']
                thumbnail['width'] = int(thumbnail['width'])  # Convert Decimal to int
                thumbnail['height'] = int(thumbnail['height'])  # Convert Decimal to int

class SavePersistenceAttributesResponseInterceptor(AbstractResponseInterceptor):
    def process(self, handler_input: HandlerInput, response):
        handler_input.attributes_manager.save_persistent_attributes()
# ###################################################################


sb.add_request_handler(LaunchRequestHandler())

sb.add_request_handler(PlayArtistIntentHandler())
sb.add_request_handler(PlayAlbumIntentHandler())

sb.add_request_handler(PlaySongIntentHandler())
sb.add_request_handler(StartPlaybackHandler())
sb.add_request_handler(PausePlaybackHandler())
sb.add_request_handler(StopPlaybackHandler())
sb.add_request_handler(NextPlaybackHandler())
sb.add_request_handler(PreviousPlaybackHandler())
sb.add_request_handler(LoopOnHandler())
sb.add_request_handler(LoopOffHandler())
sb.add_request_handler(ShuffleOnHandler())
sb.add_request_handler(ShuffleOffHandler())
sb.add_request_handler(StartOverHandler())
sb.add_request_handler(AnnounceNowPlayingHandler())
sb.add_request_handler(CreatePlaylistHandler())
sb.add_request_handler(DeletePlaylistHandler())
sb.add_request_handler(StartPlaylistHandler())
sb.add_request_handler(FindPlaylistHandler())
sb.add_request_handler(SetApiurlHandler())

# More handlers
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler())

# Interface handlers
sb.add_request_handler(PlaybackStartedEventHandler())
sb.add_request_handler(PlaybackFinishedEventHandler())
sb.add_request_handler(PlaybackStoppedEventHandler())
sb.add_request_handler(PlaybackNearlyFinishedEventHandler())
sb.add_request_handler(PlaybackFailedEventHandler())

# Exceptions
sb.add_global_request_interceptor(LogRequestInterceptor())
sb.add_exception_handler(CatchAllExceptionHandler())

# Interceptors
sb.add_global_request_interceptor(LoadPersistenceAttributesRequestInterceptor())
sb.add_global_response_interceptor(SavePersistenceAttributesResponseInterceptor())

lambda_handler = sb.lambda_handler()