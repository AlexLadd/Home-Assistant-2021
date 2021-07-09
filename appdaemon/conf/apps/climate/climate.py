
"""
Base climate app 
  -> Only dependency is the base_app

Functionality:
  -> Outdoor weather data [PWS]
  -> Indoor temps, humidity, light levels
  -> Thermostat control and data

Future updates:
  -> Add in controls for ceiling fans
  -> Add in AC/Cooling functionality


Last updates: Jan 22, 2021
"""

from base_app import BaseApp 
from const import MANUAL_HVAC_MODE, AC_MODE_BOOLEAN, HEAT_MODE_BOOLEAN, AUTOMATED_HVAC_MODE_BOOLEAN
from utils import up_to_date_wrapper

import datetime
from functools import wraps

THERMOSTAT = 'climate.entryway'
DEFAULT_AC_TEMP = 21
DEFAULT_HEAT_TEMP = 22

# Weather Forecast Sensor
WEATHER_SENSOR = 'weather.home'

# Time since last PWS update before consider 'out of date'
PWS_MAX_SENSOR_UPDATE_INTERVAL = 20 # MINUTES


class Climate(BaseApp):

  def setup(self):
    """ Called upon app creation """
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self._last_hvac_state = None
    self._last_hvac_preset_mode = None
    self._last_temperature = None


  # ********** OUTDOOR SENSORS START **********

  @property
  def pws_ready(self):
    """ Returns if PWS is online and up to date """
    return self._pws_online and self._pws_upto_date

  @property
  def _pws_online(self):
    """ PWS sensors reading correctly """
    if self.current_outdoor_temp is not None and self.todays_low is not None and \
        self.todays_high is not None:
      return True
    else:
      return False

  @property
  def _pws_upto_date(self):
    """ Unit has sent data recently """
    try:
      last_update = self.get_state('sensor.wupws_pressure', attribute='all')['attributes']['date']
    except KeyError:
      return False

    last_update = datetime.datetime.strptime(last_update, '%Y-%m-%d %H:%M:%S')
    diff = self.datetime() - last_update
    mins_since_last_update = int(diff.total_seconds()/60) # Rounded down to nearest minute

    return mins_since_last_update < PWS_MAX_SENSOR_UPDATE_INTERVAL

  @property
  def apparent_outdoor_temp(self):
    """ Current apparent temperature based on wind chill/heat index """
    if not self.pws_ready:
      return None

    if self.current_outdoor_temp < self.current_heat_index:
      return self.current_heat_index
    elif self.current_outdoor_temp > self.current_wind_chill:
      return self.current_wind_chill
    else:
      return self.current_outdoor_temp

  @property
  @up_to_date_wrapper('sensor.wupws_temp', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_outdoor_temp(self):
    try:
      return int(float(self.get_state('sensor.wupws_temp')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_temp", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_temp_high_1d', 60*8)
  def todays_high(self):
    try:
      return int(float(self.get_state('sensor.wupws_temp_high_1d')))
    except ValueError:
      try:
        return int(self.utils.get_last_valid_state(self, "sensor.wupws_temp_high_1d", 'unknown'))
      except ValueError:
        return None

  @property
  @up_to_date_wrapper('sensor.wupws_temp_low_1d', 60*8)
  def todays_low(self):
    try:
      return int(float(self.get_state('sensor.wupws_temp_low_1d')))
    except ValueError:
      try:
        return int(self.utils.get_last_valid_state(self, "sensor.wupws_temp_low_1d", 'unknown'))
      except ValueError:
        return None

  @property
  @up_to_date_wrapper('sensor.wupws_uv', 60*14) # Might not update overnight for long periods
  def current_uv(self):
    try:
      return int(float(self.get_state('sensor.wupws_uv')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_uv", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_solarradiation', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_solar_radiation(self):
    # This value is more representative of the sun's progression throughout the day
    # Units: w/m2
    try:
      return int(float(self.get_state('sensor.wupws_solarradiation')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_solarradiation", 'unknown')
  
  @property
  @up_to_date_wrapper('sensor.wupws_dewpt', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_dew_point(self):
    try:
      return int(float(self.get_state('sensor.wupws_dewpt')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_dewpt", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_humidity', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_humidity(self):
    # Units: %
    try:
      return int(float(self.get_state('sensor.wupws_humidity')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_humidity", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_winddir', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_wind_direction(self):
    # Units: degrees (0 to 360)
    try:
      return int(float(self.get_state('sensor.wupws_winddir')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_winddir", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_windgust', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_wind_gust_speed(self):
    # Units: kph
    try:
      return int(float(self.get_state('sensor.wupws_windgust')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_windgust", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_windspeed', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_wind_speed(self):
    # Units: kph
    try:
      return int(float(self.get_state('sensor.wupws_windspeed')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_windspeed", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_wind_1d', 60*8)
  def average_wind_speed_today(self):
    # Units: kph
    try:
      return int(float(self.get_state('sensor.wupws_wind_1d')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_wind_1d", 'unknown')
  
  @property
  @up_to_date_wrapper('sensor.wupws_windchill', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_wind_chill(self):
    try:
      return int(float(self.get_state('sensor.wupws_windchill')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_windchill", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_heatindex', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_heat_index(self):
    try:
      return int(float(self.get_state('sensor.wupws_heatindex')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_heatindex", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_precip_chance_1d', 60*30)
  def precip_chance_today(self):
    # % chance of precipitation today
    try:
      return int(float(self.get_state('sensor.wupws_precip_chance_1d')))
    except ValueError:
      # If it is currently raining than its 100%
      try:
        if self.current_precip_rate > 0:
          return 100
        else:
          return self.utils.get_last_valid_state(self, "sensor.wupws_precip_chance_1d", 'unknown')
      except TypeError:
        return self.utils.get_last_valid_state(self, "sensor.wupws_precip_chance_1d", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_precip_1d', 60*8)
  def expected_precip_today(self):
    # Amount of precipitation expected today (in mm)
    try:
      return int(float(self.get_state('sensor.wupws_precip_1d')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_precip_1d", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_preciprate', PWS_MAX_SENSOR_UPDATE_INTERVAL)
  def current_precip_rate(self):
    # Current precipitation rate (in mm/h)
    try:
      return int(float(self.get_state('sensor.wupws_preciprate')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_preciprate", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_preciptotal', 60*8)
  def precip_accumulation_today(self):
    # Total precipitation accumulation that has occured today (in mm)
    try:
      return int(float(self.get_state('sensor.wupws_preciptotal')))
    except ValueError:
      return self.utils.get_last_valid_state(self, "sensor.wupws_preciptotal", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_weather_1d', 60*8)
  def day_forecast(self):
    # Text forecast for day time
    r = self.get_state('sensor.wupws_weather_1d')
    if r != 'unknown':
      return r
    else:
      return self.utils.get_last_valid_state(self, "sensor.wupws_weather_1d", 'unknown')

  @property
  @up_to_date_wrapper('sensor.wupws_weather_1n', 60*8)
  def night_forecast(self):
    # Text forecast for over night
    r = self.get_state('sensor.wupws_weather_1n')
    if r != 'unknown':
      return r
    else:
      return self.utils.get_last_valid_state(self, "sensor.wupws_weather_1d", 'unknown')

    # *********** OUTDOOR WEATHER FORECAST ***********

  @property
  @up_to_date_wrapper('sensor.wupws_weather_1n', 60*8)
  def tomorrows_high(self):
    try:
      return int(self.get_state('weather.home', attribute='all')['attributes']['forecast'][0]['temperature'])
    except (KeyError, ValueError):
      return None

  @property
  @up_to_date_wrapper('sensor.wupws_weather_1n', 60*8)
  def tomorrows_low(self):
    try:
      return int(self.get_state('weather.home', attribute='all')['attributes']['forecast'][0]['templow'])
    except (KeyError, ValueError):
      return None
  
  # ********** OUTDOOR SENSORS END **********

  # ********** INDOOR SENSORS START **********
  
  @property
  def entryway_temp(self):
    try:
      # return float(self.get_state(THERMOSTAT, attribute="current_temperature"))
      return int(float(self.get_state('sensor.entryway_temperature')))
    except ValueError:
      return None

  @property
  def kitchen_temp(self):
    try:
      return int(float(self.get_state('sensor.hue_motion_kitchen_temperature')))
    except ValueError:
      return None

  @property
  def master_bedroom_temp(self):
    try:
      return int(float(self.get_state('sensor.hue_motion_master_bedroom_temperature')))
    except ValueError:
      return None

  @property
  def study_temp(self):
    try:
      return int((self.study_1_temp + self.study_2_temp) / 2)
    except ValueError:
      return None
  
  @property
  def study_2_temp(self):
    try:
      return int(float(self.get_state('sensor.hue_motion_study_2_temperature')))
    except ValueError:
      return None

  @property
  def study_1_temp(self):
    try:
      return int(float(self.get_state('sensor.hue_motion_study_temperature')))
    except ValueError:
      return None

  @property
  def living_room_temp(self):
    try:
      return int(float(self.get_state('sensor.living_room_motion_sensor_temperature')))
    except ValueError:
      return None

  @property
  def master_bathroom_temp(self):
    try:
      return int(float(self.get_state('sensor.master_bathroom_motion_sensor_temperature')))
    except ValueError:
      return None

  @property
  def average_indoor_temp(self):
    try:
      temps = [self.entryway_temp, self.study_temp, self.master_bathroom_temp, self.master_bedroom_temp, self.living_room_temp, self.kitchen_temp]
      temps_clean = [t for t in temps if t is not None]
      if len(temps) != len(temps_clean):
        self._logger.log(f'One or more indoor temperature sensors are not reading correctly!', level='WARNING')
      if len(temps_clean) <= 0:
        self._logger.log(f'None of the indoor temperature sensors are reading correctly!', level='WARNING')
        return None
      return int(sum(temps_clean)/len(temps_clean))
    except TypeError:
      return None

  @property
  def entryway_humidity(self):
    try:
      return int(float(self.get_state('sensor.entryway_humidity')))
    except ValueError:
      return None
  
  @property
  def master_bathroom_humidity(self):
    try:
      return int(float(self.get_state('sensor.master_bathroom_motion_sensor_relative_humidity')))
    except ValueError:
      return None

  @property
  def living_room_humidity(self):
    try:
      return int(float(self.get_state('sensor.living_room_motion_sensor_relative_humidity')))
    except ValueError:
      return None

  @property
  def basement_storage_humidity(self):
    try:
      return int(float(self.get_state('sensor.basement_storage_temperature_and_humitidy_sensor_humidity')))
    except ValueError:
      return None

  @property
  def average_indoor_humidity(self):
    try:
      hum = [self.entryway_humidity, self.master_bathroom_humidity, self.living_room_humidity, self.basement_storage_humidity]
      hum = [x for x in hum if x is not None]
      return int(sum(hum)/len(hum))
    except TypeError:
      return None

  @property
  def master_bathroom_light_level(self):
    # This one is a percentage from 0-100, unlike the other sensors which vary with the light levels with more sensitivity
    # Units %
    try:
      return int(float(self.get_state('sensor.master_bathroom_motion_sensor_luminance')))
    except ValueError:
      return None

  @property
  def living_room_light_level(self):
    try:
      return int(float(self.get_state('sensor.living_room_motion_sensor_luminance')))
    except ValueError:
      return None

  @property
  def study_light_level(self):
    try:
      return int((self.study_1_light_level + self.study_2_light_level) / 2)
    except ValueError:
      return None

  @property
  def study_1_light_level(self):
    try:
      return int(float(self.get_state('sensor.hue_motion_study_light_level')))
    except ValueError:
      return None

  @property
  def study_2_light_level(self):
    try:
      return int(float(self.get_state('sensor.hue_motion_study_2_light_level')))
    except ValueError:
      return None

  @property
  def kitchen_light_level(self):
    try:
      return int(float(self.get_state('sensor.hue_motion_kitchen_light_level')))
    except ValueError:
      return None

  @property
  def master_bedroom_light_level(self):
    try:
      return int(float(self.get_state('sensor.hue_motion_master_bedroom_light_level')))
    except ValueError:
      return None

  @property
  def average_indoor_light_level(self):
    try:
      temps = [self.study_light_level, self.master_bathroom_light_level, self.master_bedroom_light_level, self.living_room_light_level, self.kitchen_light_level]
      temps = [x for x in temps if x is not None]
      return int(sum(temps)/len(temps))
    except TypeError:
      return None

  # ********** INDOOR SENSORS START **********


  # ********** INDOOR CLIMATE/THERMOSTAT CONTROLS BELOW **********

  @property
  def manual_hvac_mode(self):
    return bool(self.get_state(MANUAL_HVAC_MODE) == 'on')

  @property
  def automated_hvac_mode(self):
    return bool(self.get_state(AUTOMATED_HVAC_MODE_BOOLEAN) == 'on')

  @property
  def heat_mode(self):
    return bool(self.get_state(HEAT_MODE_BOOLEAN) == 'on')

  @property
  def ac_mode(self):
    return bool(self.get_state(AC_MODE_BOOLEAN) == 'on')

  @property
  def hvac_state(self):
    """ What the hvac is currently doing: auto, heat, cool, off """
    return self.get_state(THERMOSTAT)

  @property
  def hvac_preset_mode(self):
    """ Options: none, away, eco, Away and Eco """
    return self.get_state(THERMOSTAT, attribute='preset_mode')

  @property
  def hvac_fan_state(self):
    """ Current HVAC fan state - Options: 'on', 'off' """
    return self.get_state(THERMOSTAT, attribute='fan_mode')

  @property
  def hvac_action(self):
    """ Current HVAC action. Options: 'heating', '', ... """
    return self.get_state(THERMOSTAT, attribute='hvac_action')

  @property
  def target_temperature(self):
    try:
      return float(self.get_state(THERMOSTAT, attribute="temperature"))
    except:
      # When in eco mode there is no target temperature
      return -99

  @property
  def last_hvac_state(self):
    return self._last_hvac_state

  @property
  def last_thermostat_temperature(self):
    return self._last_temperature 

  @property
  def last_hvac_preset_mode(self):
    return self._last_hvac_preset_mode


  def set_manual_hvac_mode(self, state):
    if state == 'on' and not self.hvac_mode:
      self.turn_on(MANUAL_HVAC_MODE)
    elif state == 'off' and self.hvac_mode:
      self.turn_off(MANUAL_HVAC_MODE)


  def set_ac_mode(self, state):
    if state == 'on' and not self.ac_mode:
      self.turn_on(AC_MODE_BOOLEAN)
    elif state == 'off' and self.ac_mode:
      self.turn_off(AC_MODE_BOOLEAN)


  def set_heat_mode(self, state):
    if state == 'on' and not self.heat_mode:
      self.turn_on(HEAT_MODE_BOOLEAN)
    elif state == 'off' and self.heat_mode:
      self.turn_off(HEAT_MODE_BOOLEAN)


  def _set_hvac_state(self, hvac_state):
    """ Set the themostat's operation mode [heat, off] - No AC currently """
    if self.hvac_preset_mode not in ['none', 'None']:
      self._logger.log(f'Setting HVAC state while the preset mode is not set to "none" (current mode: {self.hvac_preset_mode}, type: {type(self.hvac_preset_mode)}), turning off preset mode now.')
      # self._set_hvac_preset_mode('off')
      self._set_hvac_preset_mode('none')

    if hvac_state == self.hvac_state:
        return

    self._last_hvac_state = self.hvac_state

    self._logger.log('Setting HVAC operation mode to "{}"'.format(hvac_state))
    self.call_service(
        "climate/set_hvac_mode",
        entity_id=THERMOSTAT,
        hvac_mode=hvac_state,
    )
 

  def _set_hvac_preset_mode(self, preset_mode):
    """ Set the themostat's preset mode [none, eco] """
    if preset_mode == self.hvac_preset_mode:
        return

    self._last_hvac_preset_mode = self.hvac_preset_mode

    self._logger.log('Setting HVAC preset mode to "{}"'.format(preset_mode))
    self.call_service(
      "climate/set_preset_mode", 
      entity_id=THERMOSTAT, 
      preset_mode=preset_mode,
    )


  def set_temperature(self, temperature):
    """ Set the thermostat temperature """
    if temperature == self.target_temperature:
      return

    self._last_temperature = self.target_temperature

    self._logger.log('Setting HVAC temperature to "{}"'.format(temperature))
    self.call_service(
        "climate/set_temperature",
        entity_id=THERMOSTAT,
        temperature=str(temperature),
    )


  def set_fan_mode(self, fan_mode):
    """ Set HVAC fan mode [on, off] """
    if fan_mode not in ['on', 'off'] or fan_mode == self.hvac_fan_state:
      self._logger.log(f'Attemped to change HVAC fan mode but the current state ("{self.hvac_fan_state}") is the same as the requests state ("{fan_mode}").', 'DEBUG')
      return
    
    self._logger.log('Setting HVAC fan mode to "{}"'.format(fan_mode))
    self.call_service(
        "climate/set_fan_mode",
        entity_id=THERMOSTAT,
        fan_mode=str(fan_mode),
    )


  def set_hvac_heat(self, temperature=None):
    """ Turn heat on if not already on """
    if self.hvac_state != 'heat' or self.hvac_preset_mode != 'none':
      self._set_hvac_state('heat')

    if temperature is None: 
      temperature = DEFAULT_HEAT_TEMP
      
    self.set_temperature(temperature)


  def set_hvac_ac(self, temperature=None):
    """ Turn ac on if not already on """
    if self.hvac_state in ['off','eco','auto'] or self.hvac_preset_mode != 'none':
      self._set_hvac_state('cool')

    if temperature is None: 
      temperature = DEFAULT_AC_TEMP

    self.set_temperature(temperature)
      

  def set_hvac_eco(self):
    """ Turn eco mode on if not already on """
    if self.hvac_preset_mode not in ['eco', 'Away and Eco']:
      self._set_hvac_preset_mode('eco')


  def set_hvac_off(self):
    """ Turn hvac off if not already off """
    if self.hvac_state != 'off' or self.hvac_preset_mode != 'none':
      self._set_hvac_state('off')


  def terminate(self):
    pass


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing climate module: ')
    # self._outdoor_sensor_tests()
    self._indoor_sensor_tests()
    # self._thermostat_tests()


  def _thermostat_tests(self):
    self._logger.log('THERMOSTAT tests: ')
    self._logger.log(f'Manual HVAC mode: {self.manual_hvac_mode}')
    self._logger.log(f'AC mode: {self.ac_mode}')
    self._logger.log(f'Heat mode: {self.heat_mode}')
    self._logger.log(f'Current temperature: {self.entryway_temp}')
    self._logger.log(f'Target temperature: {self.target_temperature}')
    self._logger.log(f'Current HVAC state: {self.hvac_state}')
    self._logger.log(f'Current HVAC fan state: {self.hvac_fan_state}')
    self._logger.log(f'Current HVAC action: {self.hvac_action}')
    self._logger.log(f'Currenct HVAC preset state: {self.hvac_preset_mode}')
    self._logger.log(f'Last HVAC state: {self.last_hvac_state}')
    self._logger.log(f'Last HVAC preset state: {self.last_hvac_preset_mode}')
    self._logger.log(f'Last thermostat temperature: {self.last_thermostat_temperature}')


  def _indoor_sensor_tests(self):
    self._logger.log('INDOOR sensors:')
    self._logger.log(f'Entryway temperature: {self.entryway_temp}')
    self._logger.log(f'Study temperature: {self.study_temp}')
    self._logger.log(f'Study 1 temperature: {self.study_1_temp}')
    self._logger.log(f'Study 2 temperature: {self.study_2_temp}')
    self._logger.log(f'Master Bedroom temperature: {self.master_bedroom_temp}')
    self._logger.log(f'Master bathroom temperature: {self.master_bathroom_temp}')
    self._logger.log(f'Livng room temperature: {self.living_room_temp}')
    self._logger.log(f'Kitchen temperature: {self.kitchen_temp}')
    self._logger.log(f'Average indoor temperature: {self.average_indoor_temp}')

    self._logger.log(f'Entryway humidity: {self.entryway_humidity}')
    self._logger.log(f'Master bedroom humidity: {self.master_bathroom_humidity}')
    self._logger.log(f'Living room humidity: {self.living_room_humidity}')
    self._logger.log(f'Basement storage humidity: {self.basement_storage_humidity}')
    self._logger.log(f'Average humdity: {self.average_indoor_humidity}')    

    self._logger.log(f'Study light level: {self.study_light_level}')    
    self._logger.log(f'Master bathroom light level: {self.master_bathroom_light_level}')    
    self._logger.log(f'Master bedroom light level: {self.master_bedroom_light_level}')    
    self._logger.log(f'Living room light level: {self.living_room_light_level}')    
    self._logger.log(f'Kitchen light level: {self.kitchen_light_level}')    
    self._logger.log(f'Average indoor light level: {self.average_indoor_light_level}')    


  def _outdoor_sensor_tests(self):
    self._logger.log('OUTDOOR sensors: ')
    self._logger.log(f'PWS ready: {self.pws_ready}')
    self._logger.log(f'PWS online: {self._pws_online}')
    self._logger.log(f'PWS up to date: {self._pws_upto_date}')

    self._logger.log(f'Apparent temperature: {self.apparent_outdoor_temp}')
    self._logger.log(f'Current outdoor temperature: {self.current_outdoor_temp}')
    self._logger.log(f'Todays high temperature: {self.todays_high}')
    self._logger.log(f'Todays low temperature: {self.todays_low}')
    self._logger.log(f'Tomorrows high temperature: {self.tomorrows_high}')
    self._logger.log(f'Tomorrows low temperature: {self.tomorrows_low}')

    self._logger.log(f'Current heat index: {self.current_heat_index}')
    self._logger.log(f'Current dew point: {self.current_dew_point}')
    self._logger.log(f'Current UV: {self.current_uv}')
    self._logger.log(f'Current solar radiation: {self.current_solar_radiation}')
    self._logger.log(f'Current relative humidity: {self.current_humidity}')

    self._logger.log(f'Current wind chill temperature: {self.current_wind_chill}')
    self._logger.log(f'Current wind direction: {self.current_wind_direction}')
    self._logger.log(f'Current wind speed: {self.current_wind_speed}')
    self._logger.log(f'Current wind gust speed: {self.current_wind_gust_speed}')
    self._logger.log(f'Aver wind speed today: {self.average_wind_speed_today}')

    self._logger.log(f'Precipitation probability today: {self.precip_chance_today}')
    self._logger.log(f'Precipitation accumulation today: {self.precip_accumulation_today}')
    self._logger.log(f'Current precipitation rate: {self.current_precip_rate}')
    self._logger.log(f'Expected precipitation today: {self.expected_precip_today}')

    self._logger.log(f'Todays forecast: {self.day_forecast}')
    self._logger.log(f'Tonights forecast: {self.night_forecast}')


