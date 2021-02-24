
"""
Base class for power based appliances

NOTE: Must call super.setup() in concrete appliance app
NOTE: All appliances are dependend on appliance_base (global_modules) 
NOTE: All appliance are dependent on notifier & custom_logger (dependencies)
"""

from base_app import BaseApp
import datetime
import yaml
import json
import voluptuous as vol 

import utils_validation
from const import CONF_FRIENDLY_NAME, CONF_ALIASES, CONF_ENTITY_ID, CONF_OPTIONS, CONF_DEFAULTS, CONF_PROPERTIES


MAX_RUNTIME_TIMEOUT = 180 # minutes
# Time before reset appliances after finishing early in seconds
EARLY_FINISH_TIMEOUT = 12*60*60

NOTIFY_TARGET = ['status']

CONF_START_KEY = 'options'
CONF_SENSOR = 'sensor' # Sensor used for appliance state changes
CONF_MONITOR_ENTITY = 'monitor_entity'
CONF_RUNTIME_SENOR = 'runtime_sensor'
CONF_LAST_USED_INPUT_TEXT = 'last_used_input_text'
CONF_MIN_RUNTIME = 'min_runtime'
CONF_UPDATE_FREQUENCY = 'update_frequency'
CONF_THRESHOLD_OFF_TIME = 'threshold_off_time'
CONF_DATA_FILE_PATH = 'back_file_path'

DEFAULT_CONF_UPDATE_FREQUENCY = 5

BASE_APPLIANCE_SCHEMA = vol.Schema(
  {
    vol.Required(CONF_FRIENDLY_NAME): str,
    vol.Required(CONF_SENSOR): utils_validation.entity_id,
    vol.Required(CONF_MONITOR_ENTITY): utils_validation.entity_id,
    vol.Required(CONF_RUNTIME_SENOR): utils_validation.entity_id,
    vol.Required(CONF_LAST_USED_INPUT_TEXT): utils_validation.entity_id,
    vol.Required(CONF_MIN_RUNTIME): utils_validation.parse_star_time,
    vol.Required(CONF_THRESHOLD_OFF_TIME): utils_validation.parse_star_time,
    
    vol.Optional(CONF_UPDATE_FREQUENCY, default=DEFAULT_CONF_UPDATE_FREQUENCY): utils_validation.try_parse_int,
    vol.Optional(CONF_DATA_FILE_PATH, default=None): utils_validation.entity_id,
  },
  vol.ALLOW_EXTRA,
)


class ApplianceBase(BaseApp):

  """
  Base class for a basic appliance
  """

  def setup(self):
    """ Base attributes for all appliances """
    self.notifier = self.get_app('notifier')

    self.attrs = {}
    self._process_cfg(self.cfg)

    self._start_time = None
    self._last_checked_time = None
    self.handle_runtime_update = None
    self.handle_early_finish_restart = None

    # Sync up with saved data on reboot
    with open(self.data_file, 'r+') as f:
      previous_data = yaml.safe_load(f)
    was_running = previous_data.get('running', False)
    if was_running:
      self._start_time = previous_data['start']
      self._last_checked_time = previous_data['last_checked']
      if self.datetime() - self._start_time > datetime.timedelta(minutes=MAX_RUNTIME_TIMEOUT):
        self._turn_off(override=True)
      elif self.is_on:
        self._logger.log('The {} was running while AD restarted.'.format(self.friendly_name.lower()))
        self.handle_runtime_update = self.run_every(self._update_runtime_sensor, self.datetime() + datetime.timedelta(seconds=3), self.update_frequency)

    # Listen for primary sensor state changes
    self.listen_state(self._state_change, self.sensor)


  def _process_cfg(self, config):
    """ Prep yaml data - Ensure we keep integrety of original data """
    import copy
    self.attrs = copy.deepcopy(config[CONF_START_KEY])


############ config properties #############

  @property
  def friendly_name(self):
    """ Returns friendly_name to this appliances """
    return self.attrs[CONF_FRIENDLY_NAME]

  @property
  def sensor(self):
    """ Returns sensor to this appliances """
    return self.attrs[CONF_SENSOR]

  @property
  def monitor_entity(self):
    """ Returns monitor_entity to this appliances (input_boolean) """
    return self.attrs[CONF_MONITOR_ENTITY]

  @property
  def runtime_sensor(self):
    """ Returns runtime_sensor to this appliances data file (template sensor) """
    return self.attrs[CONF_RUNTIME_SENOR]

  @property
  def input_text(self):
    """ Returns input_text to this appliances """
    return self.attrs[CONF_LAST_USED_INPUT_TEXT]

  @property
  def min_runtime(self):
    """ Returns min_runtime to this appliances """
    return self.attrs[CONF_MIN_RUNTIME]

  @property
  def update_frequency(self):
    """ Returns the frequency of runtime updates [Defaults: 5 seconds] """
    return self.attrs[CONF_UPDATE_FREQUENCY]

  @property
  def threshold_off_time(self):
    """ Returns the time between the last indication it was on and when it should be turned off """
    return self.attrs[CONF_THRESHOLD_OFF_TIME]

  @property
  def data_file(self):
    """ Returns path to this appliances data file """
    f = self.attrs[CONF_DATA_FILE_PATH]
    if f is None:
      return '/conf/apps/appliances/{}_data.yml'.format(self.friendly_name.lower().replace(' ', '_'))
    else:
      return '/conf/apps/appliances/{}_data.yml'.format(f.replace(' ', '_'))

  @property
  def state(self):
    return self.get_state(self.monitor_entity)

  @property
  def is_on(self):
    return bool(self.state == 'on')

  @property
  def sensor_state(self):
    return self.get_state(self.sensor)

  @property
  def runtime(self) -> float:
    """ Return the runtime of the dishwasher in minutes as a float """
    try:
      time = self.get_state(self.runtime_sensor).split(':')
      return round(int(time[0])*60 + int(time[1]) + int(time[2])/60, 2)
    except:
      return 0.0

  @runtime.setter
  def runtime(self, value):
    try:
      self.set_state(self.runtime_sensor, state=str(value))
    except:
      self._logger.log(f'Failed to set {self.friendly_name} runtime sensor state. Doing nothing.')


  def _update_runtime_sensor(self, kwargs):
    """ Manually update the runtime sensor for the UI """
    if self._last_checked_time is None:
      self._last_checked_time = self.datetime()
    now = self.datetime()
    secs = (now - self._last_checked_time).total_seconds() + self.runtime*60
    self.runtime = datetime.timedelta(seconds=int(secs))
    self._last_checked_time = now


  def _turn_on(self):
    """ Actions to take when appliance is turned on """
    self.cancel_timer(self.handle_early_finish_restart)

    if not self.is_on:
      self._logger.log(f'The {self.friendly_name.lower()} was turned on.', level='INFO')
      self.turn_on(self.monitor_entity)
      self._start_time = self.datetime()
      self.handle_runtime_update = self.run_every(self._update_runtime_sensor, self.datetime() + datetime.timedelta(seconds=3), self.update_frequency)


  def _turn_off(self, override=False):
    """ Actions to take when appliance is turned off 
    param override: Force appliance to completely shutdown (no early finish)
    """
    self.cancel_timer(self.handle_early_finish_restart)

    if self.is_on:
      self._logger.log(f'The {self.friendly_name.lower()} was turned off.', level='INFO')
      self.turn_off(self.monitor_entity)
      dt = datetime.datetime.now()
      self.set_textvalue(self.input_text, dt.strftime("%b %d %Y %H:%M:%S")) #(%Y-%m-%d %H:%M:%S"))
      self.cancel_timer(self.handle_runtime_update)
      self._start_time = None

      if (self.runtime < self.min_runtime) and not override:
        msg = 'The {} finished early, please reset it. Runtime: {} minutes.'.format(self.friendly_name.lower(), int(self.runtime))
        self.handle_early_finish_restart = self.run_in(lambda *_: self._early_finish_reset(), EARLY_FINISH_TIMEOUT)
      else:
        msg = 'The {} is complete. Runtime: {} minutes.'.format(self.friendly_name.lower(), int(self.runtime))
        self.runtime = '00:00:00'
        self._last_checked_time = None

      self.notifier.tts_notify(msg)
      self.notifier.telegram_notify(msg, NOTIFY_TARGET, self.friendly_name)

    elif override:
      self._logger.log(f'Force resetting the {self.friendly_name.lower()} now')
      self.runtime = '00:00:00'
      self._last_checked_time = None
      self._start_time = None


  def _early_finish_reset(self):
    """ The appliance finished early and was not reset during the alotted time, cancelling running info now """
    self._logger.log(f'The {self.friendly_name.lower()} timed out after finishing early.')
    if not self.is_on:
      self._turn_off(override=True)


  def _state_change(self, entity, attribute, old, new, kwargs):
    """ Sensor value state changed - Call an update """
    if self.utils.valid_input(old, new):
      self.update(new)


  def update(self, value):
    """ Actions to take when sensor value state changes """
    raise NotImplementedError()


  def terminate(self):
    # Save the state on shutdown to restore running times on startup again
    output = {
      'running': self.is_on,
      'start': self._start_time,
      'last_checked': self._last_checked_time,
    }
    current_state = yaml.dump(output, default_flow_style=False, sort_keys=False)
    with open(self.data_file, 'w') as f:
      f.write(current_state)


CONF_RELAY = 'relay'
CONF_THRESHOLD_ON_POWER = 'threshold_on_power'
CONF_THRESHOLD_OFF_POWER = 'threshold_off_power'
CONF_THRESHOLD_EXTREME_POWER = 'threshold_extreme_power'

# THIS ONE IS WORKING AS A STAND ALONE!
# POWER_APPLIANCE_SCHEMA = {
#   CONF_START_KEY: vol.Schema(
#     {
#       vol.Required(CONF_FRIENDLY_NAME): str,
#       vol.Required(CONF_SENSOR): utils_validation.entity_id,
#       vol.Required(CONF_MONITOR_ENTITY): utils_validation.entity_id,
#       vol.Required(CONF_RUNTIME_SENOR): utils_validation.entity_id,
#       vol.Required(CONF_LAST_USED_INPUT_TEXT): utils_validation.entity_id,
#       vol.Required(CONF_MIN_RUNTIME): utils_validation.parse_star_time,
#       vol.Required(CONF_THRESHOLD_OFF_TIME): utils_validation.parse_star_time,
      
#       vol.Optional(CONF_UPDATE_FREQUENCY, default=DEFAULT_CONF_UPDATE_FREQUENCY): utils_validation.try_parse_int,
#       vol.Optional(CONF_DATA_FILE_PATH, default=None): utils_validation.entity_id,

#       vol.Required(CONF_RELAY): utils_validation.entity_id,
#       vol.Required(CONF_THRESHOLD_ON_POWER): utils_validation.try_parse_int,
#       vol.Required(CONF_THRESHOLD_OFF_POWER): utils_validation.try_parse_int,
#       vol.Required(CONF_THRESHOLD_EXTREME_POWER): utils_validation.try_parse_int,
#     },
#   )
# }

POWER_APPLIANCE_SCHEMA = {
  CONF_START_KEY: BASE_APPLIANCE_SCHEMA.extend(
    {
      vol.Required(CONF_RELAY): utils_validation.entity_id,
      vol.Required(CONF_THRESHOLD_ON_POWER): utils_validation.try_parse_int,
      vol.Required(CONF_THRESHOLD_OFF_POWER): utils_validation.try_parse_int,
      vol.Required(CONF_THRESHOLD_EXTREME_POWER): utils_validation.try_parse_int,
    },
  )
}


class PowerAppliance(ApplianceBase):

  """
  Base class for a power based appliance
  """
  APP_SCHEMA = BaseApp.APP_SCHEMA.extend(POWER_APPLIANCE_SCHEMA)

  def setup(self):
    """ This must be called by the appliance class with the appropriate config """
    super().setup()
    self.handle_timer_off = None


############ config properties #############

  @property
  def relay(self):
    """ Returns relay to this appliances """
    return self.attrs[CONF_RELAY]

  @property
  def relay_state(self):
    """ Returns the relay state """
    return self.get_state(self.relay)

  @property
  def relay_on(self):
    """ Returns true if the relay is on """
    return bool(self.relay_state == 'on')

  @property
  def threshold_on_power(self):
    """ Returns threshold_on_power to this appliances """
    return self.attrs[CONF_THRESHOLD_ON_POWER]

  @property
  def threshold_off_power(self):
    """ Returns threshold_off_power to this appliances """
    return self.attrs[CONF_THRESHOLD_OFF_POWER]

  @property
  def threshold_extreme_power(self):
    """ Returns threshold_extreme_power to this appliances """
    return self.attrs[CONF_THRESHOLD_EXTREME_POWER]


  def _extreme_power_notify(self):
    self.turn_off(self.relay)
    msg = '{} power is above {} Watts ({})! The relay has been turned off. Please have a look now!' \
            .format(self.friendly_name.lower(), THRESHOLD_EXTREME_POWER, self.sensor_state)
    self._logger.log(msg, level='WARNING')
    self.notifier.telegram_notify(msg, NOTIFY_TARGET, self.friendly_name)
    self.notifier.tts_notify(msg, speaker_override=True)
    self.notifier.persistent_notify(msg, self.friendly_name)
    self.run_in(lambda *_: self._relay_check(), 60)


  def _relay_check(self):
    """ Verify the relay is off after a high power spike """
    if self.relay_on:
      self.turn_off(self.relay)
      msg = f'The {self.friendly_name.lower()} relay is still on after an extreme power spike, attempting to shut off again'
      msg += f'The current power reading is {self.sensor_state} watts. Please have a look now!'
      self._logger.log(msg, level='WARNING')
      self.notifier.telegram_notify(msg, NOTIFY_TARGET, self.friendly_name)
      self.run_in(lambda *_: self._relay_check(), 5*60)
    else:
      msg = f'The {self.friendly_name.lower()} relay was successfully shut off after an extreme power spike.'
      self._logger.log(msg)


  def update(self, power):
    """ Adjust appliance state based on current power reading """
    try:
      power = float(power)
    except:
      self._logger.log(f'Invalid {self.friendly_name} sensor value: {power}', level='WARNING')
      return

    if self.is_on:
      if power < self.threshold_off_power and self.handle_timer_off is None:
        self.handle_timer_off = self.run_in(lambda *_: self._turn_off(), self.threshold_off_time)
      elif power > self.threshold_off_power and self.handle_timer_off is not None:
        self.cancel_timer(self.handle_timer_off)
        self.handle_timer_off = None

    if not self.is_on and power > self.threshold_on_power:
      self._turn_on()

    if power > self.threshold_extreme_power:
      self._extreme_power_notify()


  def terminate(self):
    super().terminate()
