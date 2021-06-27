"""
TODO: 
  - Add in config check for colour/dimable and warn  user that some options are not available when the bulb isnt colour/dimable

Various options: (TODO)
  - circadian
  - vacation
  - scheduled
  - transitional (ramping)
  - 

CHANGE_LOG:
  - April 6 - line 282 removed need to redundencly add aliases like study_light & study light.
"""


from base_app import BaseApp
import utils_validation
from const import CONF_FRIENDLY_NAME, CONF_ALIASES, CONF_ENTITY_ID, CONF_OPTIONS, CONF_DEFAULTS, CONF_PROPERTIES
import circadian

import datetime
import voluptuous as vol

# CONF_FRIENDLY_NAME = 'friendly_name'
# CONF_SENSORS = 'sensors'
# CONF_ALIASES = 'aliases'
# CONF_ENTITY_ID = 'entity_id'
# CONF_OPTIONS = 'options'
# CONF_DEFAULTS = 'defaults'
# CONF_PROPERTIES = 'properties'

CONF_START_KEY = 'lights'

CONF_LOG_LEVEL = 'log_level'
CONF_LIGHT_DISABLE_STATES = 'light_disable_states'
CONF_LIGHT_ENABLED_BOOLEAN_TRACKER = 'enabled_boolean_tracker'
CONF_TAKE_OVER_CONTROL = 'take_over_control'          # When True, the light will be disable when manually turned on (or adjusted [NOT MIMPLEMENTED YET!!!])
CONF_DETECT_NON_HA_CHANGES = 'detect_non_ha_changes' # Currently does nothing

CONF_SWITCH_ENTITY_ID = 'switch_entity_id'
CONF_PARENT_LIGHT = 'parent_light'
CONF_CHILD_LIGHTS = 'child_lights'
CONF_CHILD_BULBS = 'child_bulbs'

CONF_SLEEP_CONDITION = 'sleep_condition'
CONF_SLEEP_TRANSITION = 'sleep_transition'
CONF_SLEEP_BRIGHTNESS = 'sleep_brightness'
CONF_SLEEP_COLOUR = 'sleep_colour'
CONF_SLEEP_LIGHTS = 'sleep_lights'

CONF_USE_CIRCADIAN = 'use_circadian'
CONF_USE_DARK_MODE = 'use_dark_mode'
CONF_USE_HOLIDAYS = 'use_holidays'
CONF_USE_SEASONS = 'use_seasons'
CONF_USE_LUX = 'use_lux'
CONF_LUX_THRESHOLD = 'lux_threshold'
CONF_USE_COLOUR_LOOP = 'use_colour_loop'
CONF_USE_RANDOM_COLOURS = 'use_random_colours'
CONF_SCENE = 'scene'

CONF_DAY_THRESHOLDS = 'day_threshold_times'
CONF_MORNING = 'morning'
CONF_DAY = 'day'
CONF_NIGHT = 'night'

CONF_TRANSITION = 'transition'
CONF_BRIGHTNESS = 'brightness'
CONF_COLOUR = 'colour'

CONF_IS_COLOUR = 'is_colour'
CONF_IS_DIMABLE = 'is_dimable'

CONF_DEFAULT_LOG_LEVEL = 'NOTSET'
CONF_DEFAULT_TRANSITION = 1
CONF_DEFAULT_BRIGHTNESS = 100
CONF_DEFAULT_COLOUR = 'white'
CONF_DEFAULT_LUX_THRESHOLD = 100

CONF_DEFAULT_MORNING = '6:00:00'
CONF_DEFAULT_DAY = '11:00:00'
CONF_DEFAULT_NIGHT = '22:00:00'

CONF_DEFAULT_DAY_THRESHOLDS = {
  CONF_MORNING: CONF_DEFAULT_MORNING,
  CONF_DAY: CONF_DEFAULT_DAY,
  CONF_NIGHT: CONF_DEFAULT_NIGHT
}

# Morning, day, night schema that take of different types (int, str, time)
TIME_SCHEMA_INT = vol.Schema(
    {
      vol.Required(CONF_MORNING): utils_validation.try_parse_int,
      vol.Required(CONF_DAY): utils_validation.try_parse_int,
      vol.Required(CONF_NIGHT): utils_validation.try_parse_int,
    }
  )
TIME_SCHEMA_STR = vol.Schema(
    {
      vol.Required(CONF_MORNING): utils_validation.try_parse_str,
      vol.Required(CONF_DAY): utils_validation.try_parse_str,
      vol.Required(CONF_NIGHT): utils_validation.try_parse_str,
    }
  )
TIME_SCHEMA_TIME = vol.Schema(
    {
      vol.Required(CONF_MORNING, default=CONF_DEFAULT_MORNING): utils_validation.ensure_time,
      vol.Required(CONF_DAY, default=CONF_DEFAULT_DAY): utils_validation.ensure_time,
      vol.Required(CONF_NIGHT, default=CONF_DEFAULT_NIGHT): utils_validation.ensure_time,
    }
  )

# Properties of given light
PROPERTIES_SCHEMA = vol.Schema(
  {
    vol.Optional(CONF_USE_DARK_MODE, default=None): utils_validation.entity_id,
    vol.Optional(CONF_USE_LUX, default=None): utils_validation.entity_id,
    vol.Optional(CONF_LUX_THRESHOLD, default=CONF_DEFAULT_LUX_THRESHOLD): int,

    vol.Optional(CONF_SLEEP_CONDITION, default=[]): utils_validation.ensure_constraint_list,
    vol.Optional(CONF_SLEEP_LIGHTS, default=[]): utils_validation.entity_id_list,
    vol.Optional(CONF_SLEEP_TRANSITION, default=None): utils_validation.try_parse_int,
    vol.Optional(CONF_SLEEP_BRIGHTNESS, default=None): utils_validation.try_parse_int,
    vol.Optional(CONF_SLEEP_COLOUR, default=None): utils_validation.try_parse_int,

    vol.Optional(CONF_DAY_THRESHOLDS, default=CONF_DEFAULT_DAY_THRESHOLDS): TIME_SCHEMA_TIME,
    vol.Optional(CONF_TRANSITION, default=CONF_DEFAULT_TRANSITION): vol.Any(int, TIME_SCHEMA_INT),
    vol.Optional(CONF_BRIGHTNESS, default=CONF_DEFAULT_BRIGHTNESS): vol.Any(int, TIME_SCHEMA_INT),
    vol.Optional(CONF_COLOUR, default=CONF_DEFAULT_COLOUR): vol.Any(str, TIME_SCHEMA_STR),
  }
)

# Light operation mode options - This needs to maintain order so user can define functionality base on order
OPTION_SCHEMA = vol.Schema(
  {
    vol.Optional(CONF_USE_CIRCADIAN, default=False): bool,
    vol.Optional(CONF_USE_HOLIDAYS, default=False): bool,
    vol.Optional(CONF_USE_SEASONS, default=False): bool,
    vol.Optional(CONF_USE_COLOUR_LOOP, default=False): bool,
    vol.Optional(CONF_USE_RANDOM_COLOURS, default=False): bool,
    vol.Optional(CONF_SCENE, default=''): vol.Any(str, TIME_SCHEMA_STR),
  }
)

# Master light schema
LIGHT_SCHEMA = {
  CONF_START_KEY: vol.Schema(
    {str: vol.Schema(
        {
          vol.Optional(CONF_FRIENDLY_NAME): str,
          vol.Optional(CONF_ALIASES): utils_validation.ensure_list,

          vol.Required(CONF_ENTITY_ID): utils_validation.entity_id,
          vol.Optional(CONF_SWITCH_ENTITY_ID, default=None): utils_validation.entity_id,
          vol.Optional(CONF_PARENT_LIGHT, default=None): utils_validation.try_parse_str,
          vol.Optional(CONF_CHILD_LIGHTS, default=[]): utils_validation.entity_id_list,
          vol.Optional(CONF_CHILD_BULBS, default=[]): utils_validation.entity_id_list,

          vol.Optional(CONF_LOG_LEVEL, default=CONF_DEFAULT_LOG_LEVEL): str,
          vol.Optional(CONF_LIGHT_DISABLE_STATES, default=[]): utils_validation.ensure_constraint_list,
          vol.Optional(CONF_LIGHT_ENABLED_BOOLEAN_TRACKER, default=None): utils_validation.entity_id,
          vol.Optional(CONF_TAKE_OVER_CONTROL, default=True): bool,
          vol.Optional(CONF_DETECT_NON_HA_CHANGES, default=True): bool,

          vol.Optional(CONF_PROPERTIES): PROPERTIES_SCHEMA,
          vol.Optional(CONF_OPTIONS): OPTION_SCHEMA,
        }
      ),
    })
  }


class LightController(BaseApp):

  APP_SCHEMA = BaseApp.APP_SCHEMA.extend(LIGHT_SCHEMA)

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')
    # self.listen_state(self.test2, 'input_boolean.ad_testing_2')
    # self.listen_state(self.test3, 'input_boolean.ad_testing_3')

    self.seasons = self.get_app('seasons')

    # Load in data from config
    self._light_data = {}
    self._lights_obj = {}
    self._process_cfg(self.cfg)
    self._setup_lights(self._light_data)


  def _is_colour(self, light):
    try:
      return self.get_state(light, attribute='all')['attributes'].get('min_mireds', None) is not None
    except TypeError as e:
      # Light does not exists?
      self._logger.log(f'Failed to check if light _is_colour ("{light}"): {e}')
    return False
    

  def _is_dimable(self, light):
    try:
      return len(self.get_state(light, attribute='all')['attributes']) > 1
    except TypeError as e:
      # Light does not exists?
      self._logger.log(f'Failed to check if light _is_dimable ("{light}"): {e}')
    return False
  

  def _process_cfg(self, config):
    """ Prep yaml data - Ensure we keep integrety of original data """
    import copy
    cfg = copy.deepcopy(config[CONF_START_KEY])

    for name, data in cfg.items():
      eid = data[CONF_ENTITY_ID]
      self._light_data[eid] = data 

      # Set default options/property value if nothing is defined
      if CONF_PROPERTIES not in self._light_data[eid]:
        self._light_data[eid][CONF_PROPERTIES] = PROPERTIES_SCHEMA({})
      if CONF_OPTIONS not in self._light_data[eid]:
        self._light_data[eid][CONF_OPTIONS] = OPTION_SCHEMA({})

      # Add the room name to aliases (add aliases if it doesnt exists)
      self._light_data[eid].setdefault(CONF_ALIASES, []).append(name)

      # Set sensor friendly name to room if not declared in config
      if CONF_FRIENDLY_NAME not in self._light_data[eid]:
        self._light_data[eid][CONF_FRIENDLY_NAME] = name.replace('_', ' ').title()

      # Setup default enabled boolean tracker if not specified
      if CONF_LIGHT_ENABLED_BOOLEAN_TRACKER not in self._light_data[eid] or self._light_data[eid][CONF_LIGHT_ENABLED_BOOLEAN_TRACKER] is None:
        tracker_boolean = 'input_boolean.' + eid.replace('.', '_') + '_tracker'
        self._light_data[eid][CONF_LIGHT_ENABLED_BOOLEAN_TRACKER] = tracker_boolean
      if not self.entity_exists(self._light_data[eid][CONF_LIGHT_ENABLED_BOOLEAN_TRACKER]):
        self.create_input_boolean(tracker_boolean)
        # self.turn_on(tracker_boolean) # Do not use set_state because it will create the boolean in the wrong way if its not created yet MAYBE??????

      # Add if colour & dimable are available for this light. Saves checking continuously later
      self._light_data[eid][CONF_IS_COLOUR] = self._is_colour(data[CONF_ENTITY_ID])
      self._light_data[eid][CONF_IS_DIMABLE] = self._is_dimable(data[CONF_ENTITY_ID])

      # sleep_lights == entity_id when it isn't defined
      if not data.get(CONF_SLEEP_LIGHTS, []):
        self._light_data[eid][CONF_PROPERTIES][CONF_SLEEP_LIGHTS] = [data[CONF_ENTITY_ID]]


  def _setup_lights(self, config):
    """ Setup all lights """
    self._lights_obj = {}
    for name, settings in config.items():
      self._lights_obj[name.lower()] = Light(self, settings)


  def is_on(self, entity=None):
    """ Check if a light is on, default check is all lights """
    if entity is not None:
      return bool(self.get_state(entity) == 'on')

    # Default is to check all lights
    return len(self.lights_on_list()) > 0


  def light_check(self):
    """ Returns a human readable message with the lights that are on as a string of friendly_names """
    open = [self.friendly_name(l) for l in self.lights_on_list()]

    if len(open) == 0:
      result = "All the lights are off"
    else:
      result = self.utils.list_to_pretty_print(open, 'on')

    return result.lower().capitalize()


  def lights_on_list(self):
    """ Return a list of lights that are on """
    on = []
    for name, lt_obj in self._lights_obj.items():
      entity_id = lt_obj.entity_id
      if entity_id is not None and self.get_state(entity_id) == 'on':
        on.append(entity_id)
    return on


  def map_light_to_entity(self, light):
    """ Return the entity id of light based on alias if it exists """
    if not light:
      return light
    for lt in self._light_data.values():
      if light.lower() in lt[CONF_ALIASES]:
        return lt[CONF_ENTITY_ID]
      if light.lower() == lt[CONF_SWITCH_ENTITY_ID]:
        return lt[CONF_ENTITY_ID]
      if light.lower().replace(' ', '_') in lt[CONF_ALIASES]:
        return lt[CONF_ENTITY_ID]
    return light

  
  def map_to_light(self, light):
    """ Return the common name of the light (Used for accessing light object) """
    if not light:
      return light
    for name, data in self._light_data.items():
      if light.lower() == name: return name
      if light.lower() == data[CONF_ENTITY_ID]: return name
      if light.lower() == data[CONF_SWITCH_ENTITY_ID]: return name
      if light.lower() in data[CONF_ALIASES]:
        return name
    return light


  def disable_light(self, light, enable_entity=None, enable_state=None):
    """ If defined, used enable_entity & enable_state to re-enable light when entity enters specified state """
    if isinstance(light, str):
      light = [light]
    
    for lt in light:
      entity = self.map_light_to_entity(lt)
      light_obj = self._lights_obj.get(entity, None)
      if light_obj:
        light_obj.disable_light()
      else:
        self._logger.log(f'Could not find light object for {entity} ({lt}). It will not be disabled.', level='WARNING')

    if any([enable_entity, enable_state]):
      if enable_entity is not None and enable_state is not None:
        # Only run this listen once, than cancel it (onshot=True)
        self.listen_state(lambda *_: self.enable_light(light), enable_entity, new=enable_state, oneshot=True)
      else:
        self._logger.log(f'enable_entity ({enable_entity}) and enable_state ({enable_state}) are both required.')


  def enable_light(self, light):
    if isinstance(light, str):
      light = [light]
    
    for lt in light:
      entity = self.map_light_to_entity(lt)
      light_obj = self._lights_obj.get(entity, None)
      if light_obj:
        light_obj.enable_light()
      else:
        self._logger.log(f'Could not find light object for {entity} ({lt}). It will not be enabled.', level='WARNING')


  def turn_light_on(self, light, colour=None, brightness=None, transition=None, scene=None, override=False):
    if isinstance(light, str):
      light = [light]
    
    for lt in light:
      entity = self.map_light_to_entity(lt)
      light_obj = self._lights_obj.get(entity, None)
      if light_obj:
        light_obj.turn_light_on(colour, brightness, transition, scene, override)
      else:
        if not self.entity_exists(lt):
          self._logger.log(f'Could not find light object for {entity} ({lt}). No valid entity id was found and nothing will be turned on.', level='WARNING')
        else:
          self._logger.log(f'Could not find light object for {entity} ({lt}). Turning on light to previous state using self.turn_on().', level='WARNING')
          self.turn_on(lt)


  def turn_all_off(self):
    """ Turn off all lights in the house 
    USE WITH CAUTION, this will turn off all lights regardless of state or settings 
    """
    self._logger.log(f'Turning off all house lights')
    self.turn_off('light.all_hue_lights')

    # Turn off all switches
    for name, lt in self._lights_obj.items():
      if lt.entity_id.startswith('switch.'):
        # lt.turn_light_off(override=True)
        self.turn_off(lt.entity_id)
      if lt.entity_id.startswith('light.') and not lt.is_colour:
        # Dimable switches don't have colour but are light. entities
        # lt.turn_light_off(override=True)
        self.turn_off(lt.entity_id)
    

  def turn_light_off(self, light, transition=None, override=False):
    if isinstance(light, str):
      light = [light]
    
    for lt in light:
      entity = self.map_light_to_entity(lt)
      light_obj = self._lights_obj.get(entity, None)
      if light_obj:
        light_obj.turn_light_off(transition, override)
      else:
        if not self.entity_exists(lt):
          self._logger.log(f'Could not find light object for {entity} ({lt}). No valid entity id was found and nothing will be turned off.', level='WARNING')
        else:
          self._logger.log(f'Could not find light object for {entity} ({lt}). Turning on light to previous state using self.turn_off().', level='WARNING')
          self.turn_off(lt)


  def toggle_light(self, light, colour=None, brightness=None, transition=None, scene=None, override=False):
    if isinstance(light, str):
      light = [light]
    
    for lt in light:
      entity = self.map_light_to_entity(lt)
      light_obj = self._lights_obj.get(entity, None)
      if light_obj:
        light_obj.toggle_light(colour, brightness, transition, scene, override)
      else:
        if not self.entity_exists(lt):
          self._logger.log(f'Could not find light object for {entity} ({lt}). No valid entity id was found and nothing will be toggled.', level='WARNING')
        else:
          self._logger.log(f'Could not find light object for {entity} ({light}). Toggling light using self.toggle().', level='WARNING')
          self.toggle(light)


  # def terminate(self):
  #   # this should be required but strange things are happening....
  #   for lt in self._lights_obj.values():
  #     lt.cleanup()


  def test(self, entity, attribute, old, new, kwargs):
    self.log(f'Testing Light Module: ') 
    self.turn_light_on('study', brightness=10)

    # self.toggle_light('light.master_fan_light')

    # res = self.get_state('switch.kitchen_ceiling', attribute='all')
    # res = self.map_light_to_entity('kitchen')
    # self._logger.log(f'Light -> Entity: {res}')
    # res = self.map_to_light('kitchen')
    # self._logger.log(f'Input -> Alias: {res}')

    # lt = 'light.laundry_room'
    # entity = self.map_light_to_entity(lt)
    # light_obj = self._lights_obj.get(entity, None)

    # b = light_obj.brightness
    # self._logger.log(f'Brightness: {b}')
    # b = light_obj.is_dimable
    # self._logger.log(f'Dimable: {b}')

    
    self.turn_light_on('light.hue_lightstrip_plus_1', colour=[183,200,255], brightness=20)



# THIS METHOD DOESNT SEEM TO WORK... THEY ALWAY SAY ALEX DID IT...
USER_IDS = {
  'b25e09129e7c46958a247eeab90aaf0f': 'Alex',
  '04b3e09b0b90422786adc60b416fef28': 'Steph',
  '57faec120897443b909532edd1b2cb22': 'Google Cast',
}


# Event name for messaging between parent and children lights
RELATED_LIGHTS_EVENT = 'lights.related'
# Max number of tries for verifying if a light is in the correct state after performing an action (on/off)
MAX_LIGHT_CALLBACK_CHECKS = 5

class Light:
  """ 

  """

  def __init__(self, app, config):
    self.app = app                                # AD app instance
    self._logger = self.app._logger

    self.attrs = config

    self._update_required = False                 # Internal flag to signal update required on next turn_on call
    self._enabled = True                          # Flag used to manually disable/enable light

    self._seasonal_scene = None                   # The scene for the season if use_seasons in use
    self._holiday_scene = None                    # The scne for the holiday if use_holidays in use

    self._prevent_manual_adjustments = False      # Keep track of the light being turned on/off by manually (physically or from UI)
    self._should_be_on = False                    # If the light should be on based on AD calls to on/off
    self._related_light_is_on = False             # Child or parent light is on
    self._bulb_is_on = False                      # Physical state of light using get_state and than callback to track state
    self._switch_is_on = False                    # Physical state of switch paired with hue if defined
    self._first_off_cycle_complete = False        # The first 'on' -> 'off' must be complete before we can reliably track lights changing colour manually

    self._previous_light_state = {}               # Expected current light state (used to compare when changes make for disabling automated mode)
    self._handle_light_check = None               # Check that the light is in the correct state
    self._handle_repeat_light_on = None           # Repeat the light turn_on call to make sure it set the correct settings (brightness, etc)
    self._check_count = 0                         # Number of times trying to verify light is in correct state
    self._next_check_time = 1                     # Number of second before next light state check

    # Store various listener handles
    self._state_handles = []
    self._event_handles = []
    self._sched_handles = []

    self._setup()


  def _setup(self):
    # Initially sync app with current light state
    state = self.app.get_state(self.entity_id)
    if state == 'on':
      self._bulb_is_on = True
      self._should_be_on = True
    elif state == 'off':
      self._bulb_is_on = False
      self._should_be_on = False
    else:
      self._logger.log(f'[{self.friendly_name}] {self.entity_id} is in an unknown state during startup, current state: "{state}".', level='WARNING', notify=False)

    # Initially sync app switch state if there is a switch/hue bulb pair
    if self.switch_entity_id:
      state = self.app.get_state(self.switch_entity_id)
      if state and state == 'on':
        self._switch_is_on = True
      elif state and state == 'off':
        self._switch_is_on = False
      else:
        self._logger.log(f'[{self.friendly_name}] {self.switch_entity_id} is in an unknown state during startup, current state: "{state}".', level='WARNING', notify=False)

    # Listen for related lights signaling this light if they exists
    if self.parent_light or self.child_lights:
      self._event_handles.append(
        self.app.listen_event(self._related_lights_callback, RELATED_LIGHTS_EVENT, device=self.name.lower().replace(' ','_')))

    # Register listeners for this light (and switch if defined)
    self._state_handles.append(self.app.listen_state(self._light_callback, self.entity_id, attribute='all'))
    if self.switch_entity_id:
      self._state_handles.append(self.app.listen_state(self._light_callback, self.switch_entity_id))

    # Setup listeners for dark_mode & sleep state changes to force update when they change state
    if self.use_dark_mode is not None:
      # self._state_handles.append(self.app.listen_state(self._entity_state_change_cb, self.use_dark_mode))
      self._state_handles.append(self.app.listen_state(lambda *_: self.turn_light_off(), self.use_dark_mode, new='off'))
    if self.sleep_condition is not None:
      # self._state_handles.append(self.app.listen_state(self._entity_state_change_cb, self.sleep_condition_entity))
      self._state_handles.append(self.app.listen_state(lambda *_: self.turn_light_off(), self.sleep_condition_entity, new='on'))


  def _sync_lights(self, state):
    """ 
    Do any book keeping & signal parent/child lights of state change (via events)

    param state: The state this light is in (True/False)
    """
    # self._logger.log(f'[{self.name}] Setting _should_be_on to : {state}', level='NOTSET')
    self._should_be_on = state
    self._previous_light_state = self.app.get_state(self.entity_id, attribute='all')
    
    if self.parent_light:
      self._logger.log(f'Firing parent event for "{self.parent_light}" from "{self.name}".', level='DEBUG')
      self.app.fire_event(RELATED_LIGHTS_EVENT, device=self.parent_light, should_be_on=state)
    elif self.child_lights:
      for lt in self.child_lights:
        self._logger.log(f'Firing child event for "{self.child_lights}" from "{self.name}".', level='NOTSET')
        self.app.fire_event(RELATED_LIGHTS_EVENT, device=lt, should_be_on=state)
    else:
      # No related lights exist for this light
      return
    self._related_light_is_on = state


  def _should_adjust(self, override, turning_on):
    """ Whether this light should be adjusted or not. Override - will bypass everthing except for manually disabling """
    if not self.light_enabled:
      self._logger.log(f'{self.name} light has manual enabled boolean set to OFF.', level=self.log_level)
      return False

    if isinstance(override, bool) and override:
      self._logger.log(f'{self.name} was called with override set to: {override} (turning_on: {turning_on}).', level=self.log_level)
      return True

    # TODO: Check if a parent light is "preventing manual adjustments"???? How to handle Parent/Child relationshit in this situation?
    if self._prevent_manual_adjustments and self.take_over_control:
      self._logger.log(f'{self.name} light has "take over control" enable and was switched on physically, from the UI, or from GA.', level=self.log_level)
      return False
  
    if not self._enabled:
      self._logger.log(f'{self.name} light is currently disabled.', level=self.log_level)
      return False

    if self.get_brightness() == 0 and turning_on:
      # Only neede for turning lights on
      self._logger.log(f'{self.name} light has a brightness of 0 currently. Perhaps everyone is asleep and sleep_brightness is 0.', level=self.log_level)
      return False

    if self.light_disable_states:
      for constraint in self.light_disable_states:
        if self.app.constraint_compare(constraint): 
          self._logger.log(f'{self.name} light does not satisfy one or more of the "light_disable_states" ({self.light_disable_states}) (failed: {constraint}, result: {self.app.constraint_compare(constraint)}).', level=self.log_level)
          return False

    if self.use_dark_mode is not None and self.app.get_state(self.use_dark_mode) == 'off' and turning_on:
      # Only neede for turning lights on
      if self.use_lux and not self.lux_above_cutoff:
      # Check lux level when dark_mode is in use and it is daytime
        msg = f"{self.name} light level sensor readings ({self.app.get_state(self.use_lux)}) < cutoff threshold ({self.lux_threshold}). The light will not be disabled during daytime while using dark_mode."
        self._logger.log(msg, level=self.log_level)
      else:
        # No lux defined, use dark_mode only
        self._logger.log(f'{self.name} light is disabled during dark mode.', level=self.log_level)
        return False

    return True


  def disable_light(self):
    """ Manually disable the light """
    self._logger.log(f'[{self.name}] is disabled.', level=self.log_level)
    self._enabled = False


  def enable_light(self):
    """ Manually enable the light """
    self._logger.log(f'[{self.name}] is enabled.', level=self.log_level)
    self._enabled = True


  def _cancel_repeat_turn_on(self):
    """ Cancel turn_light_on repeat call """
    if self._handle_repeat_light_on is not None:
      self.app.cancel_timer(self._handle_repeat_light_on)


  def turn_light_on(self, colour=None, brightness=None, transition=None, scene=None, override=False):
    """
    param override: Will adjust light regardless of other settings (dark_mode, _enabled, physically switch, 0 sleep brightness)
    """
    # Cancel repeat call right away & call repeat again later
    self._cancel_repeat_turn_on()
    self._turn_light_on(colour, brightness, transition, scene, override)
    self._handle_repeat_light_on = self.app.run_in(lambda *_: self._turn_light_on(colour, brightness, transition, scene, override), 0.2)


  def _turn_light_on(self, colour=None, brightness=None, transition=None, scene=None, override=False):
    """
    param override: Will adjust light regardless of other settings (dark_mode, _enabled, physically switch, 0 sleep brightness)
    """
    if not self._should_adjust(override, turning_on=True):
      return

    # ADD BACK IN AFTER TESTING
    # if self._is_on and not any([colour, brightness, transition]) and not self._update_required:
    #   self._logger.log(f'{self.friendly_name.title()} is already on, it will not be turned on again.', level='NOTSET')
    #   return
    self._update_required = False
    self._sync_lights(True)

    # The switch must be on for the bulb(s) to work (if it exists)
    if self.switch_entity_id and self.app.get_state(self.switch_entity_id) == 'off':
      self._logger.log(f'[{self.name}] switch turning on ({self.switch_entity_id}).', level=self.log_level)
      self.app.turn_on(self.switch_entity_id)

    self._turn_on_action(colour, brightness, transition, scene)
    if self._handle_light_check is None:
      self._handle_light_check = self.app.run_in(self._light_check_cb, 2)


  def _turn_on_action(self, colour=None, brightness=None, transition=None, scene=None):
    """ 
    Handle logic of turning light on

    Sleep -> options -> default on/off -> 
    """

    option_map = {
      CONF_USE_CIRCADIAN: self._turn_on_circadian,
      CONF_USE_HOLIDAYS: self._turn_on_holiday,
      CONF_USE_SEASONS: self._turn_on_season,
      CONF_USE_COLOUR_LOOP: self._turn_on_colour_loop,
      CONF_USE_RANDOM_COLOURS: self._turn_on_random_colour,
      CONF_SCENE: self._turn_on_scene,
    }

    # Check manual inputs first!!!
    if scene is not None:
      self._logger.log(f'[{self.name}] turning on using a manual scene: {scene}', level=self.log_level)
      self.app.turn_on(scene)
    if self._turn_on_manual(colour, brightness, transition):
      return

    # Check for sleep mode next
    if self._turn_on_sleep():
      return

    # Loop through all options
    for name, value in self.attrs[CONF_OPTIONS].items():
      if value:
        op = option_map.get(name, None)
        if op and op():
          self._logger.log(f'[{self.name}] successfully turned on using: {name}.', level=self.log_level)
          return

    # Default fallback turn on
    if not self._turn_on_default():
      self._logger.log(f'[{self.name}] Failed to turn light on!', level='WARNING')


  def _turn_on_sleep(self, kwargs={}):
    if self.sleep_condition:
      kwargs = self.get_colour()
      kwargs['brightness_pct'] = self.get_brightness()
      kwargs['transition'] = self.get_transition()
      if self.sleep_entity:
        for lt in self.sleep_entity:
          kwargs['entity_id'] = lt
          # self.app.call_service('light/turn_on', **kwargs)
          self._call_service('light/turn_on', kwargs)
          self._logger.log(f'Turning {self.name} on using sleep conditions: {kwargs}.', level=self.log_level)
      else:
        kwargs['entity_id'] = self.entity_id
        # self.app.call_service('light/turn_on', **kwargs)
        self._call_service('light/turn_on', kwargs)
        self._logger.log(f'Turning {self.name} on using sleep conditions: {kwargs}.', level=self.log_level)
      return True
    return False

  def _turn_on_manual(self, colour, brightness, transition):
    """ Turn light on using manual parameters """
    if not any([colour, brightness, transition]):
      return False

    kwargs = self.parse_colour(colour)
    kwargs['entity_id'] = self.entity_id
    if brightness and isinstance(brightness, int):
      kwargs['brightness_pct'] = brightness
    if transition and isinstance(transition, int):
      kwargs['transition'] = transition
    # self.app.call_service('light/turn_on', **kwargs)
    self._call_service('light/turn_on', kwargs)
    self._logger.log(f'[{self.name}] turn on using manual inputs: colour: {colour}, brightness: {brightness}, transition: {transition}', level=self.log_level)
    return True

  def _turn_on_scene(self):
    if self.scene:
      scene = self.get_scene()
      self._logger.log(f'Turning {self.name} on using the scene: {scene}.', level=self.log_level)
      self.app.turn_on(scene)
      return True
    return False

  def _turn_on_colour_loop(self, kwargs={}):
    if self.use_colour_loop:
      kwargs['entity_id'] = self.entity_id
      kwargs['brightness_pct'] = self.get_brightness() # - 2 # Changing brightness will stop colorloop so we need it to be different here
      kwargs['transition'] = self.get_transition()
      kwargs['effect'] = 'colorloop'
      # self.app.call_service('light/turn_on', **kwargs)
      self._call_service('light/turn_on', kwargs)
      self._logger.log(f'Turning {self.name} on using colour loop: {kwargs}.', level=self.log_level)
      return True
    return False

  def _turn_on_random_colour(self, kwargs={}):
    if self.use_random_colour:
      # If we dont block the calls while on, the light will keep changing colours
      if self._is_on:
        self._logger.log(f'[{self.name}] set to use random_colour but the light is already on and will not be adjust until off again.', level=self.log_level)
        return True
      kwargs['entity_id'] = self.entity_id
      kwargs['brightness_pct'] = self.get_brightness()
      kwargs['transition'] = self.get_transition()
      kwargs['effect'] = 'random'
      # self.app.call_service('light/turn_on', **kwargs)
      self._call_service('light/turn_on', kwargs)
      self._logger.log(f'Turning {self.name} on using random colours: {kwargs}.', level=self.log_level)
      return True
    return False

  def _turn_on_season(self):
    if self.use_seasons and self.app.seasons.is_season:
      # Try to create/get a seasonal scene if we don't have it yet
      self._seasonal_scene = self.app.seasons.try_get_scene(self.app.seasons.season, self.name, self.child_bulbs, self.get_brightness(), overwrite=False)
      if self._seasonal_scene:
        self._logger.log(f'Turning {self.name} onto seasonal colours using the scene: {self._seasonal_scene} ({self.app.seasons.holiday}, {self.app.seasons.season}).', level=self.log_level)
        self.app.turn_on(self._seasonal_scene)
        return True
      else:
        # No scene was found/created or we don't have any child bulbs so a scene is pointless
        self._logger.log(f'[{self.name}] failed using a seasonal scene: {self._holiday_scene}. Attempting to use a different option now.', level='WARNING')
    return False

  def _turn_on_holiday(self):
    if self.use_holidays and self.app.seasons.is_holiday:
      # Try to create/get a holiday scene if we don't have it yet
      self._holiday_scene = self.app.seasons.try_get_scene(self.app.seasons.holiday, self.name, self.child_bulbs, self.get_brightness(), overwrite=False)
      if self._holiday_scene:
        self._logger.log(f'Turning {self.name} onto holiday colours using the scene: {self._holiday_scene} ({self.app.seasons.holiday}, {self.app.seasons.season}).', level=self.log_level)
        self.app.turn_on(self._holiday_scene)
        return True
      else:
        # No scene was found/created or we don't have any child bulbs so a scene is pointless
        self._logger.log(f'[{self.name}] failed using a holiday scene: {self._holiday_scene}. Attempting to use a different option now.', level='WARNING')
    return False

  def _turn_on_circadian(self, kwargs={}):
    if self.use_circadian and self.colour:
      self._logger.log(f'Turned {self.name} on using circadian values.', level=self.log_level)
      # kwargs['kelvin'] = circadian.calc_colortemp # Other option for CL
      kwargs['rgb_color'] = list(circadian.calc_rgb(self.app))
      kwargs['brightness_pct'] = circadian.calc_brightness(self.app)
      kwargs['entity_id'] = self.entity_id
      # self.app.call_service('light/turn_on', **kwargs)
      self._call_service('light/turn_on', kwargs)
      self._logger.log(f'Turning on {self.name} light with kwargs: {kwargs}.', level=self.log_level)
      return True
    return False

  def _turn_on_default(self):
    # Turn on using basic colour, brightness, & transition
    kwargs = self.get_colour()
    kwargs['entity_id'] = self.entity_id
    if self.is_dimable:
      kwargs['brightness_pct'] = self.get_brightness()
      kwargs['transition'] = self.get_transition()

    # This needs to be generical call since it can be a switch or light entity
    # res = self.app.call_service('homeassistant/turn_on', **kwargs)
    # self._call_service('homeassistant/turn_on', kwargs)
    # self.app.turn_on(**kwargs)

    if 'light' in kwargs['entity_id'].split('.')[0]:
      self._call_service('light/turn_on', kwargs)
    else:
      self._call_service('switch/turn_on', kwargs)

    self._logger.log(f'Turning {self.name} ({self.entity_id}) on using no options: {kwargs}', level=self.log_level)
    return True


  def _call_service(self, service, kwargs):
    """ wrapper for HA calls to log any errors """
    res = self.app.call_service(service, **kwargs)
    if not res:
      if service == 'light/turn_on' and (not self._is_on or not self._should_be_on):
        self._logger.log(f'Failed to call "{service}" using {kwargs}, result: {res}. Light is_on: {self._is_on}, should_be_On: {self._should_be_on}, state info: {self.app.get_state(kwargs["entity_id"], attribute="all")}', level='ERROR', notify=False)
      elif service == 'light/turn_off' and (self._is_on or self._should_be_on):
        self._logger.log(f'Failed to call "{service}" using {kwargs}, result: {res}. Light is_on: {self._is_on}, should_be_On: {self._should_be_on}, state info: {self.app.get_state(kwargs["entity_id"], attribute="all")}' , level='ERROR', notify=False)
  
    # Trying to track down why lights sometimes turn on dimmer than they should (very dim...)
    # if kwargs.get('brightness_pct', 1000) < 30 or kwargs.get('brightness', 1000) < 30:
    #   self._logger.log(f'[{self.name}] LOW BRIGHTNESS - {service} using {kwargs}')


  def turn_light_off(self, transition=None, override=False):
    self._cancel_repeat_turn_on()

    if not self._should_adjust(override, turning_on=False):
      return

    # Fire event to related lights updating current state
    self._sync_lights(False)
    
    if self.is_dimable:
      kwargs = {}
      kwargs['entity_id'] = self.entity_id
      kwargs['transition'] = transition if transition else self.get_transition()
      # self.app.call_service('light/turn_off', **kwargs)
      self._call_service('light/turn_off', kwargs)
      self._logger.log(f'Turning {self.friendly_name.lower()} off using: {kwargs}', level=self.log_level)
    else:
      self.app.turn_off(self.entity_id)
      self._logger.log(f'Turning {self.friendly_name.lower()} off using simple turn_off().', level=self.log_level)

    if self._handle_light_check is None:
      self._handle_light_check = self.app.run_in(self._light_check_cb, 2)


  def toggle_light(self, colour=None, brightness=None, transition=None, scene=None, override=False):
    """ If the light is physically switched this will try to call turn_light_on and fail w/o using override """
    if not self._should_adjust(override, turning_on=not self._should_be_on):
      return

    self._logger.log(f'Toggling {self.friendly_name.lower()}.', level=self.log_level)
    if self._should_be_on:
      self.turn_light_off(transition, override)
    else:
      self.turn_light_on(colour, brightness, transition, scene, override)


#########   --- Callbacks ---    #########

  
  def _entity_state_change_cb(self, entity, attribute, old, new, kwargs):
    """ Call when a entity state changes and a light need to check for an update (ex: dark_mode, sleep_mode) """
    self._update_required = True
    


  def _light_callback(self, entity, attribute, old, new, kwargs):
    """ Monitor HA light state (and switch if defined) """
    # Light adjustments other than ON -> OFF or OFF -> ON will provide a dictionary for new
    if old == new:
      self._logger.log(f'[{self.name}] old an new are the same in light callback... Should I skip these???')


    new_state = new['state'] if isinstance(new, dict) else new
    old_state = old['state'] if isinstance(old, dict) else old
    # TODO: These were changed from simply old & new
    new_attrs = new['attributes'] if isinstance(new, dict) else new
    old_attrs = old['attributes'] if isinstance(old, dict) else old

    # Light changed settings while on
    adjusted_while_on = old_state == new_state and old_attrs != new_attrs

    if new_state == 'on':
      self._logger.log(f'[{self.name}] was turned ON in reality!', 'NOTSET')
      # If take_over_control is enabled track manual adjusts made to the light
      if self.take_over_control and self._first_off_cycle_complete:
        # Light turned on manually
        if not self._should_be_on and not self._related_light_exists_and_on:
          self._logger.log(f'{self.name} ({entity}) light was manually turned on and will stay on until manually turned off (is_on: {self._is_on}, should_be_on: {self._should_be_on}): {self.app.get_state(self.entity_id, attribute="all")}', level='INFO')
          self._prevent_manual_adjustments = True

        # Light manually adjusted while on
        if adjusted_while_on:
          if 'attributes' not in self._previous_light_state:
            self._logger.log(f'Light does not have any attributes in _previous_light_state: {self._previous_light_state}')
          elif self._previous_light_state['attributes'] == old.get("attributes", {}):
            # Light was automatically adjust since we cached the "old" state before turning on automatically
            self._previous_light_state = new
          else:
            # Light was manually adjust since we cached the "old" state before turning on automatically
            self._logger.log(f'[{self.name}] light manually adjusted while it is on. Disabling automatic adjustments now:  {self.app.get_state(self.entity_id, attribute="all")}', level='INFO')
            self._logger.log(f'[{self.name}] NEW: {new}', level='DEBUG')
            self._logger.log(f'[{self.name}] OLD: {old.get("attributes", {})}', level='DEBUG')
            self._logger.log(f'[{self.name}] PREVIOUS_LIGHT_STATE: {self._previous_light_state["attributes"]}', level='DEBUG')
            self._prevent_manual_adjustments = True

      if entity == self.switch_entity_id:
        self._switch_is_on = True
        self.turn_light_on(override=True)
      else:
        self._bulb_is_on = True

    elif new_state == 'off':
      self._logger.log(f'[{self.name}] was turned OFF in reality!', 'NOTSET')
      if self.child_lights:
        # If this is the parent light, signal all child lights that it is now off (Every child light has to be off since the parent is off)
        # Needed incase the light is turned off by a human (UI/physical switch/GA/etc) to ensure everything stays in sync
        self._sync_lights(False)

      if entity == self.switch_entity_id:
        self._switch_is_on = False
        self.turn_light_off(override=True)
      else:
        self._bulb_is_on = False

      self._should_be_on = False
      self._prevent_manual_adjustments = False
      self._first_off_cycle_complete = True


  def _light_check_cb(self, kwargs):
    """ Middle man for light check to increment time between calls """
    self._next_check_time += 1
    self.app.run_in(self._light_check, self._next_check_time)

  def _light_check(self, kwargs):
    """ Verify that the light was actually turn on or off """
    # self._logger.log(f'[{self.name}] checking if light is in correct state...', level=self.log_level)
    self._handle_light_check = None
    self._check_count += 1
    if self._check_count > MAX_LIGHT_CALLBACK_CHECKS:
      if self._should_be_on and not self._is_on:
        msg = 'should be on but is off'
      elif not self._should_be_on and self._is_on:
        msg = 'should be off but is on'
      else:
        msg = f'confused... _should_be_on: {self._should_be_on} & _is_on: {self._is_on}'
      self._logger.log(f'The {self.friendly_name.lower()} tried {self._check_count} time to correct its state (max {MAX_LIGHT_CALLBACK_CHECKS}). The light {msg}.', level='WARNING', notify=False)
      self._check_count = 0
      self._next_check_time = 1
      return

    if self._should_be_on and not self._is_on:
      self.turn_light_on(override=True)
    elif not self._should_be_on and self._is_on:
      self.turn_light_off(override=True)
    else:
      self._check_count = 0


  def _related_lights_callback(self, event_name, data, kwargs):
    """ Sync parent and children lights up """
    # self._logger.log(f"Setting {data['device']} light to {data['should_be_on']} (should_be_on).", level=self.log_level)
    should_be_on = data.get('should_be_on', None)
    if should_be_on is not None:
      self._related_light_is_on = should_be_on


  @property
  def log_level(self):
    """ Log level of all messages - configurable via the YAML """
    return self.attrs[CONF_LOG_LEVEL]

  @property
  def entity_id(self):
    return self.attrs[CONF_ENTITY_ID]

  @property
  def name(self):
    """ Common name of this light """
    return self.attrs[CONF_FRIENDLY_NAME]

  @property
  def friendly_name(self):
    """ Friendly name of this light """
    return self.name.title() + ' light'

  @property
  def aliases(self):
    """ List of aliases for this light """
    return self.attrs[CONF_ALIASES]

  @property
  def child_bulbs(self):
    """ Defined if the light consists of multiple bulbs """
    return self.attrs[CONF_CHILD_BULBS]

  @property
  def switch_entity_id(self):
    """ Defined if there is a switch/hue bulb combo """
    return self.attrs[CONF_SWITCH_ENTITY_ID]

  @property
  def light_disable_states(self):
    """ List of constraints that disable this light """
    return self.attrs[CONF_LIGHT_DISABLE_STATES]

  @property
  def enabled_state_boolean_tracker(self):
    """ Return light enabled state boolean tracker """
    return self.attrs[CONF_LIGHT_ENABLED_BOOLEAN_TRACKER]

  @property
  def light_enabled(self):
    """ Check if light is enabled using the manual HA boolean """
    try:
      if not self.app.entity_exists(self.enabled_state_boolean_tracker):
        self._logger.log(f'{self.name} has not tracker boolean', self.log_level)
        return True
      return bool(self.app.get_state(self.enabled_state_boolean_tracker) == 'on')
    except Exception as e:
      self._logger.log(f'Error reading {self.name} enable state boolean: {self.enabled_state_boolean_tracker}', level='ERROR')
      return True

  @property
  def detect_non_ha_changes(self):
    """ Detect manual control and disable light """
    return self.attrs[CONF_DETECT_NON_HA_CHANGES]

  @property
  def take_over_control(self):
    """ Disable 'automated control' when the light is turned on from a different source """
    return self.attrs[CONF_TAKE_OVER_CONTROL]

  @property 
  def day_thresholds(self):
    """ Defines morning, day, night thresholds """
    return self.attrs[CONF_PROPERTIES][CONF_DAY_THRESHOLDS]

  @property
  def colour(self):
    """ Colour to turn this light on to (rgb, kelvin, etc) - Can use morning, day, night """
    return self.attrs[CONF_PROPERTIES][CONF_COLOUR]

  @property
  def brightness(self):
    """ Defined to override the default brightness - Can use morning, day, night """
    return self.attrs[CONF_PROPERTIES][CONF_BRIGHTNESS]

  @property
  def transition(self):
    """ Defined to override the default transition time - Can use morning, day, night  """
    return self.attrs[CONF_PROPERTIES][CONF_TRANSITION]

  @property
  def sleep_entity(self):
    """ Alternative light to use when asleep condition met """
    return [self.app.map_light_to_entity(lt) for lt in self.attrs[CONF_PROPERTIES][CONF_SLEEP_LIGHTS]]

  @property
  def sleep_colour(self):
    """ Colour to use when sleeping """
    return self.attrs[CONF_PROPERTIES][CONF_SLEEP_COLOUR]

  @property
  def sleep_brightness(self):
    """ Brightness to use when sleeping """
    return self.attrs[CONF_PROPERTIES][CONF_SLEEP_BRIGHTNESS]

  @property
  def sleep_transition(self):
    """ Transition to use when sleeping """
    return self.attrs[CONF_PROPERTIES][CONF_SLEEP_TRANSITION]

  @property
  def sleep_condition_entity(self):
    """ The entity used to check if the sleep condition is met """
    if self.sleep_condition is None:
      return None
    return self.attrs[CONF_PROPERTIES][CONF_SLEEP_CONDITION].split(',')[0].strip()

  @property
  def sleep_condition(self):
    """ Return true if sleep condition is met. """
    # someone = self.attrs[CONF_PROPERTIES][CONF_SLEEP_CONDITION] in ['someone', 'anyone']
    # return self.app.sleep.someone_asleep if someone else self.app.sleep.everyone_asleep
    contraint = self.attrs[CONF_PROPERTIES][CONF_SLEEP_CONDITION]
    if not contraint:
      return None
    return self.app.constraint_compare(contraint)

  @property
  def scene(self):
    """ Defined a scene to be used for this light """
    return self.attrs[CONF_OPTIONS][CONF_SCENE]

  @property
  def use_seasons(self):
    """ Defined if seasonal colours are to be used for this light """
    return self.attrs[CONF_OPTIONS][CONF_USE_SEASONS]

  @property
  def use_random_colour(self):
    """ Defined if colour are randomly to be used for this light """
    return self.attrs[CONF_OPTIONS][CONF_USE_RANDOM_COLOURS]

  @property
  def use_circadian(self):
    """ Defined if circadian lighting is to be used for this light """
    return self.attrs[CONF_OPTIONS][CONF_USE_CIRCADIAN]

  @property
  def use_dark_mode(self):
    """ Defined if this light only turns on at night """
    return self.attrs[CONF_PROPERTIES][CONF_USE_DARK_MODE]

  @property
  def use_holidays(self):
    """ Defined if holiday colours are to be used for this light """
    return self.attrs[CONF_OPTIONS][CONF_USE_HOLIDAYS]

  @property
  def use_colour_loop(self):
    """ Defined if a colour loop is to be randomly used for this light """
    return self.attrs[CONF_OPTIONS][CONF_USE_COLOUR_LOOP]

  @property
  def use_lux(self):
    """ Use light level reading to determine if this light should be on during the day (Only useful for lights that use_dark_mode) """
    return self.attrs[CONF_PROPERTIES][CONF_USE_LUX]

  @property
  def lux_threshold(self):
    """ Use light level reading to determine if this light should be on during the day (Only useful for lights that use_dark_mode) """
    return self.attrs[CONF_PROPERTIES][CONF_LUX_THRESHOLD]

  @property
  def lux_above_cutoff(self):
    """ The average light level is above the default cutoff value """
    try:
      return bool(float(self.app.get_state(self.use_lux)) > self.lux_threshold)
    except (TypeError, ValueError):
      return False

  @property
  def parent_light(self):
    """ Name of the parent light """
    return self.attrs[CONF_PARENT_LIGHT]

  @property
  def child_lights(self):
    """ Does this light have child lights (boolean) """
    return self.attrs[CONF_CHILD_LIGHTS]

  @property
  def is_colour(self):
    """ Is this light capable of using colour """
    return self.attrs[CONF_IS_COLOUR]

  @property
  def is_dimable(self):
    """ Is this light capable of using colour """
    return self.attrs[CONF_IS_DIMABLE]

  @property
  def _related_light_exists_and_on(self):
    """ A parent or child lights exist and are on """
    return (self.parent_light or self.child_lights) and self._related_light_is_on

  @property
  def _is_on(self):
    if self.switch_entity_id:
      return bool(self._switch_is_on and self._bulb_is_on)
    else:
      return bool(self._bulb_is_on)


  def parse_day_or_single(self, data):
    if not isinstance(data, dict):
      # Only a single int parameter was provided for the entire day
      return data

    thresholds = self.day_thresholds
    if self.app.now_is_between(thresholds[CONF_MORNING], thresholds[CONF_DAY]):
      period = CONF_MORNING
    elif self.app.now_is_between(thresholds[CONF_DAY], thresholds[CONF_NIGHT]):
      period = CONF_DAY
    else:
      period = CONF_NIGHT

    return data[period]


  def parse_colour(self, colour):
    """ The colour options, color_name, rgb_color, and color_temp """
    if not self.is_colour or not colour:
      return {}

    if isinstance(colour, int):   # Colour temp passed in
      return {'color_temp': colour}
    if isinstance(colour, list):  # RGB list passed in
       return {'rgb_color': colour}
    if ',' not in colour:         # Name of colour passed in
      return {'color_name': colour}
    if ',' in colour:             # RGB list passed in as a string
      try:
        rgb = [int(x.strip(' ')) for x in colour.strip('[]').strip('()').split(',')]
        if len(rgb) == 3: 
          return {'rgb_color': (rgb[0], rgb[1], rgb[2])}
      except Exception as e:
        self._logger.log(f'[{self.name}] Error converting rgb colour: {colour}: {e}')

    self._logger.log(f'[{self.name}] colour is not valid: {colour}. Using default colour: {CONF_DEFAULT_COLOUR}.', level='INFO')
    return {'color_name': CONF_DEFAULT_COLOUR}


  # Brightness, transition, colour, & scene can all be single value or dictionary of 'morning', 'day', and 'night' values
  def get_brightness(self):
    if self.sleep_brightness is not None and self.sleep_condition:
      return self.sleep_brightness
    else:
      return self.parse_day_or_single(self.brightness)

  def get_transition(self):
    if self.sleep_transition is not None and self.sleep_condition:
      return self.sleep_transition
    else:
      return self.parse_day_or_single(self.transition)

  def get_colour(self):
    if self.sleep_colour is not None and self.sleep_condition:
      return self.parse_colour(self.sleep_colour)
    else:
      return self.parse_colour(self.parse_day_or_single(self.colour))

  def get_scene(self):
    if self.scene:
      return self.parse_day_or_single(self.scene)
    else:
      return None



  @property
  def user_name(self):
    """ Map user_id to user_name - ALWAYS SEEMS TO HAVE ALEX AS THE USER CONTROLLING EVERYTHING """
    return USER_IDS.get(self.app.get_state('light.study_ceiling_light', attribute='context').get('user_id', None), 'Unknown')


  def cleanup(self):
    """ Required to manually terminate all listeners when resetting all lights after a settings change """
    self.app.cancel_timer(self._handle_light_check)
    for h in self._state_handles:
      self.app.cancel_listen_state(h)
    for h in self._event_handles:
      self.app.cancel_listen_event(h)
    for h in self._sched_handles:
      self.app.cancel_timer(h)
