  
"""
Custom Logging app that provides a minimum cutoff level for all apps 
Allows for DEBUG level messages to be logged (Otherwise this requires an AD setting change that would log all AD DEBUG messages). 
"""

import appdaemon.plugins.hass.hassapi as hass
import datetime
import inspect
import re
import textwrap

# TODO:
#   - Save previous app threshold cutoff so that it only changes when specified by the app in the future
#   - Add looping message history list (that saved to file?)

# Minimum level of logging output (inclusive)
DEFAULT_LOGGER_CUTOFF = 'DEBUG'
DEFAULT_LEVEL = 'INFO'

LEVELS = {
        "CRITICAL": 50,
        "ERROR": 40,
        "WARNING": 30,
        "INFO": 20,
        "DEBUG": 10,
        "NOTSET": 0
    }

# RegEx to extract name of app from filename
RE_NAME = re.compile('.*\/(.*).py')


class CustomLogger(hass.Hass):

  def initialize(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')
    message_history = []
    self.app_thresholds = {}


  def set_app_threshold(self, app_name, level):
    """ Set the log level cutoff threshold for an APP - Nothing will be logged below that cutoff level """
    # self.log(f'Set {app_name} log threshold to: {level}')
    if not self._valid_log_level(level):
      self.log(f'Invalid log threshold level ({level}) for: {app_name}. Setting to default ({DEFAULT_LOGGER_CUTOFF})', level='WARNING')
      level = DEFAULT_LOGGER_CUTOFF
    self.app_thresholds[app_name] = level


  def _get_app_threshold(self, app_name):
    return self.app_thresholds.get(app_name, DEFAULT_LOGGER_CUTOFF)


  def _valid_log_level(self, level):
    if isinstance(level, int):
      for k, v in LEVELS.items():
        if v == level:
          level = k
          break
    return level in LEVELS


  def error(self, msg, level="ERROR", ha_feed=True):
    self.log(msg, level, ha_feed)


  def log(self, msg, level="INFO", ha_feed=False):
    # Get our user defined app log
    logger = self.get_user_log('app_log')

    # level passed in as an integer
    if isinstance(level, int):
      for k, v in LEVELS.items():
        if v == level:
          level = k
          break

    # Check for valid level
    if not self._valid_log_level(level):
      self.error(f'Please specify a valid logging level ({level}) for the following message: {msg}')
      level = DEFAULT_LEVEL

    # Check if log level is above cutoff
    stack = inspect.stack()
    app_name = RE_NAME.match(stack[1][1]).group(1)
    cutoff = self._get_app_threshold(app_name)
    # msg = f'[{app_name}] Checking threshold for {level} ({cutoff}): {self.app_thresholds}'
    if LEVELS[level] < LEVELS[cutoff]:
      # self._log(logger, 'DEBUG', f'Log message below logging cuttoff level (Cutoff: {cutoff}, level: {level}): {msg}')
      return

    self._log(logger, level, msg, ha_feed)


  def _log(self, logger, level, msg, ha_feed=False):
    """
    param ha_feed: Whether or not to send message to HA UI Logger feed
    """
    try:
      stack = inspect.stack()
    except Exception as e:
      logger.log(30, 'Error getting app information for custom logger. Message: {}'.format(msg))
      return

    message_format = ('{lvl} {name}.{mod} - line {ln}: {msg}'
                      .format(lvl=level,
                              name=RE_NAME.match(stack[2][1]).group(1),
                              mod=stack[2][3],
                              # ln=stack[2][2],
                              ln=stack[2].lineno,
                              msg=msg))

    logger.log(20, message_format)
    # logger.info(message_format) # 'DEBUG' or lower does not appear in logs????

    # Update the HA UI Logger feed if requested
    if ha_feed:
      self.run_in(self._update_ha_log_feed, 0.5, msg=msg)


  def _update_ha_log_feed(self, kwargs):
    self.log('HA Feed is not implemented yet')


  def test(self, entity, attribute, old, new, kwargs):
    self._unit_test(None, None, None, None, None)


  def _unit_test(self, entity, attribute, old, new, kwargs):
    msg = f'Custom_logger Test - Valid'
    for k, v in LEVELS.items():
      self.log(msg, level=k)
      self.log(msg, level=v)
    

    msg = f'Custom_logger Test - Invalid'
    self.log(msg, level='Not a real level')
    self.log(msg, level=42)

    self.log('Finished custom_logger tests.', level='INFO')

