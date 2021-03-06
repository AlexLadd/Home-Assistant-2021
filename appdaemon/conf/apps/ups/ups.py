"""
APC UPS Monitoring & safe NUC shutdown

TODO: 
  - Add NUC autoshutdown feature when UPS charge is low and power is down
  - Add notification when UPS is 'down' for long period of time
"""

from base_app import BaseApp
import datetime
from const import CONF_ENTITY_ID


UPS_STATUS_SENSOR = 'sensor.ups_status'
UPS_STATUS_DATA = 'sensor.ups_status_data'
UPS_BATTERY_CHARGE = 'sensor.ups_battery_charge'
UPS_BATTERY_RUNTIME = 'sensor.ups_battery_runtime'

# Values for charging & discharging
STATUS_SENSOR_ON = 'Online Battery Charging'
STATUS_SENSOR_OFF = 'On Battery Battery Discharging'
STATUS_DATA_ON = 'OL CHRG'
STATUS_DATA_OFF = 'OB DISCHRG'

UPS_OFFLINE_NOTIFY_SECONDS = 30*60 # 30 minutes offline before notification sent
UPS_OFFLINE_STATE = 'unavailable'

NOTIFY_TARGET = 'status'
NOTIFY_TITLE = 'APC UPS'


class UPS(BaseApp):

  def setup(self):
    # self.listen_state(self.test,'input_boolean.ad_testing_1')
    
    self.notifier = self.get_app('notifier')

    self.listen_state(self._ups_charge_callback, UPS_BATTERY_CHARGE)
    # self.listen_state(self._ups_status_callback, UPS_STATUS_SENSOR)   # Duplicate functionality of UPS_STATUS_DATA listener
    self.listen_state(self._ups_status_callback, UPS_STATUS_DATA)
    self.listen_state(self._ups_status_unavailable_long_term, UPS_STATUS_SENSOR, duration=UPS_OFFLINE_NOTIFY_SECONDS, new=UPS_OFFLINE_STATE)

  def _ups_charge_callback(self, entity, attribute, old, new, kwargs):
    """ Monitor UPS charge """
    # self._logger.log(f'UPS charge went from {old} -> {new}')
    if not self.utils.valid_input(old, new):
      return

    try:
      charge = float(new)
    except:
      return 

    if charge < 50:
      self._logger.log(f'UPS charge is getting low: {charge}')
    elif charge < 20:
      msg = f'UPS charge is getting very low: {charge}'
      self._logger.log(msg, level='WARNING')
      self.notifier.telegram_notify(msg, ['status', 'alert'], NOTIFY_TITLE)


  def _ups_status_callback(self, entity, attribute, old, new, kwargs):
    """ Monitor UPS status changed """
    if not self.utils.valid_input(old, new) or old is None :
      self._logger.log(f'Invalid input: {old} -> {new}')
      return

    if new == STATUS_DATA_OFF or new == STATUS_SENSOR_OFF:
      msg = f'[APC UPS] The power is out at home! (Status: {old} -> {new})'
      self._logger.log(msg, level='WARNING')
      self.notifier.telegram_notify(msg, ['status', 'alert'], NOTIFY_TITLE)
    elif new == STATUS_DATA_ON or new == STATUS_SENSOR_ON:
      msg = f'[APC UPS] The power has been restored at home! (Status: {old} -> {new})'
      self._logger.log(msg, level='INFO')
      self.notifier.telegram_notify(msg, 'status', NOTIFY_TITLE)
    else:
      msg = f'APC UPS Status change from {old} -> {new}'
      self._logger.log(msg)
      # self.notifier.telegram_notify(msg, 'status', NOTIFY_TITLE)


  def _ups_status_unavailable_long_term(self, entity, attribute, old, new, kwargs):
    """ Send notification after UPS is 'unavailable' for a set amount of time """
    if not isinstance(new, str):
      return

    msg = f'The UPS has been in the {new} state for {UPS_OFFLINE_NOTIFY_SECONDS/60} minutes. Please have a look.'
    self._logger.log(msg + f'locals: {locals()}', level='WARNING')
    self.notifier.telegram_notify(msg, target='alarm', title='UPS OFFLINE')


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing UPS Module: ')  
    self._test_state_check()

  def _test_state_check(self):
    r = self.get_state(UPS_STATUS_SENSOR)
    self._logger.log(f'Status: {r}')
    r = self.get_state(UPS_STATUS_DATA)
    self._logger.log(f'Status Data: {r}')
    r = self.get_state(UPS_BATTERY_CHARGE)
    self._logger.log(f'Charge: {r}')
    r = self.get_state(UPS_BATTERY_RUNTIME)
    self._logger.log(f'Runtime: {r}')


  def terminate(self):
    pass
    

