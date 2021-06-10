
"""
Appdaemon App Constants
"""

# Helpers
INVALID_STATES = ['unavailable', 'unknown', 'Unavailable', 'Unknown', 'None']


# Alarm Stuff
ALARM_CONTROL_PANEL = 'alarm_control_panel.ha_alarm'


# Mode Booleans
EMERGENCY_MODE_BOOLEAN = 'input_boolean.emergency_mode'
VACATION_MODE_BOOLEAN = 'input_boolean.vacation_mode'
GUEST_MODE_BOOLEAN = 'input_boolean.guest_mode'
PET_MODE_BOOLEAN = 'input_boolean.pet_mode'
SPEECH_OVERRIDE_BOOLEAN = 'input_boolean.speech_mode'
MANUAL_HVAC_MODE = 'input_boolean.manual_hvac_mode'
AUTOMATED_HVAC_MODE_BOOLEAN = 'input_boolean.automated_hvac_mode'
HEAT_MODE_BOOLEAN = 'input_boolean.heat_mode'
AC_MODE_BOOLEAN = 'input_boolean.ac_mode'
DARK_MODE_BOOLEAN = 'input_boolean.dark_mode'


# Household Sensors
HOLIDAY_SENSOR = 'sensor.holiday'
SEASON_SENSOR = 'sensor.season'




# Sleep Booleans
ALEX_AWAKE_BOOLEAN = 'input_boolean.alex_awake'
STEPH_AWAKE_BOOLEAN = 'input_boolean.steph_awake'
EVERYONE_AWAKE_BOOLEAN = 'input_boolean.everyone_awake'
EVERYONE_ASLEEP_BOOLEAN = 'input_boolean.everyone_asleep'




# Presence Booleans
ALEX_PERSON = 'person.alex'
STEPH_PERSON = 'person.steph'

LAST_MOTION_LOCATION_SENSOR = 'sensor.last_motion_location'

BOTH_TOGETHER_SENSOR = 'input_boolean.both_together'
OCCUPANCY_BOOLEAN = 'input_boolean.occupancy'
ALEX_AWAY_BOOLEAN = 'input_boolean.alex_away'
STEPH_AWAY_BOOLEAN = 'input_boolean.steph_away'




# Time Related Constants
# These times are used throughout appdaemon, be careful changing them...
# ALEX_WAKEUP_TIME = '09:00:00'
# STEPH_WAKEUP_TIME = '08:58:00'


DAY_START = '03:30:00'
DAY_END = '15:00:00'
NIGHT_END = '22:30:00'

# Rough times we would be set to asleep
BEDTIME_START = '18:00:00'
BEDTIME_END = '03:30:00'
DEFAULT_WAKEUP = '07:00:00'
DEFAULT_ASLEEP = '22:30:00'


WINTER_MONTH_START = 'December'   # inclusive
WINTER_MONTH_END = 'February'     # inclusive 
AC_MONTH_START = 'May'            # inclusive
AC_MONTH_END = 'September'        # inclusive 
HEAT_MONTH_START = 'November'     # inclusive
HEAT_MONTH_END = 'March'          # inclusive 


# Tracking stuff
ALEX_MORNING_GREETING_BOOLEAN = 'input_boolean.alex_morning_greeting_complete_today'
STEPH_MORNING_GREETING_BOOLEAN = 'input_boolean.steph_morning_greeting_complete_today'


# Config Validation Constants
CONF_FRIENDLY_NAME = 'friendly_name'
CONF_SENSORS = 'sensors'
CONF_ALIASES = 'aliases'
CONF_ENTITY_ID = 'entity_id'
CONF_OPTIONS = 'options'
CONF_DEFAULTS = 'defaults'
CONF_PROPERTIES = 'properties'
CONF_LOG_LEVEL = 'log_level' # Log level at the individual motion sensor (class) level

