
"""
Utility functions for voluptuous validation
"""

import voluptuous as vol
import datetime

def parse_star_time(value):
  try:
    res = int(value)
  except:
    try:
      time_parts = value.strip().split('*')
      res = int(time_parts[0]) * int(time_parts[1])
    except:
      raise vol.Invalid(f"Star time parse failed: {value}")
  return res


def ensure_time(candidate):
  """ Validate and parse a time string of either %H:%M:%S or %H:%M """
  timeformat = "%H:%M:%S"
  try:
      datetime.datetime.strptime(candidate, timeformat)
      return candidate
  except ValueError:
    try:
      time_str = candidate + ':00'
      datetime.datetime.strptime(time_str, timeformat)
      return time_str
    except ValueError:
      raise vol.Invalid(f'Error parsing time: {candidate}')
  except TypeError:
    # candidate is not a string
    raise vol.Invalid(f'Error parsing time: {candidate}')


def ensure_constraint_list(candidate):
  """Validate if a given object is a list of constraints. EX: light.test, ==, 'on'"""
  if candidate is None:
    return []

  to_test = candidate if isinstance(candidate, list) else [candidate]
  for constraint in to_test:
    values = [x.strip(' ') for x in constraint.split(',')]
    if len(values) < 3:
      raise vol.Invalid(f'Invalid contraint list: {candidate}')
    entity_id(values[0])
    if values[1] not in ["+", "-", ">", ">=", "<", "<=", "=", "==", "!="]:
      raise vol.Invalid(f'Invalid contraint list: {candidate}')
     
  return candidate


def ensure_list(candidate):
  """Validate if a given object is a list."""
  if candidate is None:
    return []
  return candidate if isinstance(candidate, list) else [candidate]

def entity_id(value):
  """Validate if a given object is an entity id."""
  if not value or value is None:
    # Nothin provided return nothing
    return None
  value = str(value).lower()
  if "." in value:
    return value
  raise vol.Invalid(f"Invalid Entity-ID: {value}")

def entity_id_list(value):
  """Validate if a given object is a list of entity ids."""
  if isinstance(value, str):
    value = [value]
  for item in value:
    if "." not in item:
      raise vol.Invalid(f"Invalid Entity-List: {value}")
  return value


def log_level(value):
  """Validate if a log level."""
  if not value: 
    return None

  if not isinstance(value, str):
    raise vol.Invalid(f"Log level must be a string: {value}")

  if value not in ['NOTSET','DEBUG','INFO','WARNING','ERROR','CRITICAL']:
    raise vol.Invalid(f"Invalid Entity-List: {value}")
  return value


def try_parse_str(candidate):
  """
  Convert the given candidate to int. If it fails None is returned.
  Example:
      >>> type(try_parse_int(1))  # int will still be int
      <class 'int'>
      >>> type(try_parse_int("15"))
      <class 'int'>
      >>> print(try_parse_int("a"))
      None
  Args:
      candidate: The candidate to convert.
  Returns:
      Returns the converted candidate if convertible; otherwise None.
  """
  if not candidate or candidate is None:
    # Nothin provided return nothing
    return None
  try:
    return str(candidate)
  except (ValueError, TypeError):
    raise vol.Invalid(f'Invalid string: {candidate}')
    return None


def try_parse_int(candidate):
  """
  Convert the given candidate to int. If it fails None is returned.
  Example:
      >>> type(try_parse_int(1))  # int will still be int
      <class 'int'>
      >>> type(try_parse_int("15"))
      <class 'int'>
      >>> print(try_parse_int("a"))
      None
  Args:
      candidate: The candidate to convert.
  Returns:
      Returns the converted candidate if convertible; otherwise None.
  """
  if candidate is None:
    # Nothin provided return nothing
    return None
  try:
    return int(candidate)
  except (ValueError, TypeError):
    raise vol.Invalid(f'Invalid integer: {candidate}')
    return None


def try_parse_float(candidate):
  """
  Convert the given candidate to int. If it fails None is returned.
  Example:
      >>> type(try_parse_int(1))  # int will still be int
      <class 'int'>
      >>> type(try_parse_int("15"))
      <class 'int'>
      >>> print(try_parse_int("a"))
      None
  Args:
      candidate: The candidate to convert.
  Returns:
      Returns the converted candidate if convertible; otherwise None.
  """
  if candidate is None:
    # Nothin provided return nothing
    return None
  try:
    return float(candidate)
  except (ValueError, TypeError):
    raise vol.Invalid(f'Invalid float: {candidate}')
    return None


def parse_duration_literal(literal):
  """
  Converts duration literals as '1m', '1h', and so on to an actual duration in seconds.
  Supported are 's' (seconds), 'm' (minutes), 'h' (hours), 'd' (days) and 'w' (weeks).
  Examples:
      >>> parse_duration_literal(60)  # Int will be interpreted as seconds
      60
      >>> parse_duration_literal('10')  # Any int convertible will be interpreted as seconds
      10
      >>> parse_duration_literal('20s')  # Seconds literal
      20
      >>> parse_duration_literal('2m')  # Minutes literal
      120
      >>> parse_duration_literal('1h')  # Hours literal
      3600
      >>> parse_duration_literal('1d')  # Days literal
      86400
      >>> parse_duration_literal('1w')  # Weeks literal
      604800
      >>> parse_duration_literal('invalid')  # Invalid will raise an error
      Traceback (most recent call last):
      ...
      TypeError: Interval 'invalid' is not a valid literal
  Args:
      literal: Literal to parse.
  Returns:
      Returns the converted literal's duration in seconds. If conversion is not possible
      an exception is raised.
  """
  try:
    # if successful we got seconds
    return int(literal)
  except: 
    # Try to get star time (ex: 5*60)
    try:
      time_parts = literal.strip().split('*')
      res = int(time_parts[0]) * int(time_parts[1])
    except:
      # raise vol.Invalid(f"Star time parse failed: {literal}")
      pass 

    # We have to check for s, m, h, d, w suffix
    seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    # Remove all non-alphanumeric letters
    s = re.sub('[^0-9a-zA-Z]+', '', str(literal))
    value_str, unit = s[:-1], s[-1].lower()
    value = try_parse_int(value_str)
    if value is None or unit not in seconds_per_unit:
      raise TypeError("Interval '{}' is not a valid literal".format(literal))
    return value * seconds_per_unit[unit]

