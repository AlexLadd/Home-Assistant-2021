
"""
Old version of app
  -> No config validation
  -> Need to generalize so TV's in future can easily use via config

"""

from base_app import BaseApp
import datetime

# TODO:

LIVING_ROOM_TV = 'media_player.living_room_tv'
LIVING_ROOM_TV_BOOLEAN = 'input_boolean.living_room_tv_in_use'
LIVING_ROOM_TV_INPUT_TEXT = 'input_text.living_room_tv_last_used'

LIVING_ROOM_LAMPS = 'living_room_lamps'
LIVING_ROOM_FAN = 'living_room_fan_light'
LIVING_ROOM_LIGHTSTRIP = 'living_room_lightstrip' # This is the native hue light 'light.living_room_tv'


class LivingRoomTV(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_2')

    self.lights = self.get_app('lights')
    self.bc = self.get_app('broadlink_client')

    self._volume_level = 0.0  # Sony TV volume level (dummy volume since TV volume does not control receiver volume)
    self._volume_handle = None

    # Sync TV state on AD restart
    if self.get_state(LIVING_ROOM_TV) == 'on':
      self._turn_on()
    else:
      self._turn_off()

    self.listen_state(self._living_room_tv_state_change, LIVING_ROOM_TV)
    self.listen_state(self._dark_mode_on, self.const.DARK_MODE_BOOLEAN, new='on')

  @property
  def tv_name(self):
    return 'living_room_tv'

  @property
  def state(self):
    return self.get_state(LIVING_ROOM_TV)

  @property
  def is_on(self):
    return bool(self.get_state(LIVING_ROOM_TV_BOOLEAN) == 'on')

  @property
  def volume_level(self):
    return self._volume_level


  def turn_on_tv(self):
    if self.state == 'off':
      self._logger.log('Living room TV turned on via HA.')
      self.turn_on(LIVING_ROOM_TV)

  def turn_off_tv(self):
    if self.state != 'off':
      self._logger.log('Living room TV turned off via HA.')
      self.turn_off(LIVING_ROOM_TV)

  def stop_tv(self):
    self._logger.log('Living room TV stopped.')
    self.call_service('media_player/media_stop', entity_id=LIVING_ROOM_TV)

  def play_tv(self):
    self._logger.log('Living room TV playing.')
    self.call_service('media_player/media_play', entity_id=LIVING_ROOM_TV)

  def pause_tv(self):
    self._logger.log('Living room TV paused.')
    self.call_service('media_player/media_pause', entity_id=LIVING_ROOM_TV)

  def select_tv_source(self, source):
    self._logger.log('Living room TV switch to source {}.'.format(source))
    self.call_service('media_player.select_source', entity_id=LIVING_ROOM_TV, source=source)


  def _turn_on(self):
    self._volume_level = self.get_state(LIVING_ROOM_TV, attribute='volume_level')
    self._volume_handle = self.listen_state(self._volume_state_change, LIVING_ROOM_TV, attribute='volume_level')

    if not self.is_on:
      self._logger.log('Living room TV boolean turned on.')
      self.turn_on(LIVING_ROOM_TV_BOOLEAN)
      self.bc.execute_command('living room', 'living room receiver', 'On', repeats=3)
      if self.dark_mode:
        self.lights.turn_light_off(LIVING_ROOM_FAN)
        self.lights.turn_light_on(LIVING_ROOM_LIGHTSTRIP, colour=[183,200,255], brightness=30)
        self.lights.turn_light_on(LIVING_ROOM_LAMPS, brightness=35)


  def _turn_off(self):
    self._volume_level = 0.0
    if self._volume_handle is not None:
      self.cancel_listen_state(self._volume_handle)
      self._volume_handle = None

    if self.is_on:
      self._logger.log('Living Room TV boolean turned off.')
      self.turn_off(LIVING_ROOM_TV_BOOLEAN)
      self.bc.execute_command('living_room', 'living room receiver', 'Off', repeats=3)
      dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      self.set_textvalue(LIVING_ROOM_TV_INPUT_TEXT, dt)
      if self.dark_mode:
        self.lights.turn_light_off(LIVING_ROOM_LIGHTSTRIP)
        if self.anyone_home():
          # Prevent lights from turning back on when noone is and home and TV is turned off
          self.lights.turn_light_on(LIVING_ROOM_LAMPS, brightness=100)
          self.lights.turn_light_on(LIVING_ROOM_FAN, brightness=100)


  def _living_room_tv_state_change(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new):
      if new != 'off':
        self._turn_on()
      if new == 'off':
        self._turn_off()


  def _dark_mode_on(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new):
      if self.is_on:
        self.lights.turn_light_off(LIVING_ROOM_FAN)
        self.lights.turn_light_on(LIVING_ROOM_LIGHTSTRIP, colour=[183,200,255], brightness=30)
        self.lights.turn_light_on(LIVING_ROOM_LAMPS, brightness=35)


  def _volume_state_change(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new) and isinstance(old, float) and isinstance(new, float):
      self._logger.log(f'[{self.name}] TV volume changed from {old} to {new} percent.')
      if old > new:
        self.bc.execute_command('living_room', 'living room receiver', 'Vol-', repeats=2, interval=0.2)
      elif new > old:
        self.bc.execute_command('living_room', 'living room receiver', 'Vol+', repeats=2, interval=0.2)
      self._volume_level = new


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing Living Room TV Module: ')

    # self._logger.log(f'[{self.name}] TV state: {self.get_state(LIVING_ROOM_TV)}')
    # self.bc.execute_command('living room', 'living room receiver', 'off', repeats=3)
    
    self.bc.execute_command('living room', 'living room TV', 'on', repeats=3)


  def terminate(self):
    pass
