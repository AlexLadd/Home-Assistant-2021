"""
Appdaemon helper functions
  -> Imported as a global_module to most apps
  -> Updating this will (should) restart all dependent apps
"""

import datetime
import os

from const import (DARK_MODE_BOOLEAN,
                  WINTER_MONTH_START, WINTER_MONTH_END)


#       **********  General Functions **********

def one_space(string):
  """ Strip out all whitespace except for one """
  return re.sub(' +', ' ', string.strip())

def last_changed(hass, entity):
  """ Return the when the entity was last changed in seconds -> int """
  lc = hass.get_state(entity, attribute='last_changed')
  lc_tz_correct = hass.convert_utc(lc).replace(tzinfo=None)
  time_delta = datetime.datetime.utcnow().timestamp() - lc_tz_correct.timestamp()
  return time_delta


def valid_input(old, new=None):
  """ Return if the callback input is valid for use """
  INVALID = ['unavailable', 'unknown', 'Unavailable', 'Unknown']
  if new is None:
    return old not in INVALID
  if new != old and old not in INVALID and new not in INVALID:
    return True 
  return False 


def json_pretty_format(data, sort_keys=False):
  """ Return a 'pretty' formatted json string """
  import json
  return json.dumps(data, indent=4, sort_keys=sort_keys)

def json_pretty_print(data, logger, sort_keys=False):
  """ Log 'pretty' formatted json string to specified logger """
  import json 
  logger.log((json.dumps(data, indent=4, sort_keys=sort_keys)))


#       **********  Time Related Functions **********

seasons = [('winter', (datetime.date(2000,  1,  1),  datetime.date(2000,  3, 20))),
           ('spring', (datetime.date(2000,  3, 21),  datetime.date(2000,  6, 20))),
           ('summer', (datetime.date(2000,  6, 21),  datetime.date(2000,  9, 22))),
           ('autumn', (datetime.date(2000,  9, 23),  datetime.date(2000, 12, 20))),
           ('winter', (datetime.date(2000, 12, 21),  datetime.date(2000, 12, 31)))]
def get_season(now=None):
  """ Return current season as a string """
  if now is None:
    now = datetime.datetime.now().date()
  if isinstance(now, datetime.datetime):
      now = now.date()
  now = now.replace(year=2000) # dummy leap year to allow input X-02-29 (leap day)
  return next(season for season, (start, end) in seasons
              if start <= now <= end)

def date_is_between(start, end):
  if isinstance(start, datetime.datetime):
    start = start.date()
  if isinstance(end, datetime.datetime):
    end = end.date()
    
  now = datetime.datetime.now().date()
  if start <= now <= end:
    return True
  return False

def month_is_between(start, end, inclusive=True):
  """ Current month is between the two given months """
  s = start if isinstance(start, int) else datetime.datetime.strptime(start,'%B').month 
  e = end if isinstance(end, int) else datetime.datetime.strptime(end,'%B').month
  current_month = datetime.datetime.now().month

  if inclusive:
    return (current_month >= s and current_month <= e) or (s >= e and (current_month >= s or current_month <= e))
  return (current_month > s and current_month < e) or (s > e and (current_month > s or current_month < e))


def is_winter_months():
  """ Return true if the current month is a typical winter month """
  return month_is_between(WINTER_MONTH_START, WINTER_MONTH_END, inclusive=True)


def is_weekday():
  # 0 - Monday, 6 - Sunday
  day = datetime.datetime.now().weekday()
  return bool(day != 5 and day != 6)



#       **********  OS Path Related Functions **********

HASS_BASE_PATH = '/hass'
HASS_SERVICE_CALL_PATH = '/config'
AD_BASE_PATH = '/conf'
NOTIFY_BASE_PATH = 'local'

def ha_path(path, service_call_path=False):
  """ service_call_path is the path used in a call_service such as camera.snapshot """
  base = HASS_SERVICE_CALL_PATH if service_call_path else HASS_BASE_PATH
  alt = HASS_BASE_PATH if service_call_path else HASS_SERVICE_CALL_PATH
  if path:
    if path.startswith(base):
      return path
    elif path.startswith(alt):
      path = path[len(alt):]
  path = clean_path(path, True)
  return os.path.join(base, path)

def ad_path(path):
  if path:
    if path.startswith(AD_BASE_PATH):
      return path
  path = clean_path(path, True)
  return os.path.join(AD_BASE_PATH, path)

def html5_notify_path(path):
  """ Path used for html5_notify images - Starts with /local (which is the www folder in HA base folder) """
  if path:
    if path.startswith(NOTIFY_BASE_PATH):
      return path
  path = clean_path(path, True)
  return os.path.join(NOTIFY_BASE_PATH, path)


# Service call path is the same as HA path in every regard except that it starts with /config instead of /hass
# Notity image path starts with /local & the root is /hass/www 

def ad_to_ha_path(path, service_call_path=False):
  path = clean_path(path)
  ha_base = HASS_SERVICE_CALL_PATH if service_call_path else HASS_BASE_PATH
  return path.replace(AD_BASE_PATH, ha_base)

def ha_to_ad_path(path, service_call_path=False):
  path = clean_path(path)
  if path.startswith(HASS_SERVICE_CALL_PATH):
    return path.replace(HASS_SERVICE_CALL_PATH, AD_BASE_PATH)
  elif path.startswith(HASS_BASE_PATH):
    return path.replace(HASS_BASE_PATH, AD_BASE_PATH)
  return path


def clean_path(path, remove_lead=False):
  """ Strip duplicate slashes and trailing slash and optionally leading slash """
  if remove_lead:
    path = path.lstrip('/')
  res = []
  first_slash = True
  for c in path:
    if c == '/' and first_slash:
      first_slash = False
      res.append(c)
    elif c != '/':
      first_slash = True
      res.append(c)
  return ''.join(res).rstrip('/')

