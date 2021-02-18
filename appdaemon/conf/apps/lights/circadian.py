
#############################    CIRCADIAN LIGHTING    #####################################


"""
Circadian Lighting Component for Home-Assistant.
This component calculates color temperature and brightness to synchronize
your color changing lights with perceived color temperature of the sky throughout
the day. This gives your environment a more natural feel, with cooler whites during
the midday and warmer tints near twilight and dawn.
In addition, the component sets your lights to a nice warm white at 1% in "Sleep" mode,
which is far brighter than starlight but won't reset your circadian rhythm or break down
too much rhodopsin in your eyes.
Human circadian rhythms are heavily influenced by ambient light levels and
hues. Hormone production, brainwave activity, mood and wakefulness are
just some of the cognitive functions tied to cyclical natural light.
http://en.wikipedia.org/wiki/Zeitgeber
Here's some further reading:
http://www.cambridgeincolour.com/tutorials/sunrise-sunset-calculator.htm
http://en.wikipedia.org/wiki/Color_temperature
Technical notes: I had to make a lot of assumptions when writing this app
    *   There are no considerations for weather or altitude, but does use your
        hub's location to calculate the sun position.
    *   The component doesn't calculate a true "Blue Hour" -- it just sets the
        lights to 2700K (warm white) until your hub goes into Night mode
"""


import datetime as dt
import math

COMPONENT_NAME = 'Circadian Lighting'

DEFAULT_MIN_CT = 2000
DEFAULT_MAX_CT = 6500
DEFAULT_MIN_BRIGHTNESS = 25
DEFAULT_MAX_BRIGHTNESS = 100

SUN_EVENT_SUNRISE = 'sunrise'
SUN_EVENT_SUNSET = 'sunset'


# These methods are from: https://github.com/home-assistant/home-assistant/blob/761d7f21e90026d4a38fb20ee125ae2594ad5a5b/homeassistant/util/color.py

def _bound(color_component, minimum=0, maximum=255):
  """
  Bound the given color component value between the given min and max values.
  The minimum and maximum values will be included in the valid output.
  i.e. Given a color_component of 0 and a minimum of 10, the returned value
  will be 10.
  """
  color_component_out = max(color_component, minimum)
  return min(color_component_out, maximum)


def _get_red(temperature: float) -> float:
  """Get the red component of the temperature in RGB space."""
  if temperature <= 66:
      return 255
  tmp_red = 329.698727446 * math.pow(temperature - 60, -0.1332047592)
  return _bound(tmp_red)


def _get_green(temperature: float) -> float:
  """Get the green component of the given color temp in RGB space."""
  if temperature <= 66:
      green = 99.4708025861 * math.log(temperature) - 161.1195681661
  else:
      green = 288.1221695283 * math.pow(temperature - 60, -0.0755148492)
  return _bound(green)


def _get_blue(temperature: float) -> float:
  """Get the blue component of the given color temperature in RGB space."""
  if temperature >= 66:
      return 255
  if temperature <= 19:
      return 0
  blue = 138.5177312231 * math.log(temperature - 10) - 305.0447927307
  return _bound(blue)


def _color_temperature_to_rgb(color_temperature_kelvin):
  """
  Return an RGB color from a color temperature in Kelvin.
  This is a rough approximation based on the formula provided by T. Helland
  http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
  """
  # range check
  if color_temperature_kelvin < 1000:
      color_temperature_kelvin = 1000
  elif color_temperature_kelvin > 40000:
      color_temperature_kelvin = 40000

  tmp_internal = color_temperature_kelvin / 100.0
  red = _get_red(tmp_internal)
  green = _get_green(tmp_internal)
  blue = _get_blue(tmp_internal)

  return red, green, blue


def _color_RGB_to_hsv(iR, iG, iB):
  """Convert an rgb color to its hsv representation.
  Hue is scaled 0-360
  Sat is scaled 0-100
  Val is scaled 0-100
  """
  fHSV = colorsys.rgb_to_hsv(iR / 255.0, iG / 255.0, iB / 255.0)
  return round(fHSV[0] * 360, 3), round(fHSV[1] * 100, 3), round(fHSV[2] * 100, 3)


def _get_closest_point_to_point(xy_tuple, Gamut):
  """
  Get the closest matching color within the gamut of the light.
  Should only be used if the supplied color is outside of the color gamut.
  """
  xy_point = XYPoint(xy_tuple[0], xy_tuple[1])

  # find the closest point on each line in the CIE 1931 'triangle'.
  pAB = get_closest_point_to_line(Gamut.red, Gamut.green, xy_point)
  pAC = get_closest_point_to_line(Gamut.blue, Gamut.red, xy_point)
  pBC = get_closest_point_to_line(Gamut.green, Gamut.blue, xy_point)

  # Get the distances per point and see which point is closer to our Point.
  dAB = get_distance_between_two_points(xy_point, pAB)
  dAC = get_distance_between_two_points(xy_point, pAC)
  dBC = get_distance_between_two_points(xy_point, pBC)

  lowest = dAB
  closest_point = pAB

  if dAC < lowest:
      lowest = dAC
      closest_point = pAC

  if dBC < lowest:
      lowest = dBC
      closest_point = pBC

  # Change the xy value to a value which is within the reach of the lamp.
  cx = closest_point.x
  cy = closest_point.y

  return (cx, cy)


def _check_point_in_lamps_reach( p, Gamut):
  """Check if the provided XYPoint can be recreated by a Hue lamp."""
  v1 = XYPoint(Gamut.green.x - Gamut.red.x, Gamut.green.y - Gamut.red.y)
  v2 = XYPoint(Gamut.blue.x - Gamut.red.x, Gamut.blue.y - Gamut.red.y)

  q = XYPoint(p[0] - Gamut.red.x, p[1] - Gamut.red.y)
  s = cross_product(q, v2) / cross_product(v1, v2)
  t = cross_product(v1, q) / cross_product(v1, v2)

  return (s >= 0.0) and (t >= 0.0) and (s + t <= 1.0)


def _color_xy_brightness_to_RGB(vX, vY, ibrightness, Gamut=None):
  """Convert from XYZ to RGB."""
  if Gamut:
      if not _check_point_in_lamps_reach((vX, vY), Gamut):
          xy_closest = _get_closest_point_to_point((vX, vY), Gamut)
          vX = xy_closest[0]
          vY = xy_closest[1]

  brightness = ibrightness / 255.0
  if brightness == 0.0:
      return (0, 0, 0)

  Y = brightness

  if vY == 0.0:
      vY += 0.00000000001

  X = (Y / vY) * vX
  Z = (Y / vY) * (1 - vX - vY)

  # Convert to RGB using Wide RGB D65 conversion.
  r = X * 1.656492 - Y * 0.354851 - Z * 0.255038
  g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152
  b = X * 0.051713 - Y * 0.121364 + Z * 1.011530

  # Apply reverse gamma correction.
  r, g, b = map(
      lambda x: (12.92 * x)
      if (x <= 0.0031308)
      else ((1.0 + 0.055) * pow(x, (1.0 / 2.4)) - 0.055),
      [r, g, b],
  )

  # Bring all negative components to zero.
  r, g, b = map(lambda x: max(0, x), [r, g, b])

  # If one component is greater than 1, weight components by that value.
  max_component = max(r, g, b)
  if max_component > 1:
      r, g, b = map(lambda x: x / max_component, [r, g, b])

  ir, ig, ib = map(lambda x: int(x * 255), [r, g, b])

  return (ir, ig, ib)


def _color_xy_to_RGB(vX, vY, Gamut=None):
  """Convert from XY to a normalized RGB."""
  return _color_xy_brightness_to_RGB(vX, vY, 255, Gamut)


def _color_xy_to_hs(vX, vY, Gamut=None):
  """Convert an xy color to its hs representation."""
  h, s, _ = _color_RGB_to_hsv(*_color_xy_to_RGB(vX, vY, Gamut))
  return h, s


def _color_RGB_to_xy(iR, iG, iB, Gamut=None):
  """Convert from RGB color to XY color."""
  return _color_RGB_to_xy_brightness(iR, iG, iB, Gamut)[:2]


def _color_RGB_to_xy_brightness(iR, iG, iB, Gamut=None):
  """Convert from RGB color to XY color."""
  if iR + iG + iB == 0:
      return 0.0, 0.0, 0

  R = iR / 255
  B = iB / 255
  G = iG / 255

  # Gamma correction
  R = pow((R + 0.055) / (1.0 + 0.055), 2.4) if (R > 0.04045) else (R / 12.92)
  G = pow((G + 0.055) / (1.0 + 0.055), 2.4) if (G > 0.04045) else (G / 12.92)
  B = pow((B + 0.055) / (1.0 + 0.055), 2.4) if (B > 0.04045) else (B / 12.92)

  # Wide RGB D65 conversion formula
  X = R * 0.664511 + G * 0.154324 + B * 0.162028
  Y = R * 0.283881 + G * 0.668433 + B * 0.047685
  Z = R * 0.000088 + G * 0.072310 + B * 0.986039

  # Convert XYZ to xy
  x = X / (X + Y + Z)
  y = Y / (X + Y + Z)

  # Brightness
  Y = 1 if Y > 1 else Y
  brightness = round(Y * 255)

  # Check if the given xy value is within the color-reach of the lamp.
  if Gamut:
      in_reach = _check_point_in_lamps_reach((x, y), Gamut)
      if not in_reach:
          xy_closest = _get_closest_point_to_point((x, y), Gamut)
          x = xy_closest[0]
          y = xy_closest[1]

  return round(x, 3), round(y, 3), brightness


# These method are from the circadian_lighting component

def _get_sunrise_sunset(app, date=None):
  if date is None:
    date = app.datetime()

  sunrise_dt = app.sunrise()
  sunset_dt = app.sunset()

  sunrise = date.replace(hour=sunrise_dt.hour, minute=sunrise_dt.minute, second=sunrise_dt.second, microsecond=sunrise_dt.microsecond)
  sunset = date.replace(hour=sunset_dt.hour, minute=sunset_dt.minute, second=sunset_dt.second, microsecond=sunset_dt.microsecond)

  return {
    SUN_EVENT_SUNRISE: sunrise,
    SUN_EVENT_SUNSET: sunset,
    'solar_noon': sunrise + (sunset - sunrise)/2,
    'solar_midnight': sunset + ((sunrise + dt.timedelta(days=1)) - sunset)/2
  }


def _calc_percent(app):
  today_sun_times = _get_sunrise_sunset(app)

  now = dt.datetime.now()
  now_seconds = now.timestamp()
  today_sunrise_seconds = today_sun_times[SUN_EVENT_SUNRISE].timestamp()
  today_sunset_seconds = today_sun_times[SUN_EVENT_SUNSET].timestamp()
  today_solar_noon_seconds = today_sun_times['solar_noon'].timestamp()
  today_solar_midnight_seconds = today_sun_times['solar_midnight'].timestamp()

  # app._logger.log("now: " + str(now) + "\n\n today_sun_times: " + str(today_sun_times), level='DEBUG')

  if now < today_sun_times[SUN_EVENT_SUNRISE]:
    yesterday_sun_times = _get_sunrise_sunset(app, now - dt.timedelta(days=1))
    yesterday_sunrise_seconds = yesterday_sun_times[SUN_EVENT_SUNRISE].timestamp()
    yesterday_sunset_seconds = yesterday_sun_times[SUN_EVENT_SUNSET].timestamp()
    yesterday_solar_midnight_seconds = yesterday_sun_times['solar_midnight'].timestamp()

    # app._logger.log("yesterday_sun_times: " + str(yesterday_sun_times), level='DEBUG')

    x1 = yesterday_sunset_seconds
    y1 = 0

    if today_sun_times['solar_midnight'] > yesterday_sun_times[SUN_EVENT_SUNSET] and today_sun_times['solar_midnight'] < today_sun_times[SUN_EVENT_SUNRISE]:
      x2 = today_solar_midnight_seconds
    else:
      x2 = yesterday_solar_midnight_seconds
    y2 = -100

    x3 = today_sunrise_seconds
    y3 = 0
  elif now > today_sun_times[SUN_EVENT_SUNSET]:
    tomorrow_sun_times = _get_sunrise_sunset(app, now + dt.timedelta(days=1))
    tomorrow_sunrise_seconds = tomorrow_sun_times[SUN_EVENT_SUNRISE].timestamp()
    tomorrow_sunset_seconds = tomorrow_sun_times[SUN_EVENT_SUNSET].timestamp()
    tomorrow_solar_midnight_seconds = tomorrow_sun_times['solar_midnight'].timestamp()

    x1 = today_sunset_seconds
    y1 = 0

    if today_sun_times['solar_midnight'] > today_sun_times[SUN_EVENT_SUNSET] and today_sun_times['solar_midnight'] < tomorrow_sun_times[SUN_EVENT_SUNRISE]:
      x2 = today_solar_midnight_seconds
    else:
      x2 = tomorrow_solar_midnight_seconds
    y2 = -100

    x3 = tomorrow_sunrise_seconds
    y3 = 0
  else:
    x1 = today_sunrise_seconds
    y1 = 0
    x2 = today_solar_noon_seconds
    y2 = 100
    x3 = today_sunset_seconds
    y3 = 0

  # app._logger.log("x1: " + str(x1) + "\n\n y1: " + str(y1) + "\n\n x2: " + str(x2) + "\n\n y2: " + str(y2), level='DEBUG')

  # Generate color temperature parabola from points
  a1 = -x1**2+x2**2
  b1 = -x1+x2
  d1 = -y1+y2
  a2 = -x2**2+x3**2
  b2 = -x2+x3
  d2 = -y2+y3
  bm = -(b2/b1)
  a3 = bm*a1+a2
  d3 = bm*d1+d2
  a = d3/a3
  b = (d1-a1*a)/b1
  c = y1-a*x1**2-b*x1
  percentage = a*now_seconds**2+b*now_seconds+c

  # app._logger.log("percentage: " + str(percentage), level='DEBUG')
  return percentage


def calc_rgb(app, min_colortemp=DEFAULT_MIN_CT, max_colortemp=DEFAULT_MAX_CT):
  return _color_temperature_to_rgb(calc_colortemp(app, min_colortemp, max_colortemp))


def calc_xy(app, min_colortemp=DEFAULT_MIN_CT, max_colortemp=DEFAULT_MAX_CT):
  rgb = calc_rgb(app, min_colortemp, max_colortemp)
  iR = rgb[0]
  iG = rgb[1]
  iB = rgb[2]
  return _color_RGB_to_xy(iR, iG, iB)


def calc_hs(app, min_colortemp=DEFAULT_MIN_CT, max_colortemp=DEFAULT_MAX_CT):
  xy = calc_xy(app, min_colortemp, max_colortemp)
  vX = xy[0]
  vY = xy[1]
  return _color_xy_to_hs(vX, vY)


def calc_colortemp(app, min_colortemp=DEFAULT_MIN_CT, max_colortemp=DEFAULT_MAX_CT):
  if _calc_percent(app) > 0:
    return ((max_colortemp - min_colortemp) * (_calc_percent(app) / 100)) + min_colortemp
  else:
    return min_colortemp


def calc_brightness(app, min_brightness=DEFAULT_MIN_BRIGHTNESS, max_brightness=DEFAULT_MAX_BRIGHTNESS):
  if _calc_percent(app) > 0:
    return max_brightness
  else:
    return ((max_brightness - min_brightness) * ((100 + _calc_percent(app)) / 100)) + min_brightness


