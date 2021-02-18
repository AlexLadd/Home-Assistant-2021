
from base_app import BaseApp
import datetime

# TODO:

MASTER_SENSOR = 'hue_tap_master_bedroom'
MOBILE_SENSOR = 'hue_tap_mobile'

# Hue Tap Button Codes
HUE_BUTTON_MAP = {
  34: '1_click',
  16: '2_click',
  17: '3_click',
  18: '4_click'
}

class HueButtons(BaseApp):

  def setup(self):
    # self.listen_state(self.test,'input_boolean.ad_testing_1')
    self.sleep = self.get_app('sleep')
    self.presence = self.get_app('presence')
    self.lights = self.get_app('lights')

    self.listen_event(self._master_button, 'hue_event', id=MASTER_SENSOR)
    self.listen_event(self._mobile_button, 'hue_event', id=MOBILE_SENSOR)


  def _master_button(self, event_name, data, kwargs):
    button = HUE_BUTTON_MAP[data.get('event')]
    if button == '1_click':
      self._logger.log('Master button 1')
      if self.now_is_between(self.const.BEDTIME_START, self.const.BEDTIME_END):
        if self.sleep.alex_awake and self.presence.alex_home:
          self.sleep.set_alex('asleep')
        else:
          pass
      else:
        if self.sleep.alex_asleep and self.presence.alex_home:
          self.sleep.set_alex('awake')
        else:
          pass

    elif button == '2_click':
      self._logger.log('Master button 2')
      self.lights.toggle_light('master_light_steph', brightness=10, override=True)

    elif button == '3_click':
      self._logger.log('Master button 3')
      if self.now_is_between(self.const.BEDTIME_START, self.const.BEDTIME_END):
        if self.sleep.steph_awake and self.presence.steph_home:
          self.sleep.set_steph('asleep')
        else:
          pass
      else:
        if self.sleep.steph_asleep and self.presence.steph_home:
          self.sleep.set_steph('awake')
        else:
          pass

    elif button == '4_click':
      self._logger.log('Master button 4')
      self.lights.toggle_light('master_light_alex', brightness=10, override=True)


  def _mobile_button(self, event_name, data, kwargs):
    # self._logger.log(f'_mobile_button() called: {event_name}, {data}, {kwargs}')

    button = HUE_BUTTON_MAP[data.get('event')]
    if button == '1_click':
      self._logger.log('Mobile button 1')
      self.lights.turn_light_on('basement_storage', brightness=100, override=True)
      self.lights.disable_light('basement_storage')
    elif button == '2_click':
      self._logger.log('Mobile button 2')
      self.lights.turn_light_off('basement_storage', override=True)
      self.lights.enable_light('basement_storage')
    elif button == '3_click':
      self._logger.log('Mobile button 3')
      self.lights.turn_light_on('laundry_room', brightness=100, override=True)
      self.lights.disable_light('laundry_room')
    elif button == '4_click':
      self._logger.log('Mobile button 4')
      self.lights.turn_light_off('laundry_room', override=True)
      self.lights.enable_light('laundry_room')


  def test(self, entity, attribute, old, new, kwargs):
    pass  

  def terminate(self):
    pass