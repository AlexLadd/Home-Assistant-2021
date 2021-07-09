
from base_app import BaseApp
import datetime
import random
import requests
import json
import concurrent
import random
 

# TODO: 
#   - Should get_sanitized_speakers() be used in play_song()? (see option below, get_sanitized_speakers() is not currently being used)

MORNING_SONG_PATH = '/conf/apps/media/morning_songs.txt'
SPOTIFY_MEDIA_PLAYER = 'media_player.spotify_ha'


class SpotifyEngine(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.mp = self.get_app('speakers')
    self.sc = self.get_app('spotify_client')

    self.handle_songs = {}
    self.handle_cancel_songs = {}
    self.morning_songs = []


  def _map_song(self, song, num_tracks=1):
    if isinstance(song, list):
      return song
    elif song in ['both']:
      fns = [self._get_alex_song, self._get_steph_song]
      return random.choice(fns)(num_tracks=num_tracks)
    elif song in ['steph']:
      return self._get_steph_song(num_tracks=num_tracks)
    elif song in ['alex']:
      return self._get_alex_song(num_tracks=num_tracks)
    else:
      return song


  def _get_alex_song(self, num_tracks=1):
    artists = ['blink 182', 'Pink Floyd', 'radiohead', 'led zeppelin']
    track = self.sc.get_recommendation( { 'artist':random.choice(artists), 'random_search':'Yes', 'tracks':num_tracks } )
    return track

  def play_random_alex(self, media_player, volume=None, speaker_override=False):
    track = self._get_alex_song()
    self.play_song(track, media_player, volume, speaker_override)

  def _get_steph_song(self, num_tracks=1):
    track = self.sc.get_recommendation( { 'playlist':"Stephanie' s songs", 'username':'steph', 'random_search':True, 'tracks':num_tracks } )
    return track

  def play_random_steph(self, media_player, volume=None, speaker_override=False):
    track = self._get_steph_song()
    self.play_song(track, media_player, volume, speaker_override)


  def play_song(self, song, media_player, volume=None, speaker_override=False, offset=0, repeat=False, shuffle=True, random_song=True):
    """ Top level call - Prevent the thread from being held up by the long spotify play call """
    self.run_in(lambda *_: self._play_song(song, media_player, volume, speaker_override, offset, repeat, shuffle, random_song), 0)

  def _play_song(self, song, media_player, volume=None, speaker_override=False, offset=0, repeat=False, shuffle=True, random_song=True):
    """ 
    Core method to play spotify song on a given media_player 
    param song: Spotify song uri or a dictionary used to make a recommendation
    param speaker_override: Play music on speaker even if it is in use
    param offset: int, Provide offset as an int or track uri to start playback at a particular offset.
    param repeat: string, repeat mode such at 'track', 'etc'
    param shuffle: boolean, set playlist or album shuffle to on/off
    param random_song: boolean, start album or playlist at a random part
    """
    entity_id = self.mp.map_speaker_to_entity(media_player)
    if not entity_id or not self.mp.validate_media_players(entity_id):
      self._logger.log('Invalid spekaer: "{}", no song will play.'.format(media_player), level='ERROR')
      return
    if (self.mp.is_playing(entity_id) or self.sc.active_device_entity_id == entity_id) and not speaker_override:
      self._logger.log('["{}"] ("{}") Speaker is in use, the spotify song ("{}") will not play. Use speaker_override=True to skip this.'.format(media_player, entity_id, song), level='INFO')
      return

    if isinstance(song, dict):
      song = self.sc.get_recommendation(song)
      # self._logger.log('Song recommendation: {}'.format(song))
    else:
      song = self._map_song(song)

    # Cannot play lists of song using spotcast like our old system
    if isinstance(song, list):
      if offset and offset < len(song):
        song = song[offset]
      elif random_song:
        song = song[random.randint(0,len(song)-1)]
      else:
        song = song[0]
    elif song is None or song == '':
      self._logger.log(f'No song was passed in: {song}')
      return

    # Spotify song volume is loader than TTS
    vol = volume if volume else self.mp.default_volume(entity_id)
    self.mp.set_volume(entity_id, vol) 
    # self.sc.play(entity_id, song, offset)
    song_info = self.sc.get_track_info(song)
    self._logger.log(f'Using Spotcast to play Spotify media_player: {entity_id}, track info: {song_info}, offset: {offset}, repeat: {repeat}, shuffle: {shuffle}, random_song: {random_song}')
    try:
      self.call_service('spotcast/start', entity_id=entity_id, uri=song, offset=offset, repeat=repeat, shuffle=shuffle, random_song=random_song)
    except concurrent.futures._base.TimeoutError:
      self._logger.log(f'Getting the usual spotcast timeout error...')


  def stop_music(self):
    """ Stop the Spotify music if it was playing 
    This actually pauses it behind the scenes so that it remains active for a while 
    """
    speaker = self.sc.active_device
    if speaker is not None:
      self._logger.log(f'Music was playing on the "{speaker.lower()}", stopping music now.')
      self.sc.pause()


  def resume_music(self):
    """ Resume Spotify music on the previous speaker it was playing on if Spotify is currently active """
    speaker = self.sc.active_device
    if speaker is not None:
      self._logger.log(f'Resuming music on the "{speaker.lower()}" now.')
      self.sc.resume()


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing spotify_engine Module: ')

    device_name = 'master_bedroom_speaker'
    # device_name = 'media_player.d5739709_de9b747a'
    uri = 'spotify:album:1ohdh4vzVUXhtaE04cHvle'
    uri = {'artist':'blink 182'}
    rng_start = True

    # self.call_service('spotcast/start', device_name=device_name, uri=uri, random_song=rng_start)

    # self.play_song(uri, media_player=device_name, random_song=True, speaker_override=True)
    # self.play_random_steph(device_name)
    self.play_random_alex(device_name)

    # services = self.list_services()
    # self._logger.log(f'Services: {services}')
    # self._logger.log(f'Spotcast search: {"spotcast" in services}')

    # for s in services:
    #   if 'spot' in s.get('domain', ''):
    #     self._logger.log(f'Found spot service: {s}')
    #     break
    #   elif 'start' in s.get('service', ''):
    #     self._logger.log(f'Found a "start" service: {s}')
    #   else:
    #     self._logger.log(f'Did not find anything: {s}')

    # song_dict = {
    #   'device':'office', 
    #   'artist':'blink 182', 
    #   'random_search':True, 
    #   'tracks':5,
    # }
    # self.play_song(song_dict, 'study', speaker_override=True)

    # self.play_song(song_dict, 'study', speaker_override=True)
    # self.play_random_steph('master', speaker_override=True)
    # self._logger.log(f'Playing music using {song_dict}')

    # song_data = {}
    # song_data = {'album':'spotify:album:1ohdh4vzVUXhtaE04cHvle', 'random_start':'True'} # Pentatonix  
    # song_data = {'track':"How Far I'll Go", 'multiple':'on', 'random_start':True, 'similar':True} 
    # song_data = {'track':"How Far I'll Go"} 
    # song = self.sc.get_recommendation(song_data)

    # song = 'spotify:track:2374M0fQpWi3dLnB54qaLX'
    # self._logger.log(f'Attempting to play "{song}" derived from {song_data}.')
    # self.play_song(song, 'master', speaker_override=True)


  def terminate(self):
    pass



