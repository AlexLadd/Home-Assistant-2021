
"""
Utility app for controlling and updating the seasons/holidays sensor and providing seasonal/holiday colours and scenes for various rooms
NOTE: Season/holidays will first look for static than dynamic using the first match found.
The first match found will always be used!
"""

from base_app import BaseApp
import datetime
import yaml
import itertools
import random
import os

from file_watchdog import FileWatchdog


# TODO:
#   - Create a check if requested scene is different/same as the one that exists (particularily brightness)
#   - What is the difference between holiday & season sensor? (holiday is typically only a 1 day event & season is multiple days)

# Default birthday colours (shuffle these when creating a scene)
BIRTHDAY_COLOURS = [[199,0,247], [255,0,0], [0,0,255], [0,255,0]]

HOLIDAY_DIRECTORY = '/conf/apps/seasons/'
HOLIDAY_FILE = 'season_holiday_data.yml'
HOLIDAY_DATA_PATH = HOLIDAY_DIRECTORY + HOLIDAY_FILE

DEFAULT_NO_SEASON = 'No Season'
DEFAULT_NO_HOLIDAY = 'No Holiday'

NOTIFY_TARGET = ['alex']
NOTIFY_TITLE = 'Seasons and Holidays'


class Seasons(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_4')

    self.notifier = self.get_app('notifier')
    self.scenes = self.get_app('scenes')

    self._holiday_data = {}
    self._load_data()
    self._update_sensors()

    # Add a file listener for the holiday/season config file
    self.holiday_file_watchdog = FileWatchdog(self, HOLIDAY_DIRECTORY, HOLIDAY_FILE, debug_level='NOTSET')

    self.listen_event(lambda *_: self._update_sensors(), 'plugin_started')
    self.run_daily(lambda *_: self._update_sensors(True), datetime.time(00, 1, 0))


  @property
  def season(self):
    return self.get_state(self.const.SEASON_SENSOR)

  @season.setter
  def season(self, value):
    if value != self.season:
      self._logger.log('Updated {} to {}.'.format(self.const.SEASON_SENSOR, value))
      self.set_state(self.const.SEASON_SENSOR, state=value)

  @property
  def is_season(self):
    return bool(self.season not in ['No Season', 'unknown', 'unavailable'])

  @property
  def holiday(self):
    return self.get_state('sensor.holiday')

  @holiday.setter
  def holiday(self, value):
    if value != self.holiday:
      self._logger.log('Updated {} to {}.'.format(self.const.HOLIDAY_SENSOR, value))
      self.set_state(self.const.HOLIDAY_SENSOR, state=value)

  @property
  def is_holiday(self):
    return bool(self.holiday not in ['No Holiday', 'unknown', 'unavailable'])


  def _load_data(self):
    with open(self.utils.ad_path(HOLIDAY_DATA_PATH)) as f:
      self._holiday_data = yaml.safe_load(f)


  def on_watchdog_file_update(self, file_name, event_type):
    """ The holiday/season file was updated - This is called from the watchdog file listener """
    self._logger.log('Holiday/season data file ("{}") was "{}", reloading now.'.format(file_name, event_type), level='DEBUG')
    self._load_data()
    self._update_sensors()


  def _update_sensors(self, log=False):
    """ Update holiday & season sensors """
    if log: self._logger.log('Updating holiday & season sensors.')
    self._update_holiday_season_sensors()


  def _update_holiday_season_sensors(self):
    """ Date format month/day/year or month/day for static 
    
    Duplicates will produce the first match (Both for holiday & season)
    """
    no_holiday = True
    no_season = True
    today = self.datetime().date()

    # Static Holidays (This includes birthdays)
    for holiday, dates in self._holiday_data['static'].items():
      # Check for Holiday update
      if 'date' in dates:
        d = datetime.datetime.strptime(dates['date'], '%m/%d').date().replace(year=self.datetime().year)
        if d == today:
          if not no_holiday:
            msg = 'Duplicate holiday today: {}.'.format(holiday)
            self._logger.log(msg)
            self.notifier.telegram_notify(msg, 'logging', NOTIFY_TITLE)
          else:
            no_holiday = False
            self.holiday = holiday

      # Check for season update
      if 'start' in dates and 'end' in dates:
        start = datetime.datetime.strptime(dates['start'], '%m/%d').date().replace(year=self.datetime().year)
        end = datetime.datetime.strptime(dates['end'], '%m/%d').date().replace(year=self.datetime().year)
        if start > end:
          # Assumes date range spans the new year and not an error
          end = end.replace(year=self.datetime().year+1)
        if self.utils.date_is_between(start, end):
          if not no_season:
            msg = 'Duplicate season today: {}.'.format(holiday)
            self._logger.log(msg)
            self.notifier.telegram_notify(msg, 'logging', NOTIFY_TITLE)
          else:
            no_season = False
            self.season = holiday

    # Dynamic Holidays (This will not update if static holiday already found)
    for holiday, dates in self._holiday_data['dynamic'].items():
      # Check for holiday update
      if 'dates' in dates:
        for date in dates['dates']:
          d = datetime.datetime.strptime(date, '%m/%d/%Y').date()
          if d == today:
            if not no_holiday:
              msg = 'Duplicate holiday today: {}.'.format(holiday)
              self._logger.log(msg)
              self.notifier.telegram_notify(msg, 'logging', NOTIFY_TITLE)
            else:
              no_holiday = False
              self.holiday = holiday

        # Check for season update
        if 'start' in dates and 'end' in dates:
          start = datetime.datetime.strptime(dates['start'], '%m/%d').date().replace(year=self.datetime().year)
          end = datetime.datetime.strptime(dates['end'], '%m/%d').date().replace(year=self.datetime().year)
          if start > end:
            # Assumes date range spans the new year and not an error
            end = end.replace(year=self.datetime().year+1)
          if self.utils.date_is_between(start, end):
            if not no_season:
              msg = 'Duplicate season today: {}.'.format(holiday)
              self._logger.log(msg)
              self.notifier.telegram_notify(msg, 'logging', NOTIFY_TITLE)
            else:
              no_season = False
              self.season = holiday

    if no_holiday:
      self.holiday = DEFAULT_NO_HOLIDAY
    if no_season:
      self.season = DEFAULT_NO_SEASON


  def get_season_colours(self, season=None):
    """ Get the colours associated with a given season/holiday
    
    This will return static holiday over dynamic if both exist
    """
    if season is None:
      season = self.holiday

    if 'birthday' in season.lower():
      random.shuffle(BIRTHDAY_COLOURS)
      return BIRTHDAY_COLOURS

    if season.title() in self._holiday_data['static']:
      if 'colours' in self._holiday_data['static'][season]:
        return self._holiday_data['static'][season]['colours']
    elif season.title() in self._holiday_data['dynamic']:
      if 'colours' in self._holiday_data['dynamic'][season]:
        return self._holiday_data['dynamic'][season]['colours']

    msg = 'The season does not exists for {} or no colours are defined. Please add it to the config if desired.'.format(season)
    self._logger.log(msg, 'WARNING')
    return []


  def get_holiday_scene(self, room, lights, brightness=100, holiday=None, transition=1, overwrite=False):
    """ Returns the name of the holiday scene. If no holiday is provided the current holiday will be checked.
    
    A new scene is created if one does not exist
    """
    if holiday is None:
      if not self.is_holiday:
        return None
      holiday = self.holiday
    return self._get_scene(room, holiday, lights, brightness, transition, overwrite)


  def get_seasonal_scene(self, room, lights, brightness=100, season=None, transition=1, overwrite=False):
    """ Returns the name of the seasonal scene.  If no season is provided the current holiday will be checked.
    A new scene is created if one does not exist

    param room: Name of room used to create scene name
    param lights: List of light use for the scene
    """
    if season is None: 
      if not self.is_season:
        return None
      season = self.season
    return self._get_scene(room, season, lights, brightness, transition, overwrite)


  def try_get_scene(self, season, room, lights, brightness=100, transition=1, overwrite=False):
    """ Return holiday/seasonal scene if it is currently a holiday and successfull 
    Convenience function so both holiday & season can use the same function
    """
    if season is None:
      return None
    return self._get_scene(room, season, lights, brightness, transition, overwrite)


  def _get_scene(self, room, season, lights, brightness, transition, overwrite=False):
    """ Get or create a holiday/seasonal scene based on the room and season 
    
    param season: Can be a season or holiday name
    """
    if 'birthday' in season.lower():
      scene_name = 'birthday' + '_' + room.lower().strip().replace(' ', '_')
    else:
      scene_name = season.lower().strip().replace(' ', '_') + '_' + room.lower().strip().replace(' ', '_')
    season_colours = self.get_season_colours(season)
    if not season_colours:
      return None

    # self._logger.log(f'Getting scene for {room} using {lights} lights and {season_colours} colours: {scene_name}.', level='DEBUG')
    return self.scenes.create_scene(scene_name, lights, brightness, season_colours, transition, overwrite)


  def terminate(self):
    # Stop the watchdog thread
    self.holiday_file_watchdog.terminate()

  
  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing Season Module: ')
    self._logger.log(self.holiday)
    self._logger.log(self.is_holiday)

    c = self.get_season_colours('Halloween')
    self._logger.log(f'Season colour: {c}')

