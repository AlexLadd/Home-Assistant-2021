
from base_app import BaseApp
import datetime
import random


# TODO: 
#   - Create a group functions that return all entities in a specified state?
#   - Add date check to epson ink notify
 
QUOTES_PATH = '/conf/apps/messages/quotes.txt'

AFFIRMATIVE_RESPONSES = [
    "10-4.",
    "Affirmative.",
    "As you decree, so shall it be.",
    "As you wish.",
    "By your command.",
    "Consider it done.",
    "Done.",
    "I can do that.",
    "If you insist.",
    "It shall be done.",
    "Leave it to me.",
    "Making things happen.",
    "No problem.",
    "No worries.",
    "OK.",
    "Roger that.",
    "So say we all.",
    "Sure.",
    "Will do.",
    "You got it.",
]

WIND_SPEED_WARNING_THRESHOLD = 40


class Messages(BaseApp):

  def setup(self):
    # self.listen_state(self.test,'input_boolean.ad_testing_1')

    self.climate = self.get_app('climate')

    self.epson_ink_low_notified = False
    self.quotes = []
    self.load_quotes()


  def load_quotes(self):
    self.quotes = []
    with open(QUOTES_PATH, "r", encoding='utf-8') as f:
      for line in f:
        self.quotes.append(line.strip('\n'))


  def inspirational_quote(self):
    return random.choice(self.quotes)


  def greeting(self):
    hour = datetime.datetime.now().hour
    if 3 <= hour < 12:
      return 'Good morning. '
    elif 12 <= hour < 17:
      return 'Good afternoon. '
    elif 17 <= hour < 20:
      return 'Good evening. '
    else:
      return 'Good night. '


  def random_affirmative_response(replace_hyphens=True):
    """ Return a randomly chosen affirmative response """
    choice = random.choice(AFFIRMATIVE_RESPONSES)

    if replace_hyphens:
        return choice.replace("-", " ")
    return choice


  def date_check(self):
    return datetime.datetime.now().strftime("%A %B %-d") # %Y for year


  def water_cactus(self):
    day = datetime.datetime.now().day
    if day % 14 == 0:
      return 'The cactus need water today.'
    return ''

  def household_boolean_check(self):
    msg = ''
    are_on = []
    if self.get_state(self.const.EMERGENCY_MODE_BOOLEAN) == 'on':
      are_on.append('emergency mode')
    elif self.get_state(self.const.VACATION_MODE_BOOLEAN) == 'on':
      are_on.append('vacation mode')
    elif self.get_state(self.const.PET_MODE_BOOLEAN) == 'on':
      are_on.append('pet mode')
    elif self.get_state(self.const.MANUAL_HVAC_MODE) == 'on':
      are_on.append('manual hvac mode')

    if are_on:
      msg = self.utils.list_to_pretty_print(are_on, 'on')
    
    if self.get_state(self.const.SPEECH_OVERRIDE_BOOLEAN) == 'off':
      msg += ' Speech mode is off so no messages will be heard except for this one. '

    return self.utils.one_space(msg)


  def rockwood_garbage_schedule(self):
    return '' 

    # start_time = self.get_state('calendar.rockwood_garbage_schedule',attribute='start_time')
    # start = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S').date()
    # now = datetime.datetime.now().date()
    # day = now.weekday()

    # items = self.get_state('calendar.rockwood_garbage_schedule', attribute='message')

    # msg = ''
    # if start - now == datetime.timedelta(days=1):
    #   if items == 'Hwms closed':
    #     msg = 'There is no waste pickup tomorrow.'
    #   else:
    #     msg = 'The garbage items tomorrow are {}.'.format(items)
    # elif start - now == datetime.timedelta(days=0):
    #   if items == 'Hwms closed':
    #     msg = 'There is no waste pickup today.'
    #   else:
    #     msg = 'The garbage items today are {}.'.format(items)

    # if (day != 0 or day != 1) and msg:
    #   # Garbage days should only be Mondays or Tuesday on holidays (Xmas might be exception)
    #   self._logger.log(f'Calender has an entry for the garbage pickup when the day is not Monday or Tuesday: {msg}')
    #   return ''
    # return msg


  def wind_check(self):
    avg_wind_today = self.climate.average_wind_speed_today
    if not self.climate.pws_ready:
      self._logger.log(f'PWS not ready, wind readings not available.', 'WARNING')

    if avg_wind_today and int(avg_wind_today) > WIND_SPEED_WARNING_THRESHOLD:
      return f'There will be wind speeds of up to {avg_wind_today} kilometers per hour today.'
    else:
      return ''


  def weather_check(self):
    """ Environment Canada weather check """
    if self.now_is_between('15:00:00', '04:00:00'):
      return self.climate.night_forecast
    else:
      return self.climate.day_forecast


  def climate_check(self):
    # dw_open = self.get_state('group.door_window_sensors_master') == 'on'
    dw_open = self.entry_point_check() != "All doors and windows are closed."
    master_open = 'master bedroom' in self.entry_point_check()
    msg = ''

    if not self.climate.manual_hvac_mode:
      if not self.climate.pws_ready:
        msg += ' Home assistant is not reading the outdoor weather station temperatures correctly.'
      todays_low = self.climate.todays_low
      if todays_low > 10:
        if not self.climate.ac_mode and not master_open:
          msg += f' The overnight low is {todays_low} degrees and the air conditioner mode is off and no master bedroom windows are open.'
        elif self.climate.ac_mode and dw_open:
            msg += ' The AC mode is on and {self.messages.entry_point_check().lower()}.'
      elif todays_low < -11:
        if not self.climate.heat_mode:
          msg += f' The heat mode is off and the over night low is {todays_low} degrees. Something is wrong!'
        elif dw_open:
          msg += f' The heat mode is on and the over night low is {todays_low} degrees and {self.entry_point_check().lower()}.'
        if self.climate.target_temperature < 20:
          msg += f' The over night low is {todays_low} degrees and the thermostat temerature is {self.climate.target_temperature}.'
      elif todays_low < 1:
        if not self.climate.heat_mode:
          msg += f' The heat mode is off and the over night low is {todays_low} degrees. You may want to turn on the heat.'
        elif self.climate.heat_mode and dw_open:
          msg = f' The heat mode is on and the over night low is {todays_low} degrees and {self.entry_point_check().lower()}.'
        elif dw_open:
          msg += f' The windows or doors are open and the over night low is {todays_low} degrees.'
    else:
      msg += ' The HVAC is in manual control mode.'
      if self.climate.pws_ready:
        if self.climate.todays_low <= 0 and dw_open:
          msg += f' The overnight low is {self.climate.todays_low} and {self.entry_point_check().lower()}.'
        elif self.climate.todays_low >= 17 and not master_open:
          msg += f' The overnight low is {self.climate.todays_low} and the master windows are closed.'


    return self.utils.one_space(msg)


  def inside_weather(self):
    avg_temp = self.climate.average_indoor_temp
    humidity = self.cliamte.average_indoor_humidity
    return f'The average inside temperature is {avg_temp} degrees with a humidity of {humidity} percent.'


  def outside_weather(self):
    temp = self.climate.current_outdoor_temp
    low = self.climate.todays_low
    high = self.climate.todays_high
    rain = self.climate.expected_precip_today
    # ds_precip_type = self.get_state('sensor.dark_sky_precip_0d')

    result = f'The current temperature is {temp} degrees outside with a high of {high} and low of {low} degrees.'

    if ((self.now_is_between('03:00:00', '16:00:00') and -2 < high < 2) and -2 < temp < 2) \
        or (self.now_is_between('16:00:00', '03:00:00') and -2 < low < 2) and -2 < temp < 2:
      result += f'There is a {rain} percent of precipitation and the temperatures are around freezing.'
    else:
      result += f' There is a {rain} percent chance of precipitation today.'

    return self.utils.one_space(result)

  
  def entry_point_check(self, door_check=True, window_check=True):
    """ Returns a human readable message with the open windows and doors as a string """
    open = []
 
    if window_check:
      group = self.get_state('group.window_sensors_master', attribute="all")
      for entity in group['attributes']['entity_id']:
        entity_info = self.get_state(entity, attribute="all")
        if entity_info['state'] == 'on':
          name = entity_info['attributes']['friendly_name'].replace(' Sensor','').lower()
          open.append(name)

    if door_check:
      group = self.get_state('group.door_sensors_master', attribute="all")
      for entity in group['attributes']['entity_id']:
        entity_info = self.get_state(entity, attribute="all")
        if entity_info['state'] == 'on':
          name = entity_info['attributes']['friendly_name'].replace(' Sensor','').lower()
          open.append(name)

    if len(open) == 0:
      result = "All doors and windows are closed."
    else:
      result = self.utils.list_to_pretty_print(open, 'open')

    return result


  def light_check(self):
    open = []
 
    group = self.get_state('group.lights_master', attribute="all")
    for entity in group['attributes']['entity_id']:
      entity_info = self.get_state(entity, attribute="all")
      if entity_info['state'] == 'on':
        open.append(entity_info['attributes']['friendly_name'].lower())

    if len(open) == 0:
      result = "All the lights are off"
    else:
      result = self.utils.list_to_pretty_print(open, 'on')

    return result


  def uv_check(self):
    uv = self.climate.current_uv
    if uv is None:
      return ''

    if 6 <= uv < 8:
      return 'The uv index is {}, this is high.'.format(int(uv))
    elif 8 <= uv < 11:
      return 'The uv idex is {}, this is very high.'.format(int(uv))
    elif uv >= 11:
      return 'The uv index is {}, this is extremely high.'.format(int(uv))
    return ''


  def holiday_check(self):
    holiday = self.get_state(self.const.HOLIDAY_SENSOR)
    if holiday != 'No Holiday':
      return f'Today is {holiday}.'
    return ''


  def season_check(self):
    season = self.get_state(self.const.SEASON_SENSOR)
    if season != 'No Season':
      return f'Today is {season}.'
    return ''


  def epson_ink_check(self):
    THRESHOLD_EPSON_INK_LEVEL = 25

    if self.epson_ink_low_notified:
      return ''
    
    low = []

    group = self.get_state('group.espon_printer_sensors_master', attribute="all")
    for entity in group['attributes']['entity_id']:
      entity_info = self.get_state(entity, attribute="all")
      try:
        ink_level = int(entity_info['state'])
      except:
        # Printer could be off or not a valid ink sensor
        self._logger.log(f'Cannot read epson sensor: {self.friendly_name(entity)}, state: {entity_info}', level='DEBUG')
        continue
      if 0 < int(entity_info['state']) < THRESHOLD_EPSON_INK_LEVEL:
        low.append(entity_info['attributes']['friendly_name'].replace(' Sensor','').lower())

    if len(low) == 0:
      # result = "The epson printer ink levels are okay."
      return ''
    else:
      result = self.utils.list_to_pretty_print(low, 'low')

    self.epson_ink_low_notified = True
    return self.utils.one_space(result.replace(' ink level',''))


  # Not using greeting since it is in TTS notify
  def build_message(self, date_check=False, holiday_check=False, season_check=False,
    wind_check=False, inside_weather=False, outside_weather=False, uv_check=False,
    window_check=False, door_check=False, light_check=False, 
    epson_ink_check=False, inspirational_quote=False, water_cactus=False):
      result = ''
      if date_check:
        result += self.date_check() + ' '
      if holiday_check:
        result += self.holiday_check() + ' '
      if season_check:
        result += self.season_check() + ' '

      if water_cactus:
        result += self.water_cactus() + ' '

      if inside_weather:
        result += self.inside_weather() + ' '
      if wind_check:
        result += self.wind_check() + ' '
      if outside_weather:
        result += self.outside_weather() + ' '
      if uv_check:
        result += self.uv_check() + ' '

      if window_check and door_check:
        result += self.entry_point_check() + ' '
      elif window_check:
        result += self.entry_point_check(door_check=False)
      elif door_check:
        result += self.entry_point_check(window_check=False)

      if light_check:
        result += self.light_check() + ' '
      if epson_ink_check:
        result += self.epson_ink_check() + ' '
      if inspirational_quote:
        result += self.inspirational_quote() + ' '

      return self.utils.one_space(result)


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing Messages Module: ')
    self._logger.log(f'Light check: {self.epson_ink_check()}')
