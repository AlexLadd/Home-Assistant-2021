
"""
ONly core functionality added here
"""

from base_app import BaseApp 
import datetime
import threading
import re

# TODO:

# Default and fallbacks/failsafes
DAY_START = '03:30:00'
DAY_END = '15:00:00'
DEFAULT_ALEX_WAKEUP_TIME = '08:00:00'
DEFAULT_STEPH_WAKEUP_TIME = '07:57:00'
SECURITY_MONITORING_FREQUENCY = 10*60

ALEX_MORNING_GREETING_BOOLEAN = 'input_boolean.alex_morning_greeting_complete_today'
STEPH_MORNING_GREETING_BOOLEAN = 'input_boolean.steph_morning_greeting_complete_today'

NOTIFY_TARGET = 'everyone'
NOTIFY_TITLE = 'Good Morning'

ASLEEP_TURN_OFF_ENTITIES = [
  'master_bedroom_fan',
  'master_closet',
  'master_bathroom_ceiling',
  'master_bathroom_tub',
  'alex_master_lamp',
  'steph_master_lamp',
  'study',
]


class AwakeAsleepController(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.sleep = self.get_app('sleep')
    self.presence = self.get_app('presence')
    self.climate = self.get_app('climate')
    self.notifier = self.get_app('notifier')
    self.lights = self.get_app('lights')
    self.sm = self.get_app('security')
    # self.messages = self.get_app('messages')
    self.se = self.get_app('spotify_engine')

    self._sleep_lock = threading.Lock()       

    # Set alex/steph awake at hardcoded time (A failsafe of sorts - also leaving the house will set awake if not already awake)
    self.run_daily(self._timed_wakeup, self.parse_time(DEFAULT_STEPH_WAKEUP_TIME), steph=True)
    self.run_daily(self._timed_wakeup, self.parse_time(DEFAULT_ALEX_WAKEUP_TIME), alex=True)

    # Track alex/steph individually
    self.listen_state(self._sleep_state_change, self.const.ALEX_AWAKE_BOOLEAN) 
    self.listen_state(self._sleep_state_change, self.const.STEPH_AWAKE_BOOLEAN) 

    # Track first/last person asleep
    self.listen_state(lambda *_: self._first_person_asleep(), self.const.EVERYONE_AWAKE_BOOLEAN, old='on', new='off')
    self.listen_state(lambda *_: self._last_person_asleep(), self.const.EVERYONE_ASLEEP_BOOLEAN, old='off', new='on')
    # Track first/last person awake
    self.listen_state(lambda *_: self._first_person_awake(), self.const.EVERYONE_ASLEEP_BOOLEAN, old='on', new='off')
    self.listen_state(lambda *_: self._last_person_awake(), self.const.EVERYONE_AWAKE_BOOLEAN, old='off', new='on')


  def _first_person_asleep(self):
    self._logger.log('First person asleep.')

    for entity in ASLEEP_TURN_OFF_ENTITIES:
      self.lights.turn_light_off(entity, override=True)


  def _last_person_asleep(self):
    self._logger.log('Last person asleep, everyone is asleep.')
    self.lights.turn_all_off() # Use this until security manager is setup
    self.sm.lockdown_house()
    self.sm.start_security_monitoring(frequency=SECURITY_MONITORING_FREQUENCY)
    self.run_in(self._just_asleep_check, 45) # Give time for lockdown to complete before checking


  def _just_asleep_check(self, kwargs):
    """ Check that house is secure when everyone asleep and notify if it is not """
    msg = ''
    # if self.presence.guest_mode:
    #   msg = 'Guest mode is turned on. Only a partial house lockdown was done.'
    # else:
    #   unsecure_entities = self.sm.get_unsecure_entities(light_check=False, window_check=False, door_check=False)
    #   if unsecure_entities:
    #     msg = unsecure_entities + ' Please have a look before going to sleep.'

    if msg:
      msg += ' Good night.'
    else:
      msg = 'Good night. This is needs to be completed.'
    self.notifier.tts_notify(msg, 'master', volume=28, speaker_override=True, no_greeting=True)
    self._logger.log(msg)


  def _first_person_awake(self):
    self._logger.log('First person awake.')
    self.sm.stop_security_monitoring()


  def _last_person_awake(self):
    self._logger.log('Last person awake, everyone is awake.')

    if self.now_is_between(DAY_START, DAY_END):
      # Only run this during the day (prevents accidental message when toggling of awake/asleep)
      # msg = self.messages.build_message(
      #   holiday_check=True,
      #   garbage_check=True,
      #   water_cactus=True,
      #   wind_check=True,
      #   outside_weather=True, 
      #   uv_check=True,
      #   inspirational_quote=True,
      # )

      msg = f'Good morning. The forecast today is {self.climate.day_forecast}. Have a good day!'
      self.notifier.tts_notify(msg) # Use all idle media_players

      alex_complete = self.get_state(ALEX_MORNING_GREETING_BOOLEAN) == 'on'
      steph_complete = self.get_state(STEPH_MORNING_GREETING_BOOLEAN) == 'on'
      if not alex_complete and not steph_complete:
        song = 'steph'
      elif not steph_complete:
        song = 'steph'
      elif not alex_complete:
        song = 'alex'
      else:
        song = 'both'

      self.turn_on(ALEX_MORNING_GREETING_BOOLEAN)
      self.turn_on(STEPH_MORNING_GREETING_BOOLEAN)

      day = res = datetime.datetime.now().day
      month = datetime.datetime.now().month
      if month == 12 and 23 <= day <= 25:
        # Christmas songs
        song = {'album':'spotify:album:1ohdh4vzVUXhtaE04cHvle', 'random_search':'True', 'tracks':3} # Pentatonix
        self.listen_state(lambda *_: self.se.play_song(song, 'master'), 'media_player.master_bedroom_speaker', old='playing', new='idle', timeout=10*60, oneshot=True)
      else:
        # Play morning song after waiting for message to finish on speaker (Will cancel listener after 10 minutes & will only fire once if successful)
        self.listen_state(lambda *_: self.se.play_song(self.se._map_song(song, 3), 'master', ), 'media_player.master_bedroom_speaker', old='playing', new='idle', timeout=10*60, oneshot=True)


  def _morning_notify(self, target):
    self.notifier.telegram_notify(f'Good morning {target}', 'logging', 'Morning Message')


  def _sleep_state_change(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new):
      with self._sleep_lock:
        # Ensure proper execution when both Alex & Steph toggled at same time
        self.sleep.sync_everyone_states()
        if entity == self.const.ALEX_AWAKE_BOOLEAN:
          self._person_state_change('alex', new)
        elif entity == self.const.STEPH_AWAKE_BOOLEAN:
          self._person_state_change('steph', new)


  def _person_state_change(self, person, state):
    if state == 'on': # awake
      self._logger.log(f'{person.title()} is awake.')
      self.sm.disarm_security_system()
      if self.now_is_between(DAY_START, DAY_END):
        self._morning_notify(person.lower())
    elif state == 'off': # asleep
      self._logger.log(f'{person.title()} is asleep.')


  def _timed_wakeup(self, kwargs):
    """ Callback for programmed wakeup times """
    if 'alex' in kwargs:
      if self.sleep.alex_asleep:
        self._logger.log('Alex set awake override')
        self.sleep.set_alex('awake')
    elif 'steph' in kwargs:
      if self.sleep.steph_asleep:
        self._logger.log('Steph set awake override')
        self.sleep.set_steph('awake')


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing sleep_controller Module: ')

    for entity in ASLEEP_TURN_OFF_ENTITIES:
      self._logger.log(f'Trying to turn off {entity} using override=True')
      self.lights.turn_light_off(entity, override=True)


  def terminate(self):
    pass