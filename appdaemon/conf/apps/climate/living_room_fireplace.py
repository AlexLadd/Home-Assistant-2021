
"""
Living Room Fireplace App

"""

from base_app import BaseApp
import datetime

LIVING_ROOM_FIREPLACE_RELAY = 'switch.living_room_fireplace_controller_relay'
FIREPLACE_FIREPLACE_EVENT = 'esphome.living_room_fireplace'
FIREPLACE_LIGHT_EVENT = 'esphome.living_room_lights'
FIREPLACE_TV_EVENT = 'esphome.living_room_tv'

# TODO:
# Need to listen for the event from the display to determine if it was turned on manually vs using the relay
# build in logic for home/asleep and turning off
# Add to security check 
# add in temperature logic
# Add temperature logic to controller


class LivingRoomFireplace(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.lights = self.get_app('lights')
    self.living_room_tv = self.get_app('living_room_tv')
    self.climate = self.get_app('climate')

    self.listen_event(self._fireplace_event_cb, FIREPLACE_FIREPLACE_EVENT)
    self.listen_state(self._fireplace_state_cb, LIVING_ROOM_FIREPLACE_RELAY)
    self.listen_event(self._lights_event_cb, FIREPLACE_LIGHT_EVENT)
    self.listen_event(self._tv_event_cb, FIREPLACE_TV_EVENT)



  @property
  def state(self):
    return self.get_state(LIVING_ROOM_FIREPLACE_RELAY)

  @property
  def is_on(self):
    return bool(self.state == 'on')

  def set_fireplace_state(self, fireplace_entity, new_state):
    """ Set state of a given fireplace to on/off """
    if new_state != self.state:
      self.set_state(fireplace_entity, state=new_state)
      self._logger.log(f'Setting {fireplace_entity} to "{new_state}"')
    else:
      self._logger.log(f'{fireplace_entity} is already "{self.state}" (requesting new_state: "{new_state}"). No action will be taken.')

  def turn_fireplace_on(self):
    """ Turn living room fireplace on """
    self.set_fireplace_state(LIVING_ROOM_FIREPLACE_RELAY, 'on')
    
  def turn_fireplace_off(self):
    """ Turn living room fireplace off """
    self.set_fireplace_state(LIVING_ROOM_FIREPLACE_RELAY, 'off')


  def _fireplace_state_cb(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'The living room fireplace was just turned {new}', level='DEBUG')
    # r = self.get_state(LIVING_ROOM_FIREPLACE_RELAY, attribute='all')
    # self._logger.log(f'Fireplace event: {r}')


  def _fireplace_event_cb(self, event_name, data, kwargs):
    self._logger.log(f'_fireplace_event_cb: {locals()}', level='DEBUG')
    turn_on = data.get('action', None) == 'turn_on'
    if turn_on:
      self._logger.log(f'The fireplace was turned ON using the controller')
    else:
      self._logger.log(f'The fireplace was turned OFF using the controller')

  
  def _lights_event_cb(self, event_name, data, kwargs):
    self._logger.log(f'_lights_event_cb: {locals()}', level='DEBUG')
    turn_on = data.get('action', None) == 'turn_on'
    if turn_on:
      self.lights.turn_lights_on('living_room_lamps')
      self.lights.turn_lights_on('living_room_fan')
    else:
      self.lights.turn_lights_off('living_room_lamps')
      self.lights.turn_lights_off('living_room_fan')
  
  
  def _tv_event_cb(self, event_name, data, kwargs):
    self._logger.log(f'_tv_event_cb: {locals()}')
    turn_on = data.get('action', None) == 'turn_on'
    if turn_on:
      self.living_room_tv.turn_on_tv()
    else:
      self.living_room_tv.turn_off_tv()


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing Living Room Fireplace Module: ')

    r = self.climate.todays_low
    r2 = self.climate.todays_high

    self._logger.log(f'r: {r}, r2: {r2}')

    self.turn_fireplace_off()



  def terminate(self):
    pass
