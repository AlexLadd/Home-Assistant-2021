"""
App that controls security feature of the house:
  - lockdown
  - monitor that house stays locked down when asleep or away
  - monitor if emergency mode it on and flash lights and say TTS announcement
Note: This app does not use Lights app to turn on/off because it is too slow and error prone
"""

from base_app import BaseApp
import datetime
# from utils import list_to_pretty_print # This doesn;t exist in utils right now

# TODO:

EMERGENCY_TTS_FREQUENCY = 13
EMERGENCY_LIGHTS_FREQUENCY = 4
HUE_LIGHTS = 'light.all_hue_lights'
LIGHT_SWITCHES = 'group.light_switches_master'

VACANCY_MONITOR_FREQUENCY = 12*60*60

NOTIFY_TARGET = 'alex'
NOTIFY_TITLE = 'Security'


class SecurityManager(BaseApp):

  def setup(self):
    self._logger.log(f'Security app is not setup yet!')
    return


    # self.listen_state(self.test,'input_boolean.appdaemon_testing')

    # self.alarm = self.get_app('alarm')
    # self.garage = self.get_app('garage')
    self.dw = self.get_app('doors_windows')
    self.presence = self.get_app('presence')
    self.notifier = self.get_app('notifier')
    self.lights = self.get_app('lights')
    self.sleep = self.get_app('sleep')
    self.living_room_tv = self.get_app('living_room_tv')
    # self.messages = self.get_app('messages')
    self.se = self.get_app('spotify_engine')
    self.mp = self.get_app('speakers')

    self.handle_vacancy_monitoring = None

    # Check if security monitoring should be started on reboot
    if not self.presence.occupancy:
      self.start_security_monitoring()
    elif self.sleep.everyone_asleep:
      self.start_security_monitoring(frequency=60*60)

    # Listen for emergency mode
    # self.listen_state(self._emergency_mode_on_callback, self.const.EMERGENCY_MODE_BOOLEAN)


  @property
  def emergency_mode(self):
    return bool(self.get_state(self.const.EMERGENCY_MODE_BOOLEAN) == 'on')


  @property
  def house_locked_down(self):
    """ Verify the house locked down correctly """
    if self.presence.guest_mode:
      return True

    if not self.presence.occupancy:
      if not self.alarm.armed_away:
        return False
      if not self.lights.all_lights_off and not self.presence.vacation_mode:
        return False
      if not self.dw.doors_closed:
        return False
      if not self.dw.front_door_secure:
        return False
    elif self.presence.occupancy:
      if self.sleep.everyone_asleep:
        if not self.alarm.armed_home:
          return False
        if not self.dw.front_door_secure:
          return False
        if self.living_room_tv.is_on:
          return False
        if self.garage.is_open:
          return False
    return True 


  def _house_locked_down_entities(self):
    """ Returns a list of entites that are unsecure if any """
    if self.presence.guest_mode:
      return []

    unsecure = []

    if not self.presence.occupancy:
      if not self.alarm.armed_away:
        unsecure.append('alarm armed away')
      if not self.lights.all_lights_off and not self.presence.vacation_mode:
        # unsecure.append('lights')
        unsecure.extend(self.lights.lights_on_list())
      if not self.dw.doors_closed:
        unsecure.append('doors')
      if not self.dw.front_door_secure:
        unsecure.append('front door')
    elif self.presence.occupancy:
      if self.sleep.everyone_asleep:
        if not self.alarm.armed_home:
          unsecure.append('alarm armed home')
        if not self.dw.front_door_secure:
          unsecure.append('front door')
        if self.living_room_tv.is_on:
          unsecure.append('basement tv')
        if self.garage.is_open:
          unsecure.append('garage door')
    return unsecure


  @property
  def house_secure(self):
    """ Verify house is secure when in vacation mode """
    if self.presence.guest_mode:
      return True

    if not self.house_locked_down:
      return False
    if not self.dw.everything_closed:
      return False
    if not self.lights.all_lights_off_security_check:
      return False
    return True


  def _house_secure_entities(self):
    """ Returns a list of entites that are unsecure if any while in vacation mode """
    if self.presence.guest_mode:
      return []

    unsecure = []

    if not self.house_locked_down:
      unsecure = self._house_locked_down_entities()
    if not self.dw.everything_closed:
      if 'doors' in unsecure:
        unsecure.remove('doors')
      unsecure.append('doors and windows')
    if not self.lights.all_lights_off_security_check:
      if 'lights' not in unsecure:
        unsecure.append('lights')
    return unsecure


  def lockdown_house(self):
    self._logger.log('House lockdown initiated.', level='INFO')
    self.dw.lock_front_door()
    self.garage.close()
    if not self.presence.guest_mode:
      self.se.stop_music() # Stop Spotify music if playing
      self.lights.turn_all_off()
      self.living_room_tv.turn_off_tv()
      if self.presence.occupancy:
        self.alarm.arm_home()
      else:
        self.alarm.arm_away()
    else:
      self._logger.log('Guest mode is on, only a partial lockdown was done.', level='INFO')


  def get_unsecure_entities(self, light_check=True, window_check=True, door_check=True):
    """ Returns a human readable state of the unsecure entities in the house """
    # This method should not presume the intentions based on the household state
    # For example if guest_mode is on or not

    res = ''
    if window_check and door_check:
      if not self.dw.everything_closed:
        res = self.messages.entry_point_check() # Will get both windows and doors
    elif window_check:
      if not self.dw.windows_closed:
        res = self.messages.entry_point_check(door_check=False)
    elif door_check:
      if not self.dw.doors_closed:
        res = self.messages.entry_point_check(window_check=False)

    r = []
    if not self.dw.front_door_secure:
      r.append('front door lock')
    if self.garage.is_open:
      r.append('garage door')
    if not self.alarm.armed:
      r.append('alarm')
    if self.living_room_tv.is_on:
      r.append('basement TV')

    res += ' ' + list_to_pretty_print(r, 'unsecure')

    if light_check:
      if not self.lights.all_lights_off:
        res += ' ' + self.messages.light_check()

    return res.strip()


  def stop_security_monitoring(self):
    if self.handle_vacancy_monitoring:
      self._logger.log('Stopping vacancy monitoring.', level='INFO')
      self.cancel_timer(self.handle_vacancy_monitoring)
      self.handle_vacancy_monitoring = None


  def start_security_monitoring(self, frequency=None, start_offset=2):
    """ 
    param start_offset: Number of minutes before starting the check
    """
    self._logger.log('Starting vacancy monitoring.', level='INFO')
    if self.handle_vacancy_monitoring:
      self.cancel_timer(self.handle_vacancy_monitoring)

    self.handle_vacancy_monitoring = self.run_every(
      self._security_monitoring, 
      datetime.datetime.now() + datetime.timedelta(minutes=start_offset),
      frequency or VACANCY_MONITOR_FREQUENCY,
    )


  def _security_monitoring(self, kwargs):
    """ Verify that the house stays locked down """
    if self.anyone_home() and self.sleep.someone_awake:
      self._logger.log('Security monitoring is running while someone is home and awake, shutting down now.', level='WARNING')
      self.stop_security_monitoring()
      return

    msg = ''
    unsecure = []

    if not self.presence.vacation_mode:
      unsecure = self._house_locked_down_entities()
      if len(unsecure) > 0:
        msg = 'Security monitoring check. '
    else:
      unsecure = self._house_secure_entities()
      if len(unsecure) > 0:
        msg = 'Security monitoring check while in vacation mode. '

    if msg:
      if self.presence.guest_mode:
        msg += 'Guest mode is turned on, only a partial lockdown will be done. '
      msg += list_to_pretty_print(unsecure, 'unsecure') + ' Attempting to lockdown now. Please have a look.'
      msg = msg.strip()
      self._logger.log(msg, level='INFO')
      self.notifier.html5_notify(NOTIFY_TARGET, msg, NOTIFY_TITLE)  
      self.lockdown_house()


  def turn_on_emergency_mode(self):
    if not self.emergency_mode:
      message = 'Emergency mode turned on.'
      self._logger.log(message, level='INFO')
      self.notifier.html5_notify(NOTIFY_TARGET, message, NOTIFY_TITLE)
      self.turn_on(self.const.EMERGENCY_MODE_BOOLEAN)


  def turn_off_emergency_mode(self):
    if self.emergency_mode:
      message = 'Emergency mode turned off.'
      self._logger.log(message, level='INFO')
      self.notifier.html5_notify(NOTIFY_TARGET, message, NOTIFY_TITLE)
      self.turn_off(self.const.EMERGENCY_MODE_BOOLEAN)


  def _emergency_mode_on_callback(self, entity, attribute, old, new ,kwargs):
    """ Initialize emergency mode actions - flash lights and repeat TTS announcements """
    if self.utils.valid_input(old, new):
      if self.emergency_mode:
        self._logger.log('Emergency mode events triggered.', level='INFO')
        msg = 'You have been recorded on camera. The police have been notified. ' \
              'Please leave immediately.'
        self.notifier.tts_notify(msg, volume=0.7, speaker_override=True, no_greeting=True)

        # Prime lights to red where possible
        self.call_service('light/turn_on', entity_id=HUE_LIGHTS, brightness_pct=100, transition=0, rgb_color=[255,0,0])
        self.turn_on(LIGHT_SWITCHES)
        self.call_service('frontend/set_theme', name='Dark - Orange')
        self.run_in(self._emergency_lights_off, EMERGENCY_LIGHTS_FREQUENCY)

        # Start emergency_mode tts anouncement loop
        self._emergency_tts_announcement()
      elif not self.emergency_mode:
        # Turn all lights off? Leaving them on would brighten the house if someone was inside. 
        self.call_service('frontend/set_theme', name='Dark - Cyan')
        # Reset speaker volume back down to default levels
        self.mp.reset_volume()


  def _emergency_tts_announcement(self, kwargs=None):
    """ Repeat emergency message until emergency mode turned off """
    if self.emergency_mode:
      msg = 'Intruder in the house!...The police are on the way!...' * 3
      self.notifier.tts_notify(msg, volume=0.7, speaker_override=True, no_greeting=True)
      self.run_in(self._emergency_tts_announcement, EMERGENCY_TTS_FREQUENCY)


  def _emergency_lights_off(self, kwargs):
    if self.emergency_mode:
      self.turn_off(HUE_LIGHTS)
      self.turn_off(LIGHT_SWITCHES)
      self.run_in(self._emergency_lights_on, EMERGENCY_LIGHTS_FREQUENCY)


  def _emergency_lights_on(self, kwargs):
    if self.emergency_mode:
      self.turn_on(HUE_LIGHTS)
      self.turn_on(LIGHT_SWITCHES)
      self.run_in(self._emergency_lights_off, EMERGENCY_LIGHTS_FREQUENCY)


  def test(self, entity, attribute, old, new, kwargs):
    pass


  def terminate(self):
    pass