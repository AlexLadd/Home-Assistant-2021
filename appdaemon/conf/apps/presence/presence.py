

"""
Base Presence App 
  -> Provides an interface for basic presence data
  -> Dependent on base_app

Dependencies:
  -> custom_logger
  -> Cannot use any other dep

Functionality:
  -> Provices access to location data for household members
  -> This module does not contain any of the business logic

Future updates:
  -> 

Last updates: Jan 22, 2021
"""

from base_app import BaseApp
import datetime
from const import OCCUPANCY_BOOLEAN, GUEST_MODE_BOOLEAN, VACATION_MODE_BOOLEAN, ALEX_AWAY_BOOLEAN, STEPH_AWAY_BOOLEAN, BOTH_TOGETHER_SENSOR
from utils import last_changed

# TODO:
#   - Change turn off occupancy to check self.anyone_home() so it can be called safely anytime and produce the correct result



# Home is higher since someone is obviously home incase of some issue
RECENTLY_HOME_CUTOFF_TIME = 5*60
RECENTLY_LEFT_CUTOFF_TIME = 1*60

HOME_TODAY_CUTOFF_TIME = 18*60*60

NOTIFY_TARGET = 'alex'
NOTIFY_TITLE = 'Presence'


class Presence(BaseApp):

  def setup(self):
    # self.listen_state(self.test,'input_boolean.ad_testing_2')
    pass

  @property
  def alex_home(self):
    return bool(self.get_state(ALEX_AWAY_BOOLEAN) == 'off')

  @property
  def alex_home_today(self):
    return bool(last_changed(self, ALEX_AWAY_BOOLEAN) < HOME_TODAY_CUTOFF_TIME)

  @property
  def alex_just_got_home(self):
    return bool(self.alex_home and last_changed(self, ALEX_AWAY_BOOLEAN) < RECENTLY_HOME_CUTOFF_TIME)

  @property
  def alex_away(self):
    return bool(self.get_state(ALEX_AWAY_BOOLEAN) == 'on')

  @property
  def alex_just_left(self):
    return bool(self.alex_away and last_changed(self, ALEX_AWAY_BOOLEAN) < RECENTLY_LEFT_CUTOFF_TIME)

  @property
  def steph_home(self):
    return bool(self.get_state(STEPH_AWAY_BOOLEAN) == 'off')

  @property
  def steph_home_today(self):
    return bool(last_changed(self, STEPH_AWAY_BOOLEAN) < HOME_TODAY_CUTOFF_TIME)

  @property
  def steph_just_got_home(self):
    return bool(self.steph_home and last_changed(self, STEPH_AWAY_BOOLEAN) < RECENTLY_HOME_CUTOFF_TIME)

  @property
  def steph_away(self):
    return bool(self.get_state(STEPH_AWAY_BOOLEAN) == 'on')

  @property
  def steph_just_left(self):
    return bool(self.steph_away and last_changed(self, STEPH_AWAY_BOOLEAN) < RECENTLY_LEFT_CUTOFF_TIME)

  @property
  def both_together(self):
    return bool(self.get_state(BOTH_TOGETHER_SENSOR) == 'on')

  @property
  def someone_home(self):
    return bool(self.steph_home or self.alex_home)

  @property
  def one_person_home(self):
    return bool(self.steph_home and not self.alex_home or \
                self.alex_home and not self.steph_home)

  @property
  def everyone_home(self):
    return bool(self.alex_home and self.steph_home)

  @property
  def someone_just_got_home(self):
    return bool(self.alex_just_got_home or self.steph_just_got_home)

  @property
  def someone_just_left(self):
    return bool(self.alex_just_left or self.steph_just_left)

  @property
  def recent_presence_transition(self):
    """ Someone recently arrived/left home """
    return bool(self.someone_just_got_home or self.someone_just_left)
  
  @property
  def occupancy(self):
    return bool(self.get_state(OCCUPANCY_BOOLEAN) == 'on')

  @property
  def guest_mode(self):
    return bool(self.get_state(GUEST_MODE_BOOLEAN) == 'on')

  @property
  def vacation_mode(self):
    return bool(self.get_state(VACATION_MODE_BOOLEAN) == 'on')


  def turn_off_vacation_mode(self):
    if self.vacation_mode:
      msg = 'Vacation mode turned off.'
      self._logger.log(msg)
      self.turn_off(VACATION_MODE_BOOLEAN)

  def turn_on_vacation_mode(self):
    if not self.vacation_mode:
      msg = 'Vacation mode turned on.'
      self._logger.log(msg)
      self.turn_on(VACATION_MODE_BOOLEAN)

  def set_vacation_mode(self, state):
    if state not in ['on','off']:
      self._logger.log('Invalid input state.')
      return
    if state == 'on':
      self.turn_on_vacation_mode()
    else:
      self.turn_off_vacation_mode()


  def turn_off_both_together(self):
    if self.both_together:
      self._logger.log('Both together turned off.')
      self.turn_off(BOTH_TOGETHER_SENSOR)

  def turn_on_both_together(self):
    if not self.both_together:
      self._logger.log('Both together turned on.')
      self.turn_on(BOTH_TOGETHER_SENSOR)

  def set_both_together(self, state):
    if state not in ['on','off']:
      self._logger.log('Invalid input state.')
      return
    if state == 'on':
      self.turn_on_both_together()
    else:
      self.turn_off_both_together()


  def turn_off_occupancy(self):
    if self.occupancy and not self.guest_mode:
      self._logger.log('Occupancy turned off.')
      self.turn_off(OCCUPANCY_BOOLEAN)

  def turn_on_occupancy(self):
    if not self.occupancy:
      self._logger.log('Occupancy turned on.')
      self.turn_on(OCCUPANCY_BOOLEAN)

  def set_occupancy(self, state):
    if state not in ['on','off']:
      self._logger.log('Invalid input state.')
      return
    if state == 'on':
      self.turn_on_occupancy()
    else:
      self.turn_off_occupancy()


  def turn_off_guest_mode(self):
    if self.guest_mode:
      msg = 'Guest mode turned off.'
      self._logger.log(msg)
      self.turn_off(GUEST_MODE_BOOLEAN)

  def turn_on_guest_mode(self):
    if not self.guest_mode:
      msg = 'Guest mode turned on.'
      self._logger.log(msg)
      self.turn_on(GUEST_MODE_BOOLEAN)

  def set_guest_mode(self, state):
    if state not in ['on','off']:
      self._logger.log('Invalid input state.')
      return
    if state == 'on':
      self.turn_on_guest_mode()
    else:
      self.turn_off_guest_mode()


  def terminate(self):
    pass


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing Presence Module:')
    # self._test_suite()

  
  def _test_suite(self):
    self._logger.log(f'Steph home today: {self.steph_home_today}')  
