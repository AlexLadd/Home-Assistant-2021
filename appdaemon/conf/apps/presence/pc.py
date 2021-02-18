
from base_app import BaseApp
import datetime
import threading

# TODO:
#   - Refactor (remove alex & steph away booleans and just use person now that they seem to be working as expected)
#   - Try using both_together boolean (and not changed within x seconds) to determine home together of refactor

ALEX_INPUT_SELECT = 'input_select.alex_status_dropdown'
STEPH_INPUT_SELECT = 'input_select.steph_status_dropdown'

# Leaving/Arriving transition time
TRANSITION_TIME = 20
EXTENDED_AWAY_TIME = 24*60*60
GREETING_SONG_TIMEOUT = 10*60
LIGHTS_ON_WHEN_HOME_TIME = 10*60

KITCHEN_DOOR_SENSOR = 'binary_sensor.kitchen_door_window_sensor'

NOTIFY_TARGET = 'alex'
NOTIFY_TITLE = 'Presence Controller'


class PC(BaseApp):

  def setup(self):
    # self.listen_state(self.test,'input_boolean.ad_testing_1')
    self.notifier = self.get_app('notifier')
    self.presence = self.get_app('presence')
    # self.alarm = self.get_app('alarm')
    self.dw = self.get_app('doors_windows')
    self.sleep = self.get_app('sleep')
    self.sm = self.get_app('security')
    self.se = self.get_app('spotify_engine')  
    self.lights = self.get_app('lights')

    self.home_lock = threading.Lock()
    self.away_lock = threading.Lock()

    self.handle_front_lights = None
    self.handle_alex_extended_away = None
    self.handle_steph_extended_away = None
    self.handle_one_home_alex = None
    self.handle_one_home_steph = None
    self.handle_one_left_alex = None
    self.handle_one_left_steph = None

    self.listen_state(self._alex_state_change, self.const.ALEX_PERSON)
    self.listen_state(self._steph_state_change, self.const.STEPH_PERSON)
    self.listen_state(self._occupancy_state_change, self.const.OCCUPANCY_BOOLEAN)
    # Allow for manual guest_mode toggling
    self.listen_state(self._guest_mode_state_change, self.const.GUEST_MODE_BOOLEAN)

    # Sync up on restart
    self.run_in(lambda *_: self._resync_states(), 1)
    


  def _resync_states(self):
    """ Verify that internal states are correctly synced up w/ currently Steph & Alex person state """
    # THIS CAN ALL BE REMOVED IS ONLY USING PERSONS (except for occupancy)
    if self.get_state(self.const.ALEX_PERSON) == 'home' and self.presence.alex_away:
      self.set_state(self.const.ALEX_AWAY_BOOLEAN, state='off')
    elif self.get_state(self.const.ALEX_PERSON) != 'home' and self.presence.alex_home:
      self.set_state(self.const.ALEX_AWAY_BOOLEAN, state='on')

    if self.get_state(self.const.STEPH_PERSON) == 'home' and self.presence.steph_away:
      self.set_state(self.const.STEPH_AWAY_BOOLEAN, state='off')
    elif self.get_state(self.const.STEPH_PERSON) != 'home' and self.presence.steph_home:
      self.set_state(self.const.STEPH_AWAY_BOOLEAN, state='on')

    # if self.anyone_home() and not self.presence.occupancy:
    if self.presence.someone_home and not self.presence.occupancy:
      self.presence.turn_on_occupancy()
    # elif self.noone_home() and self.presence.occupancy:
    elif not self.presence.someone_home and self.presence.occupancy:
      self.presence.turn_off_occupancy()


  def _first_person_home(self):
    """ Called when the first person arrives home
    Triggered when occupancy is switched 'off' -> 'on' 
    """
    self._logger.log('First person got home.', level='INFO')
    self.presence.turn_off_vacation_mode()


  def _play_greeting_song(self, song):
    """ Plays a Spotify song if the front door is opened before the timeout is reached """
    if self.sleep.everyone_awake or self.now_is_between(self.const.DEFAULT_WAKEUP, self.const.DEFAULT_ASLEEP):
      # self.se.play_song_on_event(song, 'family_room', FRONT_DOOR_SENSOR, old_state='off', new_state='on', timeout=GREETING_SONG_TIMEOUT)
      self.listen_state(lambda *_: self.se.play_song(self.se._map_song(song, 2), 'kitchen', ), self.dw.get_door_sensor('kitchen'), old='off', new='on', timeout=GREETING_SONG_TIMEOUT, oneshot=True)
    else:
      self._logger.log('Not playing a greeting song because it is too late or someone is sleeping.')


  def _single_person_home(self, kwargs):
    """ Alex or Steph got home individually """
    person = kwargs['person']
    self._logger.log('Single person arrived home: {}.'.format(person))
    self._play_greeting_song(person)
    setattr(self, 'handle_one_home_' + person, None)


  def _both_home_together(self):
    """ Alex & Steph got home together """
    self._logger.log('Both of us arrived home together.')
    self._play_greeting_song('both')


  def _someone_got_home(self):
    """ Called anytime anyone gets home (including a guest) """
    self._logger.log('Someone got home.')
    # self.alarm.disarm() # THIS SHOULD BE DONE IN SECURITY FOR CONSISTANCY!!!

    if self.dark_mode:
      self.cancel_timer(self.handle_front_lights)
      lts = ['outside_carport', 'kitchen_door']
      self.lights.turn_lights_on(lts)
      self.handle_front_lights = self.run_in(lambda *_: self.lights.turn_light_off(lts), LIGHTS_ON_WHEN_HOME_TIME)


  def _last_person_left_home(self):
    """ Called when the last person leaves home
    
    Triggered when occupancy is switched 'on' -> 'off' """
    self._logger.log('Last person left, nobody home.', level='INFO')
    # self.sm.lockdown_house()


  def _single_person_left(self, kwargs):
    """ Alex or Steph left home individually """
    person = kwargs['person']
    self._logger.log('Single person left home: {}.'.format(person))
    setattr(self, 'handle_one_left_' + person, None)


  def _both_left_together(self):
    """ Alex & Steph left home together """
    self._logger.log('Both of us left home together.')


  def _alex_got_home(self):
    self.select_option(ALEX_INPUT_SELECT, 'Home')
    self.cancel_timer(self.handle_alex_extended_away)
    self._someone_got_home()

    with self.home_lock:
      self._logger.log('Alex got home.', level='INFO')
      self.presence.turn_on_occupancy()

      if self.handle_one_home_steph is not None:
        # Steph just got home -> we got home together
        self.cancel_timer(self.handle_one_home_steph)
        self.handle_one_home_steph = None
        self._both_home_together()
      else:
        self.handle_one_home_alex = self.run_in(self._single_person_home, TRANSITION_TIME, person='alex')
      self.turn_off(self.const.ALEX_AWAY_BOOLEAN)


  def _steph_got_home(self):
    self.select_option(STEPH_INPUT_SELECT, 'Home')
    self.cancel_timer(self.handle_steph_extended_away)
    self._someone_got_home()

    with self.home_lock:
      self._logger.log('Steph got home.', level='INFO')
      self.presence.turn_on_occupancy()

      if self.handle_one_home_alex is not None:
        # Alex just got home -> we got home together
        self.cancel_timer(self.handle_one_home_alex)
        self.handle_one_home_alex = None
        self._both_home_together()
      else:
        self.handle_one_home_steph = self.run_in(self._single_person_home, TRANSITION_TIME, person='steph')
      self.turn_off(self.const.STEPH_AWAY_BOOLEAN)


  def _alex_left_home(self):
    self.select_option(ALEX_INPUT_SELECT, 'Away')
    self.handle_alex_extended_away = self.run_in(
      self._enable_extended_away, EXTENDED_AWAY_TIME, alex=True)

    if self.sleep.alex_asleep:  # failsafe to set awake
      self.sleep.set_alex('awake')

    with self.away_lock:
      self._logger.log('Alex left home.', level='INFO')
      if self.handle_one_left_steph is not None:
        # Steph just left as well -> we left together
        self.cancel_timer(self.handle_one_left_steph)
        self.handle_one_left_steph = None
        self._both_left_together()
      else:
        self.handle_one_left_alex = self.run_in(self._single_person_left, TRANSITION_TIME, person='alex')

      if self.presence.steph_away:
        self.presence.turn_off_occupancy()
      elif self.sleep.someone_asleep:
        # self.sm.lockdown_house()
        pass
      self.turn_on(self.const.ALEX_AWAY_BOOLEAN)
  
  
  def _steph_left_home(self):
    self.select_option(STEPH_INPUT_SELECT, 'Away')
    self.handle_steph_extended_away = self.run_in(
      self._enable_extended_away, EXTENDED_AWAY_TIME, steph=True)

    if self.sleep.steph_asleep:  # failsafe to set awake
      self.sleep.set_steph('awake')

    with self.away_lock:
      self._logger.log('Steph left home.', level='INFO')
      if self.handle_one_left_alex is not None:
        # Alex just left as well -> we left together
        self.cancel_timer(self.handle_one_left_alex)
        self.handle_one_left_alex = None
        self._both_left_together()
      else:
        self.handle_one_left_steph = self.run_in(self._single_person_left, TRANSITION_TIME, person='steph')

      if self.presence.alex_away:
        self.presence.turn_off_occupancy()
      elif self.sleep.someone_asleep:
        # self.sm.lockdown_house()
        pass
      self.turn_on(self.const.STEPH_AWAY_BOOLEAN)


  def _enable_extended_away(self, kwargs):
    """ Callback that turns on extended away after 24 hours and vacation mode if we are both extended away """
    if 'alex' in kwargs:
      self.select_option(ALEX_INPUT_SELECT, 'Extended Away')
    elif 'steph' in kwargs:
      self.select_option(STEPH_INPUT_SELECT, 'Extended Away')

    if self.get_state(ALEX_INPUT_SELECT) == self.get_state(STEPH_INPUT_SELECT) == 'Extended Away':
      self.presence.turn_on_vacation_mode()


  def _alex_state_change(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new):
      if old == 'home':
        self._alex_left_home()
      elif new == 'home':
        self._alex_got_home()

          
  def _steph_state_change(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new):
      if old == 'home':
        self._steph_left_home()
      elif new == 'home':
        self._steph_got_home()


  def _occupancy_state_change(self, entity, attribute, old, new ,kwargs):
    if self.utils.valid_input(old, new):
      if new == 'on':
        self._first_person_home()
        # self.sm.stop_security_monitoring()
      elif new == 'off':
        self._last_person_left_home()
        # self.sm.start_security_monitoring(start_offset=5)


  def _guest_mode_state_change(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new):
      if new == 'on':
        msg = 'Guest mode turned on. Occupancy will be turned on.'
        self._logger.log(msg, level='INFO')
        self.notifier.telegram_notify(msg, 'status', NOTIFY_TITLE)
        self.presence.turn_on_occupancy()
        self._someone_got_home()
        # Do not unlock door when guest mode is turned on, they can knock if we are home
        # if self.presence.alex_home or self.presence.steph_home: 
        #   self.dw.unlock_front_door()
      elif new == 'off':
        msg = 'Guest mode turned off.'
        if self.presence.steph_away and self.presence.alex_away:
          msg += ' Noone is home, occupancy will be turned off.'
          self.presence.turn_off_occupancy()
        else:
          msg += ' Someone is home, occupancy will remain on.'
        self._logger.log(msg, level='INFO')
        self.notifier.telegram_notify(msg, 'status', NOTIFY_TITLE)


  def terminate(self):
    pass

  def test(self, entity, attribute, old, new, kwargs):
    pass

