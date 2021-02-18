
"""
Base sleep app 
  -> Provides an interface for basic awake/asleep data
  -> Dependent on base_app and presence (used by most app so should not use any others)

Dependencies:
  -> custom_logger
  -> presence
  -> Cannot use any other dep

Functionality:
  -> Provices access to data on sleep state of household members
  -> This module does not contain any of the business logic

Future updates:
  -> 

NOTE: If everyone is away than everyone is considered awake by default

Last updates: Jan 22, 2021
"""

# TODO:

from base_app import BaseApp 
import datetime


class AwakeAsleep(BaseApp):

  def setup(self):
    # self.listen_state(self.test,'input_boolean.ad_testing_1')
    self.presence = self.get_app('presence')

  @property
  def steph_awake(self):
    return bool(self.get_state(self.const.STEPH_AWAKE_BOOLEAN) == 'on')

  @property
  def steph_asleep(self):
    return bool(self.get_state(self.const.STEPH_AWAKE_BOOLEAN) == 'off')

  @property
  def alex_awake(self):
    return bool(self.get_state(self.const.ALEX_AWAKE_BOOLEAN) == 'on')

  @property
  def alex_asleep(self):
    return bool(self.get_state(self.const.ALEX_AWAKE_BOOLEAN) == 'off')

  @property
  def everyone_asleep(self):
    return bool(self.get_state(self.const.EVERYONE_ASLEEP_BOOLEAN) == 'on')

  @property
  def everyone_awake(self):
    return bool(self.get_state(self.const.EVERYONE_AWAKE_BOOLEAN) == 'on')

  @property
  def someone_asleep(self):
    return bool(self.get_state(self.const.EVERYONE_AWAKE_BOOLEAN) == 'off')

  @property
  def someone_awake(self):
    return bool(self.get_state(self.const.EVERYONE_ASLEEP_BOOLEAN) == 'off')


  def sync_everyone_states(self):
    # If noone is home, consider everyone awake
    if self.presence.alex_away and self.presence.steph_away:
      self.turn_on(self.const.EVERYONE_AWAKE_BOOLEAN)
      self.turn_off(self.const.EVERYONE_ASLEEP_BOOLEAN)
    elif self.presence.alex_away:
      if self.steph_awake:
        self.turn_on(self.const.EVERYONE_AWAKE_BOOLEAN)
        self.turn_off(self.const.EVERYONE_ASLEEP_BOOLEAN)
      else:
        self.turn_off(self.const.EVERYONE_AWAKE_BOOLEAN)
        self.turn_on(self.const.EVERYONE_ASLEEP_BOOLEAN)
    elif self.presence.steph_away:
      if self.alex_awake:
        self.turn_on(self.const.EVERYONE_AWAKE_BOOLEAN)
        self.turn_off(self.const.EVERYONE_ASLEEP_BOOLEAN)
      else:
        self.turn_off(self.const.EVERYONE_AWAKE_BOOLEAN)
        self.turn_on(self.const.EVERYONE_ASLEEP_BOOLEAN)
    else:
      if self.alex_awake and self.steph_awake:
        self.turn_on(self.const.EVERYONE_AWAKE_BOOLEAN)
      else:
        self.turn_off(self.const.EVERYONE_AWAKE_BOOLEAN)

      if self.alex_awake or self.steph_awake:
        self.turn_off(self.const.EVERYONE_ASLEEP_BOOLEAN)
      else:
        self.turn_on(self.const.EVERYONE_ASLEEP_BOOLEAN)
  

  def set_steph(self, state):
    state = state.lower().strip()
    if state == 'awake' and self.steph_asleep:
      self._logger.log('Steph set to awake', 'DEBUG')
      self.turn_on(self.const.STEPH_AWAKE_BOOLEAN)
    elif state == 'asleep' and self.steph_awake:
      self._logger.log('Steph set to asleep', 'DEBUG')
      self.turn_off(self.const.STEPH_AWAKE_BOOLEAN)


  def set_alex(self, state):
    state = state.lower().strip()
    if state == 'awake' and self.alex_asleep:
      self._logger.log('Alex set to awake', 'DEBUG')
      self.turn_on(self.const.ALEX_AWAKE_BOOLEAN)
    elif state == 'asleep' and self.alex_awake:
      self._logger.log('Alex set to asleep', 'DEBUG')
      self.turn_off(self.const.ALEX_AWAKE_BOOLEAN)


  def terminate(self):
    pass


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing Sleep Module: ')
    self.set_alex('awake')



