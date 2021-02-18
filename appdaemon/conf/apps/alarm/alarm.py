"""
SETUP TODO:
  - Create counter entity
  - Add yaml config
"""

from base_app import BaseApp
import datetime
from const import CONF_LOG_LEVEL, CONF_ENTITY_ID, CONF_FRIENDLY_NAME
import utils_validation
import voluptuous as vol

# TODO:
#   - should most of this logic be in alarm_controller??
#     - This app contains the basic functionality of the alarm system, arm, disarm, trigger
#     - What occurs when alarm is triggered is the responsibility of the alarm_controller

ALARM_CODE = '5555'
ALARM_COUNTER = 'counter.ha_alarm_system_counter'
THRESHOLD_COUNTER_VALUE = 2
THRESHOLD_COUNTER_TIME = 5*60

NOTIFY_TARGET = ['Status', 'Alarm']
NOTIFY_TITLE = 'Alarm System'


CONF_START_KEY = 'alarm_settings'
CONF_LIGHT_DISABLE_STATES = 'alarm_disable_states'
CONF_MOTION_SENSORS = 'motion_sensors'
CONF_ENTRYPOINT_SENSORS = 'entrypoints'
CONF_ARMED_AWAY = 'armed_away'
CONF_ARMED_HOME = 'armed_home'
CONF_ARMED_NIGHT = 'armed_night' 
CONF_ARMED = 'armed'

CONF_DELAYED_TIMER = 'delayed_timer'
CONF_DELAYED_COUNTER = 'delayed_counter'
CONF_DELAYED_COUNTER_TIMER = 'delayed_counter_timer'
CONF_IMMEDIATE = 'immediate'

CONF_DEFAULT_LOG_LEVEL = 'DEBUG'


def alarm_validation(candidate):
  if not candidate:
    return None

  if ',' in candidate:
    parts = candidate.split(',')
    if len(parts) == 2 and parts[1].strip().isdigit() and parts[0] in [CONF_DELAYED_TIMER, CONF_DELAYED_COUNTER_TIMER]:
      return candidate
  else:
    parts = candidate.split(' ')
    if len(parts) == 1 and parts[0] in [CONF_DELAYED_COUNTER, CONF_IMMEDIATE]:
      return candidate
  
  raise vol.Invalid(f"Invalid alarm configuration: {candidate} ({candidate.split(',')[1].strip().isdigit()})")


ALARM_NESTED_SCHEMA = vol.Schema(
    {
      vol.Required(CONF_ENTITY_ID): utils_validation.entity_id_list,
      vol.Optional(CONF_ARMED, default=None): alarm_validation,
      vol.Optional(CONF_ARMED_AWAY, default=None): alarm_validation,
      vol.Optional(CONF_ARMED_HOME, default=None): alarm_validation,
      vol.Optional(CONF_ARMED_NIGHT, default=None): alarm_validation,
    }
  )


ALARM_SCHEMA = {
  CONF_START_KEY: vol.Schema(
    {str: vol.Schema(
        {
          vol.Optional(CONF_FRIENDLY_NAME): str,
          vol.Optional(CONF_LOG_LEVEL, default=CONF_DEFAULT_LOG_LEVEL): str,
          vol.Optional(CONF_LIGHT_DISABLE_STATES, default=None): utils_validation.ensure_constraint_list,

          vol.Optional(CONF_MOTION_SENSORS): ALARM_NESTED_SCHEMA,
          vol.Optional(CONF_ENTRYPOINT_SENSORS): ALARM_NESTED_SCHEMA,
        }
      ),
    })
  }

class Alarm(BaseApp):
  
  APP_SCHEMA = BaseApp.APP_SCHEMA.extend(ALARM_SCHEMA)

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.notifier = self.get_app('notifier')

    self.debug_level = 'DEBUG'
    self._is_setup = False
    self.trigger_entities = []
    self.handle_list = []
    self.last_counter_time = None
    self.handle_reset_counter = None
    self.motion_sensors = {}
    self.entrypoints = {}

    self.listen_state(self._counter_state_change, ALARM_COUNTER)

    # These are needed for manual arming/disarming 
    self.listen_state(self._armed_home_callback, self.const.ALARM_CONTROL_PANEL, new='armed_home')
    self.listen_state(self._armed_away_callback, self.const.ALARM_CONTROL_PANEL, new='armed_away')
    self.listen_state(self._armed_night_callback, self.const.ALARM_CONTROL_PANEL, new='armed_night')
    self.listen_state(self._disarmed_callback, self.const.ALARM_CONTROL_PANEL, new='disarmed')

    # TODO: Process config and save in self.motion_sensors & self.entrypoints
    self.run_in(lambda *_: self._process_cfg(self.cfg), 1)
    self.run_in(lambda *_: self._setup_alarm(), 2)


  def _process_cfg(self, config):
    """ Prep yaml data - Ensure we keep integrety of original data """
    import copy
    cfg = copy.deepcopy(config[CONF_START_KEY])

    for name, data in cfg.items():
      if CONF_MOTION_SENSORS in data:
        self.motion_sensors[name] = data[CONF_MOTION_SENSORS]
        # self._logger.log(f'Motion sensor: {data}')
      if CONF_ENTRYPOINT_SENSORS in data:
        self.entrypoints[name] = data[CONF_ENTRYPOINT_SENSORS]
        # self._logger.log(f'Entrypoint sensor: {data}')

      
    self._is_setup = True

    # self._logger.log(f'Setup alarm entities')
    # self._logger.log(f'Motion sensors: {self.motion_sensors}')
    # self._logger.log(f'Entrypoint sensors: {self.entrypoints}')


  def _setup_alarm(self):
    """ Sync alarm to current state on Restart/Reboot """
    if self.armed_away:
      self._start_armed_away_listeners()
    elif self.armed_home:
      self._start_armed_home_listeners()
    elif self.armed_night:
      self._start_armed_night_listeners()
    elif self.triggered:
      pass

    self._setup = True


  @property
  def is_setup(self):
    """ Returns if the alarm system is setup and ready to do """
    return self._is_setup

  @property
  def state(self):
    return self.get_state(self.const.ALARM_CONTROL_PANEL)

  @property
  def armed(self):
    return (self.armed_away or self.armed_home or self.armed_night)

  @property
  def armed_away(self):
    return self.alarm_in_state('armed_away')

  @property
  def armed_home(self):
    return self.alarm_in_state('armed_home')

  @property
  def armed_night(self):
    return self.alarm_in_state('armed_night')

  @property
  def disarmed(self):
    return self.alarm_in_state('disarmed')

  @property
  def pending(self):
    return self.alarm_in_state('pending')

  @property
  def triggered(self):
    return self.alarm_in_state('triggered')

  @property
  def counter_count(self):
    return int(self.get_state(ALARM_COUNTER))

  def alarm_in_state(self, state):
    return (self.state == state)


  def trigger(self, kwargs=None):
    if self.armed:
      message = f'Alarm ("{self.state}") triggered by the "{self.trigger_entities}".'
      self._logger.log(message, level='INFO')
      self.notifier.telegram_notify(message, NOTIFY_TARGET, NOTIFY_TITLE)
      self.call_service("alarm_control_panel/alarm_trigger", entity_id=self.const.ALARM_CONTROL_PANEL)
      self._reset_counter()
      self._stop_listeners() # Needed for when alarm is triggered -> pending -> armed
      self._logger.log(self.get_state(self.const.ALARM_CONTROL_PANEL, attribute='all'))
      if self.noone_home() or self.now_is_between('8:00:00', '20:00:00'):
        self.notifier.tts_notify(f'The alarm system has been triggered. The police will notified. Please leave the house immediately.', volume=0.6, speaker_override=True, no_greeting=True)
    else:
      self._logger.log(f'Alarm trigger() called but the system is {self.state}.', level='INFO')


  def arm_home(self): 
    if self.disarmed:
      self._logger.log(f'Home alarm system is arming home now', level='DEBUG')
      self.call_service('alarm_control_panel/alarm_arm_home', entity_id=self.const.ALARM_CONTROL_PANEL, code=ALARM_CODE)


  def _armed_home_callback(self, entity, attribute, old, new, kwargs):
    self._logger.log('Alarm is armed_home.', level='DEBUG')
    self._start_armed_home_listeners()


  def arm_away(self):
    if self.disarmed:
      msg = 'The house alarm system is arming away. It will set in 30 seconds if not over ridden.'
      self.notifier.tts_notify(msg)
      self._logger.log(msg, level='INFO')
      self.call_service('alarm_control_panel/alarm_arm_away', entity_id=self.const.ALARM_CONTROL_PANEL, code=ALARM_CODE)


  def _armed_away_callback(self, entity, attribute, old, new, kwargs):
    self._logger.log('Alarm is armed_away.', level='DEBUG')
    self._start_armed_away_listeners()


  def arm_night(self):
    if self.disarmed:
      self._logger.log(f'Home alarm system is arming night now', level='DEBUG')
      self.call_service('alarm_control_panel/alarm_arm_night', entity_id=self.const.ALARM_CONTROL_PANEL, code=ALARM_CODE)


  def _armed_night_callback(self, entity, attribute, old, new, kwargs):
    self._logger.log('Alarm is armed_night.', level='DEBUG')
    self._start_armed_night_listeners()


  def disarm(self):
    if not self.disarmed:
      self._logger.log(f'Home alarm system is disarming now', level='DEBUG')
      self.call_service('alarm_control_panel/alarm_disarm', entity_id=self.const.ALARM_CONTROL_PANEL, code=ALARM_CODE)


  def _disarmed_callback(self, entity, attribute, old, new, kwargs):
    self._logger.log('Alarm is disarmed.', level='DEBUG')
    self._stop_listeners()


  def _increment_counter(self):
    self.call_service('counter/increment', entity_id=ALARM_COUNTER)
    self.last_counter_time = datetime.datetime.now()
    self._logger.log(f'Counter incremented to {self.counter_count}.', level='DEBUG')


  def _reset_counter(self, kwargs=None):
    self._logger.log('Counter reset.', level='DEBUG')
    self.call_service('counter/reset', entity_id=ALARM_COUNTER)
    self.cancel_timer(self.handle_reset_counter)
    self.trigger_entities = []


  def _counter_state_change(self, entity, attribute, old, new, kwargs):
    if self.utils.valid_input(old, new):
      if 0 < int(new) < THRESHOLD_COUNTER_VALUE:
        self._logger.log(f'Counter is now at {new}, and will reset in {THRESHOLD_COUNTER_TIME} seconds if the threshold of {THRESHOLD_COUNTER_VALUE} is not reached.', level='DEBUG')
        self.cancel_timer(self.handle_reset_counter)
        self.handle_reset_counter = self.run_in(self._reset_counter, THRESHOLD_COUNTER_TIME)
      elif int(new) >= THRESHOLD_COUNTER_VALUE:
        self._logger.log(f'Counter reached limit of {THRESHOLD_COUNTER_VALUE} ("{new}"), alarm is triggering.', level='INFO')
        self.trigger()
        self.cancel_timer(self.handle_reset_counter)
        self.handle_reset_counter = None

    # Failsafe to reset/trigger using last_counter_time
    if self.counter_count > THRESHOLD_COUNTER_VALUE:
      if not self.last_counter_time:
        self._reset_counter()
      elif datetime.datetime.now() - self.last_counter_time > datetime.timedelta(minutes=5):
        self._reset_counter()
      else:
        self.trigger()


  def _trigger_delayed_counter(self, entity, attribute, old, new, kwargs):
    """ Trigger actions for entrypoints """
    if self.utils.valid_input(old, new):
      self._logger.log(f'{entity} was triggered and will increment the counter. locals: {locals()}', level='INFO')
      self.trigger_entities.append(self.friendly_name(entity))
      self._increment_counter()


  def _trigger_immediate(self, entity, attribute, old, new, kwargs):
    """ Trigger actions for garage door """
    self._logger.log(f'_trigger_immediate called by {entity}')
    if self.utils.valid_input(old, new):
      self._logger.log(f'{entity} was triggered and will increment the counter. locals: {locals()}', level='INFO')
      self.trigger_entities.append(self.friendly_name(entity))
      self.trigger()


  def _register_alarm_entity(self, entity, alarm_settings, new, old=None):
    """ Parse the settings alarm config and register the entity accordingly 
    
    param entity: HA entity_id
    param alarm_settings: Settings config containing delayed_timer, delayed_counter, or immediate ({} will result in nothing registered)
    param new: Callback state required for entity to transition to fire event
    param old: Callback state required for entity to previously be in to fire event 
    """
    dur = 0
    if CONF_DELAYED_COUNTER_TIMER in alarm_settings:
      # TODO: Add counter & timer combo logic
      pass
    elif CONF_DELAYED_TIMER in alarm_settings:
      parts = alarm_settings.strip().split(',')
      dur = int(parts[1])
      callback = self._trigger_immediate
    elif CONF_DELAYED_COUNTER in alarm_settings:
      callback = self._trigger_delayed_counter
    elif CONF_IMMEDIATE in alarm_settings:
      callback = self._trigger_immediate
    else:
      return

    self._logger.log(f'Registering new alarm entity: {entity}, old: {old}, new: {new}, duration: {dur}, callback: {callback}', level='DEBUG')
    self.handle_list.append(self.listen_state(callback, entity, old=old, new=new, duration=dur))


  def _register_alarm_category(self, config, alarm_type, new, old=None):
    """ Register all entities in category (ex: entrypoints, motion_sensors, etc)
    param config: Settings config for category entrypoints, motion_sensors, etc
    param alary_type: armed_home, armed_away, armed_night, etc as a String
    """
    for data in config.values():
      alarm_settings = data.get(alarm_type, None) or data.get(CONF_ARMED, None)
      entity_ids = data.get(CONF_ENTITY_ID)
      if alarm_settings:
        for e in entity_ids:
          self._register_alarm_entity(e, alarm_settings, new, old)
      else:
        self._logger.log(f'Entity ({entity_ids}) does not contain {alarm_type} config, it will not be registered.', level='DEBUG')


  def _start_armed_home_listeners(self):
    """ This is for home and awake """
    self._logger.log('Setting up armed home listeners.', level='DEBUG')
    self._register_alarm_category(self.entrypoints, 'armed_home', 'on', 'off')
    # self._register_alarm_entity(FRONT_DOOR_LOCK_SENSOR, 'immediate', new='161') # code for 'tamper alarm'


  def _start_armed_away_listeners(self):
    """ This is for not home """
    self._logger.log('Setting up armed away listeners.', level='DEBUG')
    self._start_armed_home_listeners()

    # Might need this if Squirtly trigger alarm when away
    if self.get_state(self.const.PET_MODE_BOOLEAN) == 'off':
      self._register_alarm_category(self.motion_sensors, 'armed_away', 'on', 'off')
    else:
      self._logger.log('Pet mode is turned on, alarm armed away motion sensors will not be used for alarm detection.', level='DEBUG')


  def _start_armed_night_listeners(self):
    """ This is for home and asleep """
    self._logger.log('Setting up armed night listeners.', level='DEBUG')
    self._register_alarm_category(self.entrypoints, 'armed_night', 'on', 'off')
    # self._register_alarm_entity(FRONT_DOOR_LOCK_SENSOR, 'immediate', new='161') # code for 'tamper alarm'


  def _stop_listeners(self):
    """ Unregister all entities for the current alarm (i.e. Disarm the alarm system) """
    self._logger.log('Listeners stopped.', level='DEBUG')
    for handle in self.handle_list:
      self.cancel_listen_state(handle)
    self.handle_list = []


  def terminate(self):
    pass

  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing Alarm Module: ')  
    # self.arm_night()


    
