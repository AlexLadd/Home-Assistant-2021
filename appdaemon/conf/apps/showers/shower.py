
from base_app import BaseApp
import datetime

LIGHT_OFF_NO_MOTION_TIME = 3*60


class Shower(BaseApp): 

  def setup(self): 
    # self.listen_state(self.test,'input_boolean.appdaemon_testing')
    self.lights = self.get_app('lights')

    self.fan_switch = self.args['switch']
    self.shower_boolean = self.args['boolean']
    self.motion_sensor = self.args['motion_sensor'] 
    self.light_on = self.args['light_on']
    self.light_off = self.args.get('light_off', self.light_on)
    self.shower_scene = self.args.get('shower_scene', None)

    # Listen for exhaust fan state change
    self.listen_state(self._state_change, self.fan_switch)
    # Wait for everything to setup??
    self.run_in(self._setup, 1)


  def _setup(self, kwargs):
    # Sync up state on restart
    if self.get_state(self.fan_switch) == 'on':
      self._turn_on_boolean()
    if self.get_state(self.fan_switch) == 'off':
      self._turn_off_boolean()


  @property
  def state(self):
    return self.get_state(self.shower_boolean)

  @property
  def is_on(self):
    return bool(self.state == 'on')
    

  def __str__(self):
    return self.shower_boolean.split('.')[1].replace('_shower_in_use','').capitalize() + ' shower'


  def _turn_on_boolean(self):
    if not self.is_on:
      self._logger.log(f'{self} turned on.')
      self.turn_on(self.shower_boolean)
      if self.shower_scene:
        self.lights.turn_light_on(self.light_on, scene=self.shower_scene, override=True)
      else:
        self.lights.turn_light_on(self.light_on, brightness=100, override=True)


  def _turn_off_boolean(self):
    if self.is_on:
      self._logger.log(f'{self} turned off.')
      self.turn_off(self.shower_boolean)
      if self.utils.last_changed(self, self.motion_sensor) > LIGHT_OFF_NO_MOTION_TIME:
        # No motion for a while, turn light off
        self.lights.turn_light_off(self.light_off)


  def _state_change(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new):
      if new == 'on':
        self._turn_on_boolean() 
      elif new == 'off':
        self._turn_off_boolean()


  def test(self, entity, attribute, old, new, kwargs):
    pass

  def terminate(self):
    pass
