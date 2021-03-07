
from base_app import BaseApp
import datetime
import threading

# TODO: 
#   - Add repatition option to tts messages?
#   - TTS & Spotify engine both individually control speakers - Try joining them so we don't end up with conflicts

class TTS(BaseApp):

  def setup(self):
    # self.listen_state(self.test,'input_boolean.ad_testing_2')

    self.sleep = self.get_app('sleep')
    self.mp = self.get_app('speakers')
    self.messages = self.get_app('messages')
    self.sc = self.get_app('spotify_client')

    self.debug_level = 'DEBUG'
    self.tts_playing = False                # TTS announcement is playing
    self.spotify_paused = False             # Spotify song paused for TTS
    self.previous_spotify_volume = 0        # Previous Spotify speaker volume level
    self.tts_messages = []                  # List of queued TTS messages as dictionaries
    self.tts_lock = threading.Lock()        # TTS lock
    
    # Schedule TTS Cache cleanup every sunday at 4AM
    dt = datetime.datetime.combine(self.date(), datetime.time(4, 00))
    if dt - self.datetime() > datetime.timedelta(seconds=1):
      dt += datetime.timedelta(days = 6 - dt.weekday()) # Get the next sunday
    else:
      # It is currently Sunday and past 4AM - Schedule for next Sunday
      dt += datetime.timedelta(days = 7 + 6 - dt.weekday()) # Get the next sunday
    self.run_every(lambda *_: self._clear_tts_cache(), dt, 24*60*60*7) # Cleanup file every sunday at 4AM


  @property
  def tts_is_playing(self):
    """ Is a TTS message currently playing """
    return self.tts_playing


  def tts_notify(self, message, media_player=None, volume=None, speaker_override=False, no_greeting=False, options={}):
    """
    param message: The message to say
    param media_player: The speaker to use [Default: Use idle media_players depending of sleep state]
    param volume: The speaker volume [Default: Use media_player app default volume for each speaker]
    param speaker_override: Will use speaker even if currently in use - will also force the speaker to be used even if everyone asleep for example
    param no_greeting: Will not append the time of day greeting to message
    param options: The google tts options (gender, voice, encoding, speed, pitch, gain, profiles)
    """
    emergency = self.get_state(self.const.EMERGENCY_MODE_BOOLEAN) == 'on'
    speech_mode = self.get_state(self.const.SPEECH_OVERRIDE_BOOLEAN) == 'on'
    # valid_hour = (self.sleep.someone_awake or 8 < datetime.datetime.now().hour < 21)
    # This verson takes into account that someone may be away and set 'awake' since they are not home to be 'asleep'
    valid_hour = (self.sleep.everyone_awake or (self.everyone_home() and self.sleep.someone_awake) or self.now_is_between(self.const.DEFAULT_WAKEUP, self.const.DEFAULT_ASLEEP))
    someone_home = (self.anyone_home() or self.get_state(self.const.GUEST_MODE_BOOLEAN) == 'on')

    # if emergency or (speech_mode and valid_hour and someone_home):
    if not (speech_mode and valid_hour and someone_home) and not speaker_override:
      if not emergency:
        self._logger.log('TTS is disabled, the message ("{}") was ignored.'.format(message))
        return
        
    with self.tts_lock:
      if self.tts_playing:
        self._logger.log('TTS is currently playing. Message saved for later.')
        msg = {
          'message' : message,
          'media_player' : media_player,
          'volume' : volume,
          'speaker_override' : speaker_override,
          'no_greeting' : no_greeting,
          'options' : options
        }
        self.tts_messages.append(msg)
        return
      else:
        self.tts_playing = True

    speakers = self.mp.get_sanitized_speakers(speaker=media_player, speaker_override=speaker_override, use_groups=False)
    if not no_greeting:
      message = self.messages.greeting() + message
    _message = '<speak> ' + message + ' </speak>'
    
    # If spotify is currently playing take a snapshot
    if self.sc.state == 'playing' and not self.spotify_paused: # OR try self.sc.progress_ms_remaining > 0
      active_sc_mp = self.sc.active_device_entity_id
      if active_sc_mp in speakers:
        self.sc.take_playback_snapshot()
        self.sc.pause()
        self.spotify_paused = True
        self.active_sc_mp = active_sc_mp
        self._logger.log(f'TTS snapshot spotify. Active speaker: {active_sc_mp}.')

    self.mp.set_volume(speakers, volume)
    self.call_service('tts/google_say', entity_id=speakers, message=_message, options=options) 
    self._logger.log(f'Notifying via Google TTS: "{message}" said on "{", ".join(speakers)}"')
    self.run_in(self._on_tts_pre_finished, 5, speakers=speakers)


  def _on_tts_pre_finished(self, kwargs):
    """ Determine when TTS will be done on speaker using media_duration attribute """
    try:
      speaker = kwargs['speakers'][0]
    except:
      # No speaker was used for the TTS
      self._logger.log('No speaker was used for the previous TTS message!', level='WARNING')
      self._on_tts_finished(None)
      return

    duration = self.get_state(str(speaker), attribute="media_duration")
    if not duration:
      self._logger.log(f'Could not calculate duration for TTS. Current speaker state: {self.get_state(str(speaker), attribute="all")}', level='WARNING')
      self._on_tts_finished(None)
      return

    # self._logger.log('Speakers: {} have a remaining TTS duration of {}.'.format(kwargs['speakers'], duration-5))
    d = duration if duration > 0 else 1
    self.run_in(self._on_tts_finished, d, speakers=kwargs['speakers'])


  def _on_tts_finished(self, kwargs):
    """ TTS is finished """
    # self._logger.log('TTS should now be finished.')
    message = None
    with self.tts_lock:
      self.tts_playing = False
      if len(self.tts_messages) > 0:
        message = self.tts_messages.pop(0)

    if message:
      self.tts_notify(message['message'], message['media_player'], message['volume'], message['speaker_override'], message['no_greeting'], message['options'])
      # self.tts_notify(message['message'], **message) # Untested but should work if 'message' key removed first
    else:
      if self.spotify_paused:
        # self.sc.restore_playback_from_snapshot()
        self.spotify_paused = False
        self.mp.set_volume(self.active_sc_mp, self.mp.default_volume(self.active_sc_mp)*0.65)


  def _clear_tts_cache(self):
    self.call_service('tts/clear_cache') 
    self._logger.log(f'Cleared TTS cache.', level='INFO')


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing TTS Module: ')
    self._clear_tts_cache()

  def terminate(self):
    pass
