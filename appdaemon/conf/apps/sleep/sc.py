
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

NOTIFY_TARGET = 'everyone'
NOTIFY_TITLE = 'Sleep Controller'

ASLEEP_TURN_OFF_ENTITIES = [
  'master_bedroom_fan',
  # 'master_closet',
  # 'master_bathroom_ceiling',
  # 'master_bathroom_tub',
  'alex_master_lamp',
  'steph_master_lamp',
  # 'study',
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
    self.messages = self.get_app('messages')
    self.se = self.get_app('spotify_engine')
    self.cat_water_dish = self.get_app('cat_water_dish')

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

    msg = self.messages.climate_check()

    # climate_check should catch this but keeping it here for now as a fallback
    if self.climate.todays_low <= 0 and self.messages.entry_point_check() != "All doors and windows are closed.":
      msg += f' The overnight low is {self.climate.todays_low} and {self.messages.entry_point_check().lower()}'
      self.climate.outside_tem

    if msg:
      msg += ' Good night.'
      msg = self.utils.one_space(msg)
      self.notifier.tts_notify(msg, 'master', volume=35, speaker_override=True)


  def _last_person_asleep(self):
    self._logger.log('Last person asleep, everyone is asleep.')
    self.cat_water_dish.turn_relay_off()
    self.lights.turn_all_off() # Use this until security manager is setup
    self.sm.lockdown_house()
    self.sm.start_security_monitoring(frequency=SECURITY_MONITORING_FREQUENCY)
    self.run_in(self._just_asleep_check, 45) # Give time for lockdown to complete before checking


  def _just_asleep_check(self, kwargs):
    """ Check that house is secure when everyone asleep and notify if it is not """
    msg = ''
    if self.presence.guest_mode:
      msg = 'Guest mode is turned on. Only a partial house lockdown was done.'
    else:
      unsecure_entities = self.sm.get_unsecure_entities(light_check=False, window_check=False, door_check=False)
      if unsecure_entities:
        msg = unsecure_entities + ' Please have a look before going to sleep.'

    if msg:
      msg += ' Good night.'
      self.notifier.tts_notify(msg, 'master', volume=28, speaker_override=True, no_greeting=True)
      self._logger.log(msg)


  def _first_person_awake(self):
    self._logger.log('First person awake.')
    self.cat_water_dish.turn_relay_on()
    self.sm.stop_security_monitoring()


  def _last_person_awake(self):
    self._logger.log('Last person awake, everyone is awake.')

    if self.now_is_between(DAY_START, DAY_END):
      # Only run this during the day (prevents accidental message when toggling of awake/asleep)
      msg = self.messages.build_message(
        holiday_check=True,
        # garbage_check=True,
        water_cactus=True,
        wind_check=True,
        outside_weather=True, 
        uv_check=True,
        inspirational_quote=True,
      )

      self.notifier.tts_notify(msg) # Use all idle media_players

      alex_complete = self.get_state(self.const.ALEX_MORNING_GREETING_BOOLEAN) == 'on'
      steph_complete = self.get_state(self.const.STEPH_MORNING_GREETING_BOOLEAN) == 'on'
      if not alex_complete and not steph_complete:
        song = 'steph'
      elif not steph_complete:
        song = 'steph'
      elif not alex_complete:
        song = 'alex'
      else:
        song = 'both'

      self.turn_on(self.const.ALEX_MORNING_GREETING_BOOLEAN)
      self.turn_on(self.const.STEPH_MORNING_GREETING_BOOLEAN)

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
    # self.notifier.telegram_notify(f'Good morning {target}', 'logging', 'Morning Message')
    msg = self.messages.build_message(
      holiday_check=True,
      # garbage_check=True,
      outside_weather=True,
      water_cactus=True,
      wind_check=True,
      # fd_battery_check=True,
      epson_ink_check= True,
    )

    if msg:
      msg = f'Good morning {target.title()}. {self.utils.one_space(msg)}'
      self.notifier.telegram_notify(msg, target, NOTIFY_TITLE)


  def _night_notify(self, target):
    msg = self.messages.household_boolean_check()
    if msg:
      msg = f'{self.utils.one_space(msg)}. Good night {target}.'
      self.notifier.telegram_notify(msg, target, NOTIFY_TITLE)


  def _sleep_state_change(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new):
      with self._sleep_lock:
        # Ensure proper execution when both Alex & Steph toggled at same time
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
      if self.now_is_between(DAY_END, DAY_START):
        self._night_notify(person.lower())


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