"""
TODO: 
  - Add check for available services (they sometime fail to load when AD restarts)
"""

from base_app import BaseApp
import datetime

SUNRISE_OFFSET = 20
SUNSET_OFFSET = -20

DAILY_BOOLEANS = [
  'input_boolean.alex_morning_greeting_complete_today',
  'input_boolean.steph_morning_greeting_complete_today',
]


class DailyRoutines(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.notifier = self.get_app('notifier')
    self.presence = self.get_app('presence')
    # self.cameras = self.get_app('camera') Setup camera preset and dt

    self.handle_reboot = self.listen_event(self._ha_reboot, 'plugin_started')
    self.handle_daily_reset = self.run_daily(self._reset_daily_booleans, datetime.time(3, 30, 0))
    # W/O delay calling sunrise() and sunset() can cause errors on startup
    self.run_in(self._setup, 3)


  def _ha_reboot(self, event_name, data, kwargs):
    self._logger.log('Home assistant restarted.')
    # self.call_service('frontend/set_theme', name='Dark - Cyan')
    self.run_in(lambda *_: self._dark_mode_check(), 2)
    # self.run_in(lambda *_: self._zwave_reboot_check(), ZWAVE_REBOOT_CHECK_DELAY)

    # Reset camera preset position and set time
    # success = self.cameras.set_camera_preset('outside_frontyard', 'default')
    # if not success:
    #   self._logger.log('Failed to set front entrance camera to default preset (towards the front door).', level='WARNING')
    # success = self.cameras.set_camera_dt('outside_frontyard')
    # if not success:
    #   self._logger.log('Failed to set front entrance camera to the current time.', level='WARNING')


  def _zwave_reboot_check(self):
    # Called after HA/AD reboots after short delay
    state = self.get_state()
    if ZWAVE_STICK not in state:
      self._logger.log("ZWAVE not started after HA/AD reboot.")
    else:
      self._logger.log('ZWAVE started successfully.')


  def _setup(self, kwargs):
    # Set up sunrise/sunset callbacks
    self._setup_dark_mode_listeners()
    # Check that dark mode is in correct state on reboot
    self._dark_mode_check()
  

  def _setup_dark_mode_listeners(self):
    # self._logger.log(f'Sunset/Sunrise offset: {datetime.timedelta(minutes=SUNSET_OFFSET).total_seconds()}')
    self.run_at_sunrise(
      self._dark_mode_off, 
      offset=datetime.timedelta(minutes=SUNRISE_OFFSET).total_seconds()
    )
    self.run_at_sunset( 
      self._dark_mode_on, 
      offset=datetime.timedelta(minutes=SUNSET_OFFSET).total_seconds()
    )
    self.run_at_sunset(self._dark_mode_on)

  
  def _dark_mode_check(self):
    sr_time = (self.sunrise() + datetime.timedelta(minutes=SUNRISE_OFFSET)).time()
    ss_time = (self.sunset() + datetime.timedelta(minutes=SUNSET_OFFSET)).time()
    now_time = self.time()
    if now_time >= sr_time and now_time <= ss_time:
      self._dark_mode_off(None)
    else:
      self._dark_mode_on(None)


  def _dark_mode_on(self, kwargs):
    # self._test_sun_rise_down_times()
    if self.get_state(self.const.DARK_MODE_BOOLEAN) == 'off':
      self._logger.log('Dark mode turned on.')  
      self.turn_on(self.const.DARK_MODE_BOOLEAN)


  def _dark_mode_off(self, kwargs):
    if self.get_state(self.const.DARK_MODE_BOOLEAN) == 'on':
      self._logger.log('Dark mode turned off.')
      self.turn_off(self.const.DARK_MODE_BOOLEAN)


  def _reset_daily_booleans(self, kwargs):
    self._logger.log('Reseting daily booleans now...')
    for b in DAILY_BOOLEANS:
      if self.presence.steph_away and b == 'input_boolean.steph_morning_greeting_complete_today':
        continue
      elif self.presence.alex_away and b == 'input_boolean.alex_morning_greeting_complete_today':
        continue
      else:
        self.turn_off(b)


  def test(self, entity, attribute, old, new, kwargs):
    self.log(f'Testing DailyRoutines Module: ') 
    self._test_sun_rise_down_times()

  
  def _test_sun_rise_down_times(self):
    self.log("--------------------------------------------------")
    self.log("Sun logging test")
    self.log("Next Sunrise: %s", self.sunrise())
    self.log("Next Sunset: %s", self.sunset())
    self.log("Sun down: %s", self.sun_down())
    self.log("Sun up: %s", self.sun_up())
    self.log("--------------------------------------------------")