
"""

Cat Water Dish

TODO:
  - add motion sensor & ON/OFF control
"""

from base_app import BaseApp
import datetime


CAT_WATER_DISH_RELAY = 'switch.sonoff_s20_cat_water_dish_relay'


class WaterDish(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.notifier = self.get_app('notifier')
    self.sleep = self.get_app('sleep')

    self._enabled = True


  @property
  def relay_state(self):
    return self.get_state(CAT_WATER_DISH_RELAY)

  @property
  def is_on(self):
    return self.relay_state == 'on'

  @property
  def is_enabled(self):
    return self._enabled

  
  def turn_relay_on(self):
    if not self.is_on:
      self._logger.log(f'Turning the cat water dish relay ON')
      self.turn_on(CAT_WATER_DISH_RELAY)
  
  def turn_relay_off(self):
    if self.is_on:
      self._logger.log(f'Turning the cat water dish relay OFF')
      self.turn_off(CAT_WATER_DISH_RELAY)


  def _water_dish_motion_callback(self, entity, attribute, old, new, kwargs):
    """ Enable/disable the water dish after a long delay using motion sensor aimed close to the dish """
    pass


  def test(self, entity, attribute, old, new, kwargs):
    self.log(f'Testing Water Dish Module: ') 

    if self.is_on:
      self.turn_relay_off()
    elif not self.is_on:
      self.turn_relay_on()
