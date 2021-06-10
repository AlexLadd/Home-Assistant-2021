
"""
App that monitors 3D Printer:
  - tool temp for overheating (notification & emergency shutoff)
  - Job completed (notification)

Created: Oct 21/2019
Last Updated: Feb 7, 2021

TODO:
  - Add smart switch to allow disabling when overheating occurs
    -> Make this configurable in yaml and disable feature if no switch exists
"""

from base_app import BaseApp
import datetime
from utils import valid_input

PRINTER_RELAY = 'switch.sonoff_s20_3d_printer_relay'

PRINTER_STATUS = 'binary_sensor.octoprint_printing'
PRINTER_PERCENT_COMPLETE = 'sensor.octoprint_job_percentage'
PRINTER_CURRENT_STATE = 'sensor.octoprint_current_state'        # Use to determine if printer is online
# States: Unknown, Operational, Printing

TIME_ELAPSED = 'sensor.octoprint_time_elapsed'
PREDICTED_TIME_REMAINING = 'sensor.octoprint_time_remaining'

TARGET_BED_TEMP_SENSOR = 'sensor.octoprint_target_bed_temp'
TARGET_TOOL_TEMP_SENSOR = 'sensor.octoprint_target_tool0_temp'
ACTUAL_BED_TEMP_SENSOR = 'sensor.octoprint_actual_bed_temp'
ACTUAL_TOOL_TEMP_SENSOR = 'sensor.octoprint_actual_tool0_temp'

MAX_TOOL_TEMP = 260
THRESHOLD_BED_TEMP = 1.05
THRESHOLD_TOOL_TEMP = 1.2

WARNING_NOTIFY_FREQUENCY = 15*60 # 15 minutes

NOTIFY_TITLE = '3D Printer'


class ThreeDPrinter(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')
    self.notifier = self.get_app('notifier')


    self.listen_state(self._tool_temp_state_change, ACTUAL_TOOL_TEMP_SENSOR)
    self.listen_state(self._printer_state_change, PRINTER_CURRENT_STATE)
    # This version of checking completion fires many, many, many more callbacks...
    # self.listen_state(self._job_state_change, PRINTER_PERCENT_COMPLETE) 

    self.handle_reboot = self.listen_event(self._ha_reboot, 'plugin_started')


  @property
  def current_state(self):
    return self.get_state(PRINTER_CURRENT_STATE)

  @property
  def target_bed_temp(self):
    try:
      return float(self.get_state(TARGET_BED_TEMP_SENSOR))
    except ValueError:
      return 0.0

  @property
  def target_tool_temp(self):
    try:
      return float(self.get_state(TARGET_TOOL_TEMP_SENSOR))
    except ValueError:
      return 0.0

  @property
  def bed_temp(self):
    try:
      return float(self.get_state(ACTUAL_BED_TEMP_SENSOR))
    except ValueError:
      return 0.0

  @property
  def tool_temp(self):
    try:
      return float(self.get_state(ACTUAL_TOOL_TEMP_SENSOR))
    except ValueError:
      return 0.0
  
  @property
  def job_percentage(self):
    try:
      return float(self.get_state(PRINTER_PERCENT_COMPLETE))
    except ValueError:
      return 0.0

  @property
  def elapsed_time(self):
    """ Time the print has been going in seconds """
    try:
      return float(self.get_state(TIME_ELAPSED))
    except ValueError:
      return -99

  @property
  def time_remaining(self):
    """ Time the print has left in seconds """
    try:
      return float(self.get_state(PREDICTED_TIME_REMAINING))
    except ValueError:
      return -99

  @property
  def _safe_temps(self):
    if self.tool_temp > MAX_TOOL_TEMP or \
        (self.tool_temp > self.target_tool_temp * THRESHOLD_TOOL_TEMP and self.target_tool_temp > 0) or \
        (self.bed_temp > self.target_bed_temp * THRESHOLD_BED_TEMP and self.target_bed_temp > 0):
      return False
    return True
  
  @property
  def _printer_relay_on(self):
    return bool(self.get_state(PRINTER_RELAY) == 'on')


  def _ha_reboot(self, event_name, data, kwargs):
    # self._logger.log('Home assistant restarted.')
    if self._safe_temps:
      self._turn_on_relay()
    else:
      self._turn_off_relay()


  def _turn_on_relay(self):
    if not self._printer_relay_on:
      self._logger.log('3D Printer relay turned on.')
      self.turn_on(PRINTER_RELAY)


  def _turn_off_relay(self):
    if self._printer_relay_on:
      self._logger.log('3D Printer relay turned off.')
      self.turn_off(PRINTER_RELAY)


  def _tool_temp_state_change(self, entity, attribute, old, new, kwargs):
    if valid_input(old, new):
      try:
        target_bed_temp = float(self.get_state(TARGET_BED_TEMP_SENSOR))
        target_tool_temp = float(self.get_state(TARGET_TOOL_TEMP_SENSOR))
      except:
        self._logger.log(f'Invalid printer temperatures. It might be off? Bed temp: {self.get_state(TARGET_BED_TEMP_SENSOR)}, Tool temp: {self.get_state(TARGET_TOOL_TEMP_SENSOR)}.', level='WARNING')
        return

      if self.target_bed_temp <= 0 and self.target_tool_temp <= 0:
        # The printer is off
        return

      if not self._safe_temps:
        self._turn_off_relay()
        self.run_in(self._warning_notify_callback, 5)
      else:
        self._turn_on_relay()


  def _warning_notify_callback(self, kwargs):
    # Make sure the printer is cut off from power!!!
    self._turn_off_relay()

    if self.target_bed_temp <= 0 and self.target_tool_temp <= 0:
        # The printer is off or the job has been cancelled
      msg = f'The 3D Printer has been turned off after overheating. Bed temp: {self.bed_temp} (target: {self.target_bed_temp}) & Tool temp: {self.tool_temp} (targer: {self.target_tool_temp}).'
      self._logger.log(msg)
      self.notifier.telegram_notify(msg, 'alarm', NOTIFY_TITLE)
      return

    if not self._safe_temps:
      msg = f'The 3D Printer is overheating!!! Please have a look now! Bed temp: {self.bed_temp} (target: {self.target_bed_temp}) & Tool temp: {self.tool_temp} (targer: {self.target_tool_temp}).'
      self._logger.log(msg)
      self.notifier.telegram_notify(msg, 'alarm', NOTIFY_TITLE)
      # self.notifier.tts_notify(msg, speaker_override=True)
      self.run_in(self._warning_notify_callback, WARNING_NOTIFY_FREQUENCY)
    else:
      msg = 'The 3D Printer has cooled down after overheating. Bed temp: {self.bed_temp} (target: {self.target_bed_temp}) & Tool temp: {self.tool_temp} (targer: {self.target_tool_temp}).'
      self._logger.log(msg)
      self.notifier.telegram_notify(msg, 'alarm', NOTIFY_TITLE)


  def _job_state_change(self, entity, attribute, old, new, kwargs):
    if valid_input(old, new):
      try:
        percent = float(new)
        if percent >= 100:
          msg = f'The 3D Printer job is complete. Total time is {int(self.elapsed_time/60)} minutes and the ramaining time is {int(self.time_remaining/60)} minutes.'
          self._logger.log(msg)
          self.notifier.telegram_notify(msg, 'logging', NOTIFY_TITLE)
          self.notifier.tts_notify(msg)
      except:
        # Not a float
        pass

  
  def _printer_state_change(self, entity, attribute, old, new, kwargs):
    if not self.utils.valid_input(old, new) or old == 'None' or new == 'None' or new is None or old is None:
      return

    self._logger.log(f'Octoprint changed state from {old} to {new}. Current state: {self.current_state}')

    # Finished a print!
    if old == 'Printing' and new == 'Operational':
      msg = f'The 3D printer is finished printing. The total time was {int(self.elapsed_time/60)} minutes.'
      self._logger.log(msg)
      self.notifier.tts_notify(msg)


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(self._printer_relay_on)
    pass

  def terminate(self):
    pass