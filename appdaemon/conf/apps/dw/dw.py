"""
Entrypoint App 
  -> Provides an entrypoint data and controls
  -> Dependent on base_app

Dependencies:
  -> custom_logger
  -> presence, lights

Functionality:
  -> Provices window & door state data
  -> Logic for what happens when doors are opened/closed (lights on/off, etc)

Future updates:
  -> 

Created: Jan 23, 2021
Last Updated: Jan 23, 2021
"""

from base_app import BaseApp
import datetime
from const import GUEST_MODE_BOOLEAN
from utils import last_changed, valid_input

# TODO: 

LOG_CUTOFF = 'DEBUG'

DOORS_MASTER = 'group.door_sensors_master'
WINDOWS_MASTER = 'group.window_sensors_master'

FRONT_DOOR_SENSOR = 'binary_sensor.front_door_window_sensor'
KITCHEN_DOOR_SENSOR = 'binary_sensor.kitchen_door_window_sensor'

FRONT_DOOR_RECENTLY_OPEN_TIME = 10*60
KITCHEN_DOOR_RECENTLY_OPEN_TIME = 10*60
DOOR_INITIAL_OPEN_NOTIFY_TIME = 5*60
DOOR_OPEN_LIGHTS_ON_TIME = 15*60
KITCHEN_DOOR_OPEN_LIGHTS = ['outside_carport', 'kitchen_door']

NOTIFY_TARGET = ['alex', 'steph']
NOTIFY_TITLE = 'Entry Points'


class DoorsWindows(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_3')

    self.notifier = self.get_app('notifier')
    self.presence = self.get_app('presence')
    self.lights = self.get_app('lights')

    self._handle_kitchen_door_open = None

    self.listen_state(self._kitchen_door_opened_cb, KITCHEN_DOOR_SENSOR, old='off', new='on')
    self.listen_state(self._door_open_notify, KITCHEN_DOOR_SENSOR, new='on', duration=DOOR_INITIAL_OPEN_NOTIFY_TIME)
    self.listen_state(self._door_open_notify, FRONT_DOOR_SENSOR, new='on', duration=DOOR_INITIAL_OPEN_NOTIFY_TIME)

    
  @property
  def doors_closed(self):
    return bool(not self.is_open(DOORS_MASTER))

  @property
  def windows_closed(self):
    return bool(not self.is_open(WINDOWS_MASTER))

  @property
  def everything_closed(self):
    return bool(self.doors_closed and self.windows_closed)


  def map_door_to_entity(self, door):
    """ map aliases to entity """
    if door.lower().replace('_', ' ') in ['kitchen', 'carport', 'side door']:
      return KITCHEN_DOOR_SENSOR
    elif door.lower().replace('_', ' ') in ['front', 'main']:
      return FRONT_DOOR_SENSOR
    else:
      return door


  def front_door_recently_opened(self, time_limit=None):
    """ If the F.D. is open or was recently opened/closed than return True """
    cutoff = time_limit if time_limit else FRONT_DOOR_RECENTLY_OPEN_TIME
    return bool(self.is_open(FRONT_DOOR_SENSOR) or last_changed(self, FRONT_DOOR_SENSOR) < cutoff)


  def kitchen_door_recently_opened(self, time_limit=None):
    """ If the F.D. is open or was recently opened/closed than return True """
    cutoff = time_limit if time_limit else KITCHEN_DOOR_RECENTLY_OPEN_TIME
    return bool(self.is_open(KITCHEN_DOOR_SENSOR) or last_changed(self, KITCHEN_DOOR_SENSOR) < cutoff)


  def is_open(self, entity=None, min_open_time=None):
    """ 
    Check if an entrypoint is open. Default -> All windows & doors 
    param min_open_time: Minimum time that the entrypoint needs to be open for before returning 'open' (seconds)
    """
    if entity is None:
      entity = [DOORS_MASTER, WINDOWS_MASTER]
    if isinstance(entity, str):
      entity = [entity]
    for e in entity:
      if self.get_state(e) == 'on':
        if min_open_time is not None:
          # self._logger.log(f'Entity: {e}, last_changed: {last_changed(self, e) }')
          if last_changed(self, e) > min_open_time:
            return True
        else:
          return True
    return False


  def entry_point_check(self, door_check=True, window_check=True):
    """ Returns a human readable message with the open windows and/or doors as a string """
    open = []
 
    if door_check:
      group = self.get_state(DOORS_MASTER, attribute="all")
      for entity in group['attributes']['entity_id']:
        entity_info = self.get_state(entity, attribute="all")
        if entity_info['state'] == 'on':
          name = entity_info['attributes']['friendly_name'].replace(' Sensor','').lower()
          open.append(name)

    if window_check:
      group = self.get_state(WINDOWS_MASTER, attribute="all")
      for entity in group['attributes']['entity_id']:
        entity_info = self.get_state(entity, attribute="all")
        if entity_info['state'] == 'on':
          name = entity_info['attributes']['friendly_name'].replace(' Sensor','').lower()
          open.append(name)

    if len(open) == 0:
      result = "All doors and windows are closed."
    else:
      result = list_to_pretty_print(open, 'open')

    return result.lower().capitalize()

  
  def _kitchen_door_opened_cb(self, entity, attribute, old, new, kwargs):
    """ Perform actions when kitchen door is opened """
    if new == 'on' and self.dark_mode:
      self.cancel_timer(self._handle_kitchen_door_open)
      self.lights.turn_light_on(KITCHEN_DOOR_OPEN_LIGHTS)
      self._handle_kitchen_door_open = self.run_in(lambda *_: self.lights.turn_light_off(KITCHEN_DOOR_OPEN_LIGHTS), DOOR_OPEN_LIGHTS_ON_TIME)


  def _door_open_notify(self, entity, attribute, old, new, kwargs):
    self._door_open_notify_timer( { 'door': entity } )


  def _door_open_notify_timer(self, kwargs):
    door = kwargs.get('door', None)
    if not door:
      self._logger.log(f'Failed to get door, kwargs: {kwargs}')
      return

    if self.is_open(door):
      time = int(self.utils.last_changed(self, door)/60)
      msg = f'The "{self.friendly_name(door)}" ({door}) door has been open for "{time}" minutes.'
      self.notifier.telegram_notify(msg, 'status', NOTIFY_TITLE)
      self._logger.log(msg, level='WARNING')
      self.run_in(self._door_open_notify_timer, FRONT_DOOR_REPLEAT_OPEN_NOTIFY_TIME, door=door)
    else:
      time = int(self.utils.last_changed(self, door)/60)
      msg = f'The "{self.friendly_name(door)}" ({door}) door has been closed for "{time}" minutes.'
      self._logger.log(msg)


  def terminate(self):
    pass


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing DW Module: ')
    # self._door_test()
    
    r = self.entry_point_check()
    self._logger.log(f'Door & Window Check: {r}')


  def _door_test(self):
    res = self.get_state(DOORS_MASTER, attribute='all')
    self._logger.log(res)

    self.run_in(self._door_open_notify_timer, 1, door=FRONT_DOOR_SENSOR)
    self.run_in(self._door_open_notify_timer, 1, door=KITCHEN_DOOR_SENSOR)

    for e in res['attributes'].get('entity_id', []):
      self._logger.log(f'Door entity_id: {e}')
      self._logger.log(f'state: {self.get_state(e)}, friendly_name: {self.get_state(e, attribute="friendly_name")}')
      self._logger.log(f'Friendly name: {self.friendly_name(e)}')

    res = self.front_door_recently_opened()
    self._logger.log(f'Front door just opened: {res} (time_limit: {FRONT_DOOR_RECENTLY_OPEN_TIME}). Last changed: {last_changed(self, FRONT_DOOR_SENSOR)/60} minutes.')
    res = self.kitchen_door_recently_opened()
    self._logger.log(f'Kitchen door just opened: {res} (time_limit: {KITCHEN_DOOR_RECENTLY_OPEN_TIME}) Last changed: {last_changed(self, KITCHEN_DOOR_SENSOR)/60} minutes.')
    res = self.front_door_recently_opened(10000000000)
    self._logger.log(f'Front door just opened: {res} (time_limit: 10000000000). Last changed: {last_changed(self, FRONT_DOOR_SENSOR)/60} minutes.')
    res = self.kitchen_door_recently_opened(1000000000)
    self._logger.log(f'Kitchen door just opened: {res} (time_limit: 1000000000). Last changed: {last_changed(self, KITCHEN_DOOR_SENSOR)/60} minutes.')
  
