"""
Basement Freezer Monitoring App 
  -> Provides basement freezer door open/close data and controls
  -> Dependent on base_app

Dependencies:
  -> custom_logger
  -> presence

Functionality:
  -> Provices door state data
  -> Logic for what happens when doors are opened/closed (lights on/off, etc)
  -> Notify when door is left open too long!

Future updates:
  -> 

Created: April 6, 2021
Last Updated: April 6, 2021
"""

from base_app import BaseApp
import datetime

# TODO: 


BASEMENT_FREEZER_DOOR_SENSOR = 'binary_sensor.basement_freezer_door_sensor'

DOOR_OPEN_INITIAL_NOTIFY_TIME = 2*60
DOOR_OPEN_REPEAT_NOTIFY_TIME = 4*60

NOTIFY_TARGET = ['alex', 'steph']
NOTIFY_TITLE = 'Basement Freezer'


class BasementFreezer(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_3')

    self.notifier = self.get_app('notifier')
    self.presence = self.get_app('presence')

    self.listen_state(self._door_open_notify, BASEMENT_FREEZER_DOOR_SENSOR, new='on', duration=DOOR_OPEN_INITIAL_NOTIFY_TIME)


  
  def door_open_recently(self, door, time_limit=None):
    """ 
    Check if given door has been open within the time_limit
    
    param time_limit: Number of second to check if the door has been open. Default if FRONT_DOOR_RECENTLY_OPEN_TIME 
    """
    cutoff = time_limit if time_limit else FRONT_DOOR_RECENTLY_OPEN_TIME
    return bool(self.is_open(door) or self.utils.last_changed(self, door) < cutoff)


  def basement_freezer_door_recently_opened(self, time_limit=None):
    return self.door_open_recently(FRONT_DOOR_SENSOR, time_limit) 


  def is_open(self, entity, min_open_time=None):
    """ Return True if the freezer door is open """
    return bool(self.get_state(BASEMENT_FREEZER_DOOR_SENSOR) == 'on')


  def _door_open_notify(self, entity, attribute, old, new, kwargs):
    """ Callback used to notify when a door has been opened for too long """
    repeat_time = kwargs.get('repeat_time', DOOR_OPEN_REPEAT_NOTIFY_TIME)
    self._door_open_notify_timer( { 'door': entity, 'repeat_time': repeat_time } )


  def _door_open_notify_timer(self, kwargs):
    door = kwargs.get('door', None)
    repeat_time = kwargs.get('repeat_time', DOOR_OPEN_REPEAT_NOTIFY_TIME)
    if not door:
      self._logger.log(f'Failed to get door, kwargs: {kwargs}', level='WARNING')
      return

    if self.is_open(door):
      time = int(self.utils.last_changed(self, door)/60)
      log_msg = f'The "{self.friendly_name(door)}" ({door}) has been open for "{time}" minutes.'
      self._logger.log(log_msg, level='WARNING')
      
      notify_msg = f"The {self.friendly_name(door).lower().replace('sensor', '')} has been open for {time} minutes."
      self.notifier.telegram_notify(notify_msg, ['status', 'alarm'], NOTIFY_TITLE)
      self.notifier.tts_notify(notify_msg, speaker_override=True)
      
      self.run_in(self._door_open_notify_timer, repeat_time, door=door, repeat_time=repeat_time)
    else:
      time = int(self.utils.last_changed(self, door)/60)
      msg = f'The "{self.friendly_name(door)}" ({door}) has been closed for "{time}" minutes.'
      self._logger.log(msg)


  def terminate(self):
    pass


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing Basement_Freezer Module: ')
