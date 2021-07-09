

from base_app import BaseApp
import utils_validation
import voluptuous as vol
from const import CONF_FRIENDLY_NAME, CONF_SENSORS, CONF_ALIASES


CONF_START_KEY = 'sensors'
CONF_LOG_LEVEL = 'log_level'                     # Log level at the individual motion sensor (class) level
CONF_ON_LIGHTS = 'on_lights'
CONF_OFF_LIGHTS = 'off_lights'
CONF_ON_DURATION = 'on_duration'
CONF_DISABLE_STATES = 'motion_disable_states'
CONF_TRACK_LAST_MOTION = 'track_last_motion'
CONF_USE_PET_MODE = 'use_pet_mode'              # Disable sensors at night so cats don't trigger lights, etc

CONF_DEFAULT_LOG_LEVEL = 'NOTSET'
CAT_MODE_BOOLEAN = 'input_boolean.pet_mode'

class Motion(BaseApp):

  APP_SCHEMA = BaseApp.APP_SCHEMA.extend({
    CONF_START_KEY: vol.Schema(
      {str: 
        vol.Schema(
          {
            vol.Required(CONF_SENSORS): utils_validation.entity_id_list,
            vol.Optional(CONF_LOG_LEVEL, default=CONF_DEFAULT_LOG_LEVEL): str,
            vol.Required(CONF_ON_LIGHTS): utils_validation.ensure_list,
            vol.Required(CONF_ON_DURATION): utils_validation.parse_star_time,
            vol.Optional(CONF_FRIENDLY_NAME): str,
            vol.Optional(CONF_ALIASES): list,
            vol.Optional(CONF_OFF_LIGHTS): utils_validation.ensure_list,
            vol.Optional(CONF_DISABLE_STATES, default=[]): list,
            vol.Optional(CONF_TRACK_LAST_MOTION, default=True): bool,
            vol.Optional(CONF_USE_PET_MODE, default=True): bool,
          }
        ),
      })
    }
  )

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_4')

    self.lights = self.get_app('lights')
    self.se = self.get_app('spotify_engine')
    self.sleep = self.get_app('sleep')
    self.messages = self.get_app('messages')
    self.notifier = self.get_app('notifier')

    # Load in data from config
    self._motion_sensors = {}
    self._motion_data = {}
    self._process_cfg(self.cfg)
    self._setup_generic_sensors(self._motion_data)

    # Custom motion actions
    for sensor in self._motion_sensors['kitchen'].sensors:
      self.listen_state(self._kitchen_motion_cb, sensor, new='on')

  
  def _process_cfg(self, config):
    """ Prep yaml data - Ensure we keep integrety of original data """
    import copy
    cfg = copy.deepcopy(config)

    for name, data in cfg[CONF_SENSORS].items():
      self._motion_data[name] = data 
      # off_lights == on_lights when it isn't defined
      if CONF_OFF_LIGHTS not in data:
        self._motion_data[name][CONF_OFF_LIGHTS] = data[CONF_ON_LIGHTS]
      # Add the room name to aliases (add aliases if it doesnt exists)
      self._motion_data[name].setdefault(CONF_ALIASES, []).append(name)
      # Set sensor friendly name to room
      self._motion_data[name][CONF_FRIENDLY_NAME] = name.replace('_', ' ').title()


  def _setup_generic_sensors(self, config):
    """ Setup all the generic motion sensors """
    self._motion_sensors = {}
    for name, settings in self._motion_data.items():
      self._motion_sensors[name.lower()] = MotionEntity(self, settings)


  def _kitchen_motion_cb(self, entity, attribute, old, new, kwargs):
    if not self._motion_sensors['kitchen']._should_adjust():
      # Triggers this message too often when motion in the kitchen frequently
      # self._logger.log('The kitchen custom motion automation is disabled. No morning announcement or song will be played!', level='DEBUG')
      return

    if self.utils.valid_input(old, new) and new == 'on':
      if (self.get_state(self.const.ALEX_MORNING_GREETING_BOOLEAN) == 'off' and self.sleep.alex_awake) or \
         (self.get_state(self.const.STEPH_MORNING_GREETING_BOOLEAN) == 'off' and self.sleep.steph_awake):

        msg = self.messages.build_message(
          holiday_check= True,
          # garbage_check= True,
          wind_check=True,
          outside_weather=True,
          uv_check=True,
          inspirational_quote=True,
        )
        speaker = 'kitchen'
        self.notifier.tts_notify(msg, speaker, speaker_override=True)
        if self.sleep.alex_awake:
          self.turn_on(self.const.ALEX_MORNING_GREETING_BOOLEAN)
        if self.sleep.steph_awake:
          self.turn_on(self.const.STEPH_MORNING_GREETING_BOOLEAN)

        # Play morning song after waiting for message to finish on speaker (Will cancel listener after 10 minutes & will only fire once if successful)
        self.listen_state(lambda *_: self.se.play_song('both', 'kitchen'), 'media_player.kitchen_speaker', old='playing', new='idle', timeout=10*60, oneshot=True)


  def test(self, entity, attribute, old, new, kwargs):
    self.log(f'Testing Motion Module: ') 






class MotionEntity:
  """
  Generic motion sensor to turn lights on/off
  """

  def __init__(self, app, config):
    self.app = app
    self.logger = self.app._logger

    self.attrs = config
    self._handle_motion = None
    self._enabled = True

    for sensor in self.attrs[CONF_SENSORS]:
      self.logger.log(f'Setting up sensor: {sensor} ({self.friendly_name})', level=self.log_level)
      self.app.listen_state(self._motion_on, sensor, new='on')


  @property
  def sensors(self):
    """ List of motion sensor entities """
    return self.attrs[CONF_SENSORS]

  @property
  def name(self):
    """ Name used for UI and sensors since more likely to be unique """
    return self.friendly_name + ' Motion Sensor'

  @property
  def friendly_name(self):
    return self.attrs[CONF_FRIENDLY_NAME]

  @property
  def log_level(self):
    """ Log level of all messages - configurable via the YAML """
    return self.attrs[CONF_LOG_LEVEL]

  @property
  def on_duration(self):
    return self.attrs[CONF_ON_DURATION]

  @property
  def on_lights(self):
    """ Light(s) to turn on with motion detection """
    return self.attrs[CONF_ON_LIGHTS]

  @property
  def off_lights(self):
    """ Light(s) to turn off with motion detection (Default: on_lights) """
    return self.attrs[CONF_OFF_LIGHTS]

  @property
  def conditions(self):
    """ Conditions in which motion should be disabled """
    return self.attrs[CONF_DISABLE_STATES]

  @property
  def track_last_motion(self):
    """ Use this sensor to track last motion location in house """
    return self.attrs[CONF_TRACK_LAST_MOTION]

  @property
  def track_last_motion_sensor(self):
    """ Sensor used to track last motion location in house """
    return self.app.const.LAST_MOTION_LOCATION_SENSOR

  @property
  def use_pet_mode(self):
    """ Disable lights, etc when pet_mode is on at night for cat """
    return self.attrs[CONF_USE_PET_MODE]

  @property
  def cat_mode_on(self):
    """ Return True is cat_mode boolean is currently on """
    return self.app.get_state(CAT_MODE_BOOLEAN) == 'on'


  def _should_adjust(self, override=False):
    if not self._enabled:
      self.logger.log('{} is disabled: self._enabled: {}.'.format(self.name, self._enabled), level=self.log_level)
      return False

    # Check if config constraints are met
    if self.conditions:
      for b in self.conditions:
        if self.app.constraint_compare(b):
          self.logger.log(f"One of the {self.name} condition(s) is not met: {b}.", level=self.log_level)
          return False

    if self.use_pet_mode and self.cat_mode_on and self.app.sleep.everyone_asleep:
      self.logger.log(f'{self.name} is disabled because pet_mode is on ({self.cat_mode_on}) and everyone is asleep ({self.app.sleep.everyone_asleep}).', level=self.log_level)
      return False

    return True


  def _motion_on(self, entity, attribute, old, new, kwargs):
    if self.track_last_motion:
      self.app.set_state(self.track_last_motion_sensor, state=self.friendly_name.lower().replace('_', ' ').capitalize())

    if not self._should_adjust():
      return

    if self.app.utils.valid_input(old, new) and new == 'on':
      self.logger.log('{} ({}) is turning lights ON.'.format(self.name, entity), level=self.log_level)
      self.app.cancel_timer(self._handle_motion)
      for lt in self.on_lights:
        self.app.lights.turn_light_on(lt)
      self._handle_motion = self.app.run_in(self._motion_off, self.on_duration)


  def _motion_off(self, kwargs):
    self.app.cancel_timer(self._handle_motion)
    self._handle_motion = None
    if not self._should_adjust():
      return

    self.logger.log('{} ({}) is turning lights OFF.'.format(self.name, self.sensors), level=self.log_level)
    for lt in self.off_lights:
      self.app.lights.turn_light_off(lt)



