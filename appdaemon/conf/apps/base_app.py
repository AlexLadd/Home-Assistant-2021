"""
Base class app for all Appdaemon Apps

Options:
  - self.set_logger_threshold: Log threshold for specific app

TODO:
  - Add function to access emergency_mode boolean, guest mode, various modes, 
  - Add ability to add contraints to the app that will disable/enable it
"""

import appdaemon.plugins.hass.hassapi as hass
import inspect
import operator
import voluptuous as vol
import utils_validation
import threading
import yaml

"""
Yaml Parameters (possibilities):
  - constraint_app_enabled: A list of contraints to disable to the app. ex: input_boolean.ad_testing_1, ==, on
  - logging_cutoff: Threshold for log messages. Anything below this level will not be displayed
  - 

global_dependencies set by this app: (they do not need to be set in each app)
  - base_app
  - utils
  - const
  - utils_validation
  -> NOTE: These can all be accessed in the app using self.utils, self.const, etc followed by the function you need

TODO:
  - Add in functionality to check app dependencies and set them to given app so the app doesnt need to do it individually
"""

INPUT_BOOLEAN_HA_PATH = 'input_booleans/appdaemon_automatic_booleans.yaml'
# Toggle for debugging since this app cannot use the built in logger to manage this
DEBUGGING = False

CONF_DEPENDENCIES = 'dependencies'
CONF_DISABLED_STATES = "constraint_app_enabled"
CONF_LOGGING_CUTTOFF = 'logging_cutoff'
CONF_LOGGING_CUTTOFF_DEFAULT = 'DEBUG'

# Base schema that can be extended by any app
APP_SCHEMA = vol.Schema(
  {
    vol.Optional(CONF_DEPENDENCIES, default=[]): utils_validation.ensure_list,
    vol.Optional(CONF_LOGGING_CUTTOFF, default=CONF_LOGGING_CUTTOFF_DEFAULT): str,
    vol.Optional(CONF_DISABLED_STATES, default=[]): utils_validation.ensure_list,
  },
  extra=vol.ALLOW_EXTRA,
)

# global_dependencies which will be registered to all apps
GLOBAL_MODULES = ['base_app', 'const', 'utils', 'utils_validation']


class BaseApp(hass.Hass):

  APP_SCHEMA = APP_SCHEMA

  def initialize(self):
    # Setup logger and threshold
    self._logger = self.get_app('custom_logger') 

    # Process base config (This must be done again if the app extends the schema???????)
    try:
      self.cfg = self.APP_SCHEMA(self.args)
    except vol.Invalid as err:
      # self._logger.log(f'Basic configuration error: {err}', level='ERROR')
      raise vol.Invalid(f"Basic configuration error: {err}")

    # Set logging threshold after reading in config
    self.set_logger_threshold(self.cfg.get(CONF_LOGGING_CUTTOFF))

    # Register global_dependencies used in all apps
    for module in GLOBAL_MODULES:
      self.depends_on_module(module)
      # Provide access to all utility module for every App (Excluding the base_app)
      if module != 'base_app':
        setattr(self, module, __import__(module))

    # Register constraint checks for enable/disable state checks
    self.register_constraint("constraint_app_enabled")

    # Locks to prevent concurency issues for IO operations (creating HA entities by writing to files)
    self._create_input_boolean_lock = threading.Lock()
    self._run_in_input_booleans = None

    # Call the child class version of initialize
    if hasattr(self, 'setup'):
      self.setup()



  @property
  def dark_mode(self):
    return self.get_state(self.const.DARK_MODE_BOOLEAN) == 'on'

  @property
  def dt_str(self):
    """ Formated datetime Str """
    return self.datetime().strftime("%Y-%m-%d, %H:%M:%S")

  def set_logger_threshold(self, lvl):
    """
    Set app specific log threshold
    This will automatically use the module name
    """
    stack = inspect.stack()
    app_name = stack[1][0].f_locals["self"].__module__
    self._logger.set_app_threshold(app_name, lvl)
    self.debug_level = lvl
    if DEBUGGING:
      self._logger.log(f'Setting app logger level to {lvl} for: {app_name} ({self.name})')


  def constraint_app_enabled(self, value): 
    """ 
    Top level call for app config comparisons - Used for clarity
    Add "constraint_app_enabled" to app yaml along with constraints
    """
    return self.constraint_compare(value)


  def constraint_compare(self, value):
    """ 
    Add "constraint_app_enabled" to app yaml along with constraints
    All entities are required to satisfy the provided operator with their respective listed state(s)
    Examples:
      - sensor.temperature, <, 25.2
      - sensor.humidity, >, 60
      - input_boolean.dark_mode, =, on
      - sensor.people_home, !=, 1, 3
    """
    if DEBUGGING:
      self._logger.log(f'constraint_compare called: {value}')

    ops = { 
      "+" : operator.add,
      "-" : operator.sub,
      ">" : operator.gt,
      ">=" : operator.ge,
      "<" : operator.lt,
      "<=" : operator.le,
    }

    if not isinstance(value, list):
      value = [value]

    for v in value:
      if len(v) < 3:
        self.log('Invalid config for constraint_compare in {} app. Specify: entity, operator, state(s). It will be ignored.'.format(self.name))
        continue

      values = [x.strip(' ') for x in v.split(',')]
      entity = values[0]
      op = values[1]
      desired_states = values[2:]

      if not self.entity_exists(entity):
        self.log(f'Entity does not exists ({entity}). Skipping this constraint ({v})')
        continue
      current_state = self.get_state(entity)

      if op in ['=', '==']:
        if current_state not in desired_states:
          return False
      elif op in ['!=']:
        if current_state in desired_states:
          return False
      elif op in ops:
        for state in desired_states:
          if not ops[op](float(current_state), float(state)):
            return False
      else:     
        self.log('Invalid config for constraint_compare in {} app. Specify: entity, operator, state(s). It will be ignored.'.format(self.name))

    return True

    
  def create_input_boolean(self, boolean_id, name=None, icon=None, file_path=INPUT_BOOLEAN_HA_PATH):
    """ Create an HA input boolean by saving the config to a file """
    if not boolean_id.startswith('input_boolean.'):
      boolean_id = 'input_boolean.' + boolean_id
    # if not boolean_id.startswith('_tracker'):
    #   boolean_id = boolean_id + '_tracker'

    if self.entity_exists(boolean_id):
      self._logger.log(f'{boolean_id} already exists so one will not be created using create_input_boolean', level='INFO')
      return

    if name is None:
      name = boolean_id.replace('input_boolean.', '').replace('_', ' ').title()
    options = {'name': name}
    if icon is not None:
      options['icon'] = icon

    # Create config using unique boolean ID
    config = {boolean_id.replace('input_boolean.', ''): options}
    yaml.Dumper.ignore_aliases = lambda *args : True 
    yaml_config = yaml.dump(config, default_flow_style=False, sort_keys=False)

    with self._create_input_boolean_lock:
      with open(self.utils.ha_path(file_path), 'a') as f:
        f.write(str(yaml_config))
        f.write('\n')
      # Make sure this is locked as well to prevent missing the reload
      if self._run_in_input_booleans:
        self.cancel_timer(self._run_in_input_booleans)
        self._run_in_input_booleans = None
      self._run_in_input_booleans = self.run_in(self._reload_input_booleans, 1)

    self._logger.log(f'Saved input_boolean config to {file_path}: "{yaml_config}"', level='INFO')


  def _reload_input_booleans(self, kwargs):
    self._logger.log(f'Reloading input_booleans now')
    self.call_service('input_boolean/reload')
    #TODO: Add in a check for correct reload
    
