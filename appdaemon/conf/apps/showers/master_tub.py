
from base_app import BaseApp
import datetime
import voluptuous as vol
import utils_validation

CONF_START_KEY = 'options'
CONF_MONITOR_ENTITY = 'monitor_entity'
CONF_TUB_SCENE = 'tub_scene'
CONF_DISABLED_LIGHT = 'disabled_lights'
CONF_TIMEOUT = 'timeout'

CONF_DEFAULT_TIMEOUT = 30*60

MASTER_TUB_SCHEMA = {
  CONF_START_KEY: vol.Schema(
    {
      vol.Required(CONF_MONITOR_ENTITY): utils_validation.entity_id,
      vol.Optional(CONF_TUB_SCENE, default=None): utils_validation.entity_id,
      vol.Optional(CONF_DISABLED_LIGHT, default=[]): utils_validation.ensure_list,
      vol.Optional(CONF_TIMEOUT, default=CONF_DEFAULT_TIMEOUT): utils_validation.parse_star_time,
    },
  )
}


class MasterTub(BaseApp): 

  APP_SCHEMA = BaseApp.APP_SCHEMA.extend(MASTER_TUB_SCHEMA)

  def setup(self): 
    # self.listen_state(self.test,'input_boolean.ad_testing_1')
    
    self.lights = self.get_app('lights')

    self._handle_tub_timer = None
    self.attrs = {}
    self._process_cfg(self.cfg)

    # Listen for exhaust fan state change
    self.listen_state(self._state_change, self.monitor_entity)

    # Sync up state on restart
    if self.is_on:
      self._turn_on()
    if not self.is_on:
      self._turn_off()


  def _process_cfg(self, config):
    """ Prep yaml data - Ensure we keep integrety of original data """
    import copy
    self.attrs = copy.deepcopy(config[CONF_START_KEY])


  @property
  def monitor_entity(self):
    return self.attrs[CONF_MONITOR_ENTITY]

  @property
  def tub_scene(self):
    return self.attrs[CONF_TUB_SCENE]
  
  @property
  def disabled_lights(self):
    return self.attrs[CONF_DISABLED_LIGHT]
    
  @property
  def timeout(self):
    return self.attrs[CONF_TIMEOUT]
  
  @property
  def state(self):
    return self.get_state(self.monitor_entity)

  @property
  def is_on(self):
    return bool(self.state == 'on')
    

  def _turn_on_boolean(self):
    if not self.is_on:
      self.turn_on(self.monitor_entity)
    self._logger.log(f'"{self.friendly_name(self.monitor_entity)}" turned on.')
    self._turn_on()


  def _turn_on(self):
    """ Logic for turning master tub on """
    for lt in self.disabled_lights:
      self.lights.disable_light(lt)
    self.lights.turn_light_on(self.tub_scene, override=True)

    # Start timeout timer (AD/HA reset will cause this to restart timer)
    self._handle_tub_timer = self.run_in(lambda *_: self._turn_off_boolean(), self.timeout)

      
  def _turn_off_boolean(self):
    if self.is_on:
      self.turn_off(self.shower_boolean)
    self._logger.log(f'"{self.friendly_name(self.monitor_entity)}" turned off.')
    self._turn_off()


  def _turn_off(self):
    """ Logic for turning master tub off """
    for lt in self.disabled_lights:
      self.lights.enable_light(lt)

    # Cancel timeout timer
    if self._handle_tub_timer is not None:
      self.cancel_timer(self._handle_tub_timer)


  def _state_change(self, entity, attribute, old, new, kwargs):
    # self._logger.log(f'State: {self.state}, is_on: {self.is_on}')
    if self.utils.valid_input(old, new):
      if new == 'on':
        self._turn_on_boolean() 
      elif new == 'off':
        self._turn_off_boolean()


  def test(self, entity, attribute, old, new, kwargs):
    pass

  def terminate(self):
    pass
