
from base_app import BaseApp
import datetime

# TODO:

MASTER_TUB_IN_USE = 'input_boolean.master_tub_in_use'

MASTER_SENSOR = 'hue_tap_master_bedroom'
MOBILE_SENSOR = 'hue_tap_mobile'
MASTER_BATHROOM_DIMMER = 'hue_dimmer_master_bathroom'

# Hue Tap Button Codes
ZGP_SWITCH_BUTTON_1 = 34
ZGP_SWITCH_BUTTON_2 = 16
ZGP_SWITCH_BUTTON_3 = 17
ZGP_SWITCH_BUTTON_4 = 18

HUE_BUTTON_MAP = {
  ZGP_SWITCH_BUTTON_1: "1_click",
  ZGP_SWITCH_BUTTON_2: "2_click",
  ZGP_SWITCH_BUTTON_3: "3_click",
  ZGP_SWITCH_BUTTON_4: "4_click",
}

# Hue Dimmer Button Codes
ZLL_SWITCH_BUTTON_1_INITIAL_PRESS = 1000
ZLL_SWITCH_BUTTON_2_INITIAL_PRESS = 2000
ZLL_SWITCH_BUTTON_3_INITIAL_PRESS = 3000
ZLL_SWITCH_BUTTON_4_INITIAL_PRESS = 4000

ZLL_SWITCH_BUTTON_1_HOLD = 1001
ZLL_SWITCH_BUTTON_2_HOLD = 2001
ZLL_SWITCH_BUTTON_3_HOLD = 3001
ZLL_SWITCH_BUTTON_4_HOLD = 4001

ZLL_SWITCH_BUTTON_1_SHORT_RELEASED = 1002
ZLL_SWITCH_BUTTON_2_SHORT_RELEASED = 2002
ZLL_SWITCH_BUTTON_3_SHORT_RELEASED = 3002
ZLL_SWITCH_BUTTON_4_SHORT_RELEASED = 4002

ZLL_SWITCH_BUTTON_1_LONG_RELEASED = 1003
ZLL_SWITCH_BUTTON_2_LONG_RELEASED = 2003
ZLL_SWITCH_BUTTON_3_LONG_RELEASED = 3003
ZLL_SWITCH_BUTTON_4_LONG_RELEASED = 4003

HUE_DIMMER_MAP = {
    ZLL_SWITCH_BUTTON_1_INITIAL_PRESS: "1_click",
    ZLL_SWITCH_BUTTON_2_INITIAL_PRESS: "2_click",
    ZLL_SWITCH_BUTTON_3_INITIAL_PRESS: "3_click",
    ZLL_SWITCH_BUTTON_4_INITIAL_PRESS: "4_click",
    ZLL_SWITCH_BUTTON_1_HOLD: "1_hold",
    ZLL_SWITCH_BUTTON_2_HOLD: "2_hold",
    ZLL_SWITCH_BUTTON_3_HOLD: "3_hold",
    ZLL_SWITCH_BUTTON_4_HOLD: "4_hold",
    ZLL_SWITCH_BUTTON_1_SHORT_RELEASED: "1_click_up",
    ZLL_SWITCH_BUTTON_2_SHORT_RELEASED: "2_click_up",
    ZLL_SWITCH_BUTTON_3_SHORT_RELEASED: "3_click_up",
    ZLL_SWITCH_BUTTON_4_SHORT_RELEASED: "4_click_up",
    ZLL_SWITCH_BUTTON_1_LONG_RELEASED: "1_hold_up",
    ZLL_SWITCH_BUTTON_2_LONG_RELEASED: "2_hold_up",
    ZLL_SWITCH_BUTTON_3_LONG_RELEASED: "3_hold_up",
    ZLL_SWITCH_BUTTON_4_LONG_RELEASED: "4_hold_up",
}

class HueButtons(BaseApp):

  def setup(self):
    # self.listen_state(self.test,'input_boolean.ad_testing_1')
    self.sleep = self.get_app('sleep')
    self.presence = self.get_app('presence')
    self.lights = self.get_app('lights')

    self.listen_event(self._master_button, 'hue_event', id=MASTER_SENSOR)
    self.listen_event(self._mobile_button, 'hue_event', id=MOBILE_SENSOR)
    self.listen_event(self._master_bathroom_dimmer, 'hue_event', id=MASTER_BATHROOM_DIMMER)


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


  def _master_bathroom_dimmer(self, event_name, data, kwargs):
    button = HUE_DIMMER_MAP[data.get('event')]
    self._logger.log(f'Master Bathroom Dimmer button: {button}')

    # TODO: Add bathroom scenes & dimmer controls
    if button == '1_click_up':
      self.turn_on(MASTER_TUB_IN_USE)
    elif button == '4_click_up':
      self.turn_off(MASTER_TUB_IN_USE)


  def test(self, entity, attribute, old, new, kwargs):
    pass  

  def terminate(self):
    pass