
from base_app import BaseApp
import datetime
from const import CONF_ENTITY_ID


class AlarmController(BaseApp):

  def setup(self):
    self._logger.log(f'Setting up alarm controller.')
    return 

    # self.listen_state(self.test,'input_boolean.ad_testing_1')
    self.logger = self.get_app('custom_logger')
    self.notifier = self.get_app('notifier')
    self.alarm = self.get_app('alarm')
    # self.sm = self.get_app('security')
    self.presence = self.get_app('presence')

    self.listen_state(self._triggered_callback, self.const.ALARM_CONTROL_PANEL, new='triggered')
    self.listen_state(self._untrigger_callback, self.const.ALARM_CONTROL_PANEL, old='triggered')


  def _triggered_callback(self, entity, attribute, old, new, kwargs):
    # Securiy app handles the emergency mode actions when alarm is triggered
    # self.sm.turn_on_emergency_mode()
    pass


  def _untrigger_callback(self, entity, attribute, old, new, kwargs):
    # self.sm.turn_off_emergency_mode()
    if not self.presence.occupancy and self.alarm.disarmed:
      msg = 'The alarm was disarmed while nobody is home. Please have a look.'
      self.logger.log(msg, level='WARNING')
      self.notifier.html5_notify(NOTIFY_TARGET, msg, NOTIFY_TITLE)


  def test(self, entity, attribute, old, new, kwargs):
    pass  

  def terminate(self):
    pass
    
