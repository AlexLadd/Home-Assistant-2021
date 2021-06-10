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

TODO:
  - Move config to yaml and add VOLUPTUOUS validation

Created: Jan 23, 2021
"""

from base_app import BaseApp
import datetime

DOORS_MASTER = 'group.door_sensors_master'
WINDOWS_MASTER = 'group.window_sensors_master'

FRONT_DOOR_SENSOR = 'binary_sensor.front_door_window_sensor'
KITCHEN_DOOR_SENSOR = 'binary_sensor.kitchen_door_window_sensor'
STUDY_DOOR_SENSOR = 'binary_sensor.study_outside_door_sensor'
BASEMENT_DOOR_SENSOR = 'binary_sensor.basement_patio_door_sensor'
MASTER_DOOR_SENSOR = 'binary_sensor.master_bedroom_outside_door_sensor'

MASTER_DOOR_SCREEN_SENSOR = 'binary_sensor.master_bedroom_screen_door_sensor'

HOUSE_DOORS = {
  'front_door' : {
    'door_sensor' : FRONT_DOOR_SENSOR,
    'screen_sensor' : None,
  },
  'kitchen_door' : {
    'door_sensor' : KITCHEN_DOOR_SENSOR,
    'screen_sensor' : None,
  },
  'study_door' : {
    'door_sensor' : STUDY_DOOR_SENSOR,
    'screen_sensor' : None,
  },
  'basement_door' : {
    'door_sensor' : BASEMENT_DOOR_SENSOR,
    'screen_sensor' : None,
  },
  'master_door' : {
    'door_sensor' : MASTER_DOOR_SENSOR,
    'screen_sensor' : MASTER_DOOR_SCREEN_SENSOR,
  },
}

DEEP_FREEZER_DOOR_SENSOR = 'binary_sensor.basement_freezer_door_sensor'
APPLIANCE_DOORS = [DEEP_FREEZER_DOOR_SENSOR]

FRONT_DOOR_RECENTLY_OPEN_TIME = 10*60
KITCHEN_DOOR_RECENTLY_OPEN_TIME = 10*60
DOOR_OPEN_INITIAL_NOTIFY_TIME = 5*60
DOOR_OPEN_REPEAT_NOTIFY_TIME = 10*60
DOOR_OPEN_LIGHTS_ON_TIME = 15*60
KITCHEN_DOOR_OPEN_LIGHTS = ['outside_carport', 'kitchen_door']

NOTIFY_TARGET = ['alex', 'steph']
NOTIFY_TITLE = 'Entry Points'


class DoorsWindows(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.notifier = self.get_app('notifier')
    self.presence = self.get_app('presence')
    self.lights = self.get_app('lights')

    self._handle_kitchen_door_open = None

    # Door Listeners
    self.listen_state(self._kitchen_door_opened_cb, KITCHEN_DOOR_SENSOR, old='off', new='on')
    self.listen_state(self._door_open_notify, KITCHEN_DOOR_SENSOR, new='on', duration=DOOR_OPEN_INITIAL_NOTIFY_TIME)
    self.listen_state(self._door_open_notify, FRONT_DOOR_SENSOR, new='on', duration=DOOR_OPEN_INITIAL_NOTIFY_TIME)
    self.listen_state(self._door_open_notify, STUDY_DOOR_SENSOR, new='on', duration=DOOR_OPEN_INITIAL_NOTIFY_TIME, repeat_time=15*60)
    self.listen_state(self._door_open_notify, BASEMENT_DOOR_SENSOR, new='on', duration=DOOR_OPEN_INITIAL_NOTIFY_TIME, repeat_time=15*60)
    self.listen_state(self._door_open_notify, MASTER_DOOR_SENSOR, new='on', duration=DOOR_OPEN_INITIAL_NOTIFY_TIME, repeat_time=15*60, second_door_sensor=MASTER_DOOR_SCREEN_SENSOR)

    # Screen Door Listeners
    self.listen_state(self._door_open_notify, MASTER_DOOR_SCREEN_SENSOR, new='on', duration=DOOR_OPEN_INITIAL_NOTIFY_TIME, repeat_time=15*60, second_door_sensor=MASTER_DOOR_SENSOR)

    
  @property
  def doors_closed(self):
    """ Return True all doors are close - Does not accouint for any screen doors """
    # return bool(not self.is_open(DOORS_MASTER))
    # return True not in [self.get_state(d) == 'off' for name, d in HOUSE_DOORS.items()['door_sensor']]
    for d in HOUSE_DOORS.values():
      if self.get_state(d['door_sensor']) == 'on':
        return False
    return True

  @property
  def doors_secure(self):
    """ Return True all doors or screens are close - Accouint for any screen doors in conjunction with their doors """
    for d in HOUSE_DOORS.values():
      if self.get_state(d['door_sensor']) == 'on': 
        if d['screen_sensor'] is not None and self.get_state(d['screen_sensor']) == 'on':
          return False
        elif d['screen_sensor'] is None:
          return False
    return True

  @property
  def appliance_doors_closed(self):
    return True not in [self.get_state(d) == 'off' for d in APPLIANCE_DOORS]

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
    elif door.lower().replace('_', ' ') in ['study', 'office']:
      return STUDY_DOOR_SENSOR
    else:
      return door

  
  def door_open_recently(self, door, time_limit=None):
    """ 
    Check if given door has been open within the time_limit
    
    param time_limit: Number of second to check if the door has been open. Default if FRONT_DOOR_RECENTLY_OPEN_TIME 
    """
    cutoff = time_limit if time_limit else FRONT_DOOR_RECENTLY_OPEN_TIME
    return bool(self.is_open(door) or self.utils.last_changed(self, door) < cutoff)


  def front_door_recently_opened(self, time_limit=None):
    return self.door_open_recently(FRONT_DOOR_SENSOR, time_limit) 

  def kitchen_door_recently_opened(self, time_limit=None):
    return self.door_open_recently(KITCHEN_DOOR_SENSOR, time_limit) 

  def study_door_recently_opened(self, time_limit=None):
    return self.door_open_recently(STUDY_DOOR_SENSOR, time_limit) 

  def master_door_recently_opened(self, time_limit=None):
    return self.door_open_recently(MASTER_DOOR_SENSOR, time_limit) 
    
  def basement_door_recently_opened(self, time_limit=None):
    return self.door_open_recently(BASEMENT_DOOR_SENSOR, time_limit) 


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
          # self._logger.log(f'Entity: {e}, last_changed: {self.utils.last_changed(self, e) }')
          if self.utils.last_changed(self, e) > min_open_time:
            return True
        else:
          return True
    return False


  def entry_point_check(self, door_check=True, window_check=True):
    """ Returns a human readable message with the open windows and/or doors as a string """
    open = []
 
    if door_check:
      for d in HOUSE_DOORS.values():
        if self.get_state(d['door_sensor']) == 'on': 
          name = self.friendly_name(d['door_sensor']).replace(' Sensor', '').lower()
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
      result = self.utils.list_to_pretty_print(open, 'open')

    return result.lower().capitalize()


  def appliance_door_check(self):
    """ Return if which appliance doors are open if any - LIST """
    opened = []
    for d in APPLIANCE_DOORS:
      if self.is_open(d):
        opened.append(self.friendly_name(d).replace(' sensor', ''))
    return self.utils.list_to_pretty_print(opened, 'open')

  
  def _kitchen_door_opened_cb(self, entity, attribute, old, new, kwargs):
    """ Perform actions when kitchen door is opened """
    if new == 'on' and self.dark_mode:
      self.cancel_timer(self._handle_kitchen_door_open)
      self.lights.turn_light_on(KITCHEN_DOOR_OPEN_LIGHTS)
      self._handle_kitchen_door_open = self.run_in(lambda *_: self.lights.turn_light_off(KITCHEN_DOOR_OPEN_LIGHTS), DOOR_OPEN_LIGHTS_ON_TIME)


  def _door_open_notify(self, entity, attribute, old, new, kwargs):
    """ Callback used to notify when a door has been opened for too long """
    repeat_time = kwargs.get('repeat_time', DOOR_OPEN_REPEAT_NOTIFY_TIME)
    second_door_sensor = kwargs.get('second_door_sensor', None)
    self._door_open_notify_timer( { 'door': entity, 'repeat_time': repeat_time, 'second_door_sensor': second_door_sensor } )


  def _door_open_notify_timer(self, kwargs):
    door = kwargs.get('door', None)
    repeat_time = kwargs.get('repeat_time', DOOR_OPEN_REPEAT_NOTIFY_TIME)
    second_door_sensor = kwargs.get('second_door_sensor', None)

    if not door:
      self._logger.log(f'Failed to get door, kwargs: {kwargs}')
      return

    if self.is_open(door):      
      if second_door_sensor is not None and not self.is_open(second_door_sensor):
        msg = f'The door is open ({self.friendly_name(door)}) while the second_door_sensor ({self.friendly_name(second_door_sensor)}) is open. No notification will be sent.'
        self._logger.log(msg, level='INFO')
        return

      time = int(self.utils.last_changed(self, door)/60)
      log_msg = f'The "{self.friendly_name(door)}" ({door}) door has been open for "{time}" minutes.'
      self._logger.log(log_msg, level='WARNING')


      notify_msg = f"The {self.friendly_name(door).lower().replace('sensor', '').replace('door', '')} door has been open for {time} minutes."
      self.notifier.telegram_notify(notify_msg, ['status', 'alarm'], NOTIFY_TITLE)
      self.notifier.tts_notify(notify_msg, speaker_override=True)
      
      self.run_in(self._door_open_notify_timer, repeat_time, door=door, repeat_time=repeat_time)
    else:
      time = int(self.utils.last_changed(self, door)/60)
      msg = f'The "{self.friendly_name(door)}" ({door}) door has been closed for "{time}" minutes.'
      self._logger.log(msg)


  def terminate(self):
    pass


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing DW Module: ')
    self._door_test()
    # self._appliance_door_tests()
    

  def _appliance_door_tests(self):
    self._logger.log(f'----------------------')
    self._logger.log(f'Appliances Doors Tests')
    r = [self.get_state(d) == 'off' for d in APPLIANCE_DOORS]
    self._logger.log(f'Appliance doors: {APPLIANCE_DOORS}, True check: {r}, result: {True not in r} ({self.appliance_doors_closed})')
    for d in APPLIANCE_DOORS:
      self._logger.log(f'{d} is open: {self.is_open(d)}')
    self._logger.log(f'All appliance doors closed: {self.appliance_doors_closed}')
    self._logger.log(f'----------------------')


  def _door_test(self):
    res = self.get_state(DOORS_MASTER, attribute='all')
    self._logger.log(res)

    # self.run_in(self._door_open_notify_timer, 1, door=FRONT_DOOR_SENSOR)
    # self.run_in(self._door_open_notify_timer, 1, door=KITCHEN_DOOR_SENSOR)
    self.run_in(self._door_open_notify_timer, 1, door=MASTER_DOOR_SENSOR, second_door_sensor=MASTER_DOOR_SCREEN_SENSOR)
    self.run_in(self._door_open_notify_timer, 2, door=MASTER_DOOR_SCREEN_SENSOR, second_door_sensor=MASTER_DOOR_SENSOR)

    for e in res['attributes'].get('entity_id', []):
      self._logger.log(f'Door entity_id: {e}')
      self._logger.log(f'state: {self.get_state(e)}, friendly_name: {self.get_state(e, attribute="friendly_name")}')
      self._logger.log(f'Friendly name: {self.friendly_name(e)}')

    res = self.front_door_recently_opened()
    self._logger.log(f'Front door just opened: {res} (time_limit: {FRONT_DOOR_RECENTLY_OPEN_TIME}). Last changed: {self.utils.last_changed(self, FRONT_DOOR_SENSOR)/60} minutes.')
    res = self.kitchen_door_recently_opened()
    self._logger.log(f'Kitchen door just opened: {res} (time_limit: {KITCHEN_DOOR_RECENTLY_OPEN_TIME}) Last changed: {self.utils.last_changed(self, KITCHEN_DOOR_SENSOR)/60} minutes.')
    res = self.front_door_recently_opened(10000000000)
    self._logger.log(f'Front door just opened: {res} (time_limit: 10000000000). Last changed: {self.utils.last_changed(self, FRONT_DOOR_SENSOR)/60} minutes.')
    res = self.kitchen_door_recently_opened(1000000000)
    self._logger.log(f'Kitchen door just opened: {res} (time_limit: 1000000000). Last changed: {self.utils.last_changed(self, KITCHEN_DOOR_SENSOR)/60} minutes.')

    self._logger.log(f'All doors closed: {self.doors_closed}')
    self._logger.log(f'All doors secure: {self.doors_secure}')
    self._logger.log(f'Entry point check: {self.entry_point_check()}')
  
