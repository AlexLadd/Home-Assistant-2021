
from base_app import BaseApp 
import datetime
from const import VACATION_MODE_BOOLEAN, AC_MODE_BOOLEAN, HEAT_MODE_BOOLEAN, AUTOMATED_HVAC_MODE_BOOLEAN
from utils import is_winter_months, valid_input, month_is_between

# TODO:
#   - Incorporate presence and eta to home when heading home?
#   - Add functionality to raise temperature when AC is on and we have been sleeping for a couple hours, perhaps raise up again close to waking up???
#   - Add in schedules for temperatures? (use in get_heat/ac_temp)
#   - Add option to heat/cool house using temperature in a specific room


DOOR_WINDOW_OPEN_TRIGGER_TIME = 5*60
DOOR_WINDOW_MESSAGE_INTERVAL = 4*60*60

EMERGENCY_LOW_TEMP_CUTOFF = 10

WINTER_HEAT_TEMP = 22
NON_WINTER_HEAT_TEMP_COOL = 18
NON_WINTER_HEAT_TEMP_WARM = 21
VACATION_HEAT_TEMP = 15

NOTIFY_TARGET = 'everyone'
NOTIFY_TITLE = 'Climate Controls'


class SmartClimate(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_2')

    self.climate = self.get_app('climate')
    self.notifier = self.get_app('notifier')
    self.dw = self.get_app('doors_windows')
    self.sleep = self.get_app('sleep')
    self.presence = self.get_app('presence')

    self._last_ac_mode = self.climate.ac_mode
    self._last_heat_mode = self.climate.heat_mode

    self._handle_turn_fan_on = None

    self.listen_state(self._automated_hvac_mode_callback, AUTOMATED_HVAC_MODE_BOOLEAN)
    self.listen_state(self._ac_mode_callback, AC_MODE_BOOLEAN)
    self.listen_state(self._heat_mode_callback, HEAT_MODE_BOOLEAN)

    # self.listen_state(self._windows_closed, 'group.door_window_sensors_master', new='off')
    # self.listen_state(self._windows_open, 'group.door_window_sensors_master', new='on', duration=DOOR_WINDOW_OPEN_TRIGGER_TIME)

    # run once per hour, on the hour
    self.run_hourly(self._hvac_algo, datetime.time(0,0,0))
    self._hvac_algo()
    # Check for open windows on AD restart while the furnace is running (AC/Heat)
    # if self.dw.is_open() and self.climate.hvac_state != 'off':
    #   self._windows_open(None, None, None, 'on', None)


  def _automated_hvac_mode_callback(self, entity, attribute, old, new, kwargs):
    """ Automated mode state change """
    self._logger.log(f'Automated mode is now "{new}""', level='DEBUG')
    self._hvac_algo()

  
  def _ac_mode_callback(self, entity, attribute, old, new, kwargs):
    """ AC mode state change """
    self._logger.log(f'AC mode is now "{new}""', level='DEBUG')
    self._hvac_algo()

  
  def _heat_mode_callback(self, entity, attribute, old, new, kwargs):
    """ Heat mode state change """
    self._logger.log(f'Heat mode is now "{new}""', level='DEBUG')
    self._hvac_algo()


  def get_ac_temp(self):
    """ Locic for what the current AC temp should be """
    return None


  def get_winter_temp(self):
    """ Locic for what the current HEAT temp should be """
    temp = NON_WINTER_HEAT_TEMP_WARM
    if self.presence.vacation_mode:
      temp = VACATION_HEAT_TEMP
    elif is_winter_months():
      temp = WINTER_HEAT_TEMP
    else:
      if self.climate.pws_ready:
        if self.climate.todays_low < -2 and self.climate.todays_high < 0:
          temp = NON_WINTER_HEAT_TEMP_WARM
        else:
          temp = NON_WINTER_HEAT_TEMP_COOL
    return temp


  def _update_ac_mode(self):
    """ Logic for updating AC mode - Reflected in ac_mode boolean """
    self._logger.log(f'AC is not installed in this house yet.', level='DEBUG')
    return

    self._last_ac_mode = self.climate.ac_mode

    # Never turn on AC Mode during the winter
    if self.is_winter_months():
      self.climate.set_ac_mode('off')
      return

    # If PWS is not up to date than don't do anything
    if self.cliamte.pws_ready:
      self._logger.log(f'PWS not ready. AC mode will not be updated.', level='WARNING')
      return

    if self.climate.ac_mode and self.sleep.everyone_asleep:
      return
    elif 3 < datetime.datetime.now().hour < 12 and self.climate.todays_high and self.climate.todays_high > 27:
      self.climate.set_ac_mode('on')
    elif datetime.datetime.now().hour >= 17:
      if self.climate.tomorrows_high and self.climate.tomorrows_high > 27:
        if self.climate.todays_low and self.climate.todays_low > 20:
          self.climate.set_ac_mode('on')
        elif self.climate.ac_mode and self.climate.current_outdoor_temp and self.climate.current_outdoor_temp > 23: 
          # this does nothing but keep the ac on
          return
        elif self.climate.current_outdoor_temp and self.climate.current_outdoor_temp > 25: # TODO: add in indoor temp checks here
          self.climate.set_ac_mode('on')
        else:
          self.climate.set_ac_mode('off')
      else:
        if self.climate.current_outdoor_temp and self.climate.current_outdoor_temp < 23 and \
            self.climate.todays_low and self.climate.todays_low < 20:
          self.climate.set_ac_mode('off')


  def _update_heat_mode(self):
    """ Logic for updating HEAT mode - Reflected in heat_mode boolean """
    self._last_heat_mode = self.climate.heat_mode

    # Heat is always on during the winter months!
    if is_winter_months():
      self.climate.set_heat_mode('on')
      return

    # If PWS is not up to date than don't do anything
    # if not self.climate.pws_ready:
    #   self._logger.log(f'PWS not ready. HEAT mode will not be updated.', level='WARNING')
    #   return

    # Adjust heat mode based on outdoor temperatures - This only occurs during transitional seasons
    if self.now_is_between(self.const.DAY_START, self.const.DAY_END):
      if self.climate.todays_low < -2 and self.climate.todays_high < 2:
        self.climate.set_heat_mode('on')
    elif self.now_is_between(self.const.DAY_END, self.const.DAY_START):
      if self.climate.todays_low < -2 and self.climate.tomorrows_high < 2:
        self.climate.set_heat_mode('on')

    if self.climate.average_indoor_temp and self.climate.average_indoor_temp < 15:
      self.climate.set_heat_mode('on')
    elif self.climate.current_outdoor_temp and self.climate.current_outdoor_temp > 2 and \
        self.climate.todays_low and self.climate.todays_low > 4:
      self.climate.set_heat_mode('off')


  def _turn_on_fan(self, heat_temp=None, ac_temp=None):
    """ Heat or AC must be on for the fan to be running """


    if heat_temp is None and ac_temp is None:
      self.climate.set_hvac_heat(temperature=EMERGENCY_LOW_TEMP_CUTOFF)
    elif ac_temp is None:
      self.climate.set_hvac_heat(temperature=heat_temp)
    elif heat_temp is None:
      self.climate.set_hvac_ac(temperature=ac_temp)

    self.climate.set_fan_mode('on')

    # if self._handle_turn_fan_on is not None:
    #   self.cancel_timer(self._handle_turn_fan_on)
    #   self._handle_turn_fan_on = None
    # self._handle_turn_fan_on = self.run_in(lambda *_: self.climate.set_fan_mode('on'), 1)


  def _hvac_algo(self, entity=None, attribute=None, old=None, new=None, kwargs=None):
    """ Top level call to run the HVAC algorithm. Do not use AC/HEAT function calls independently. They will be called from here. """

    # FAILSAFE CHECK
    if not self.climate.average_indoor_temp:
      self._logger.log(f'Indoor average temperature sensor not reading correctly!', level='WARNING')

    if self.climate.average_indoor_temp and self.climate.average_indoor_temp < EMERGENCY_LOW_TEMP_CUTOFF:
      msg = f'Climate failsafe check failed! Average indoor temperate: "{self.climate.average_indoor_temp}", Current HVAC State: "{self.climate.hvac_state}"'
      
      if (is_winter_months() or (self.climate.current_outdoor_temp and self.climate.current_outdoor_temp < 0)):
        # Winter months or cold outside
        if self.climate.hvac_state != 'heat':
          msg += ' The furnace is on, however, it is very cold. Please look immediately!'
          self.cliamte.set_hvac_heat(temperature=self.get_winter_temp())
      elif self.cliamte.hvac_state == 'cool':
        # The AC is on...
        msg += ' The AC was on... Turning off now.'
        self.cliamte.set_hvac_off()  
      else:
        # It not cold outside and the AC isn't on...
        msg += ' Not sure why its so cold inside...'

      self._logger.log(msg, level='WARNING')
      # self.notifier.NOTIFY_EVERYONE_EVERYWEHRE(msg)
      return

    # If manual HVAC mode is on than do nothing...
    if self.climate.manual_hvac_mode:
      self._logger.log(f'Manual HVAC mode is on. The system will not make any adjustments.', level='INFO')
      return

    # Automated mode allows for updating heat/ac mode
    if self.climate.automated_hvac_mode:
      if is_winter_months():
        # Winter months
        self._logger.log(f'Maintaining automated winter month heating temperatures.', level='DEBUG')
        self.climate.set_heat_mode('on')
        self.climate.set_ac_mode('off')
        self.climate.set_hvac_heat(temperature=self.get_winter_temp())

      else:
        # Not Winter months
        self._update_heat_mode()
        self._update_ac_mode()

        # Check what eco mode does...?
        if self.presence.vacation_mode and not is_winter_months():
          self._logger.log(f'Setting thermostat to eco mode.', level='DEBUG')
          self.climate.set_hvac_eco()

        elif self.climate.heat_mode:
          self._logger.log(f'Setting thermostat to heat mode.', level='DEBUG')
          self.climate.set_hvac_heat(temperature=self.get_winter_temp())

        elif self.climate.ac_mode:
          if self.dw.is_open(min_open_time=DOOR_WINDOW_OPEN_TRIGGER_TIME):
            self._logger.log(f'The AC is not turning on because the windows are open.', level='DEBUG')
            self.climate.set_hvac_off()
          else:
            self._logger.log(f'Setting thermostat to AC mode.', level='DEBUG')
            self.climate.set_hvac_ac(temperature=self.get_ac_temp())

        # This is the last check before turning everything off
        elif self.now_is_between('17:00:00', '04:00:00') and self.presence.someone_home and self._warm_upstairs():
          if not self.dw.windows_closed and self.climate.hvac_fan_state != "on":
            msg = f'The furnace fan is turning on to cool down the master bedroom before bed but there are some windows open.'
            self.notifier.tts_notify(msg)
            log_msg = f'{msg} Open windows: {self.dw.entry_point_check(door_check=False)}'
            self.notifier.telegram_notify(log_msg)
            self._logger.log(log_msg, level='INFO')
          self._logger.log(f'Turning furnace fan on to cool house before bed.', level='DEBUG')
          self._turn_on_fan()

        # Nothing to do... turning system off
        else:
          self._logger.log(f'Turning HVAC off.', level='DEBUG')
          self.climate.set_hvac_off()

    # Automated mode is off
    else:
      self._logger.log(f'Automated HVAC mode is off. Using current AC/Heat modes.', level='DEBUG')
      if self.climate.heat_mode:
        self.climate.set_hvac_heat(temperature=self.get_winter_temp())
      elif self.climate.ac_mode:
        self.climate.set_hvac_ac(temperature=self.get_ac_temp())


  def _warm_upstairs(self):
    """ Return True if it is warm upstairs """
    upstairs_temp_threshold = 20
    if self.climate.average_indoor_temp is not None and self.climate.average_indoor_temp > upstairs_temp_threshold:
      return True
    elif self.climate.study_temp is not None and self.climate.study_temp > upstairs_temp_threshold:
      return True
    elif self.climate.master_bedroom_temp is not None and self.climate.master_bedroom_temp > upstairs_temp_threshold:
      return True
    else:
      return False


  def terminate(self):
    pass


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing climate_controller Module: ')
    self._turn_on_fan()





