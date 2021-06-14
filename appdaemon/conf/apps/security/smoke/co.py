"""

Smoke & CO Detectors

TODO:
"""

from base_app import BaseApp
import datetime
from dateutil.relativedelta import relativedelta

# Testing Notification Parameters
MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING = 3
TEST_NOTIFICATION_DAY = 1
TEST_NOTIFICATION_HOUR = 19
TEST_NOTIFICATION_MINUTE = 30

UPSTAIRS_CO_DETECTOR = 'binary_sensor.upstairs_co_smoke_detector'

co_detectors = {
  'upstairs': UPSTAIRS_CO_DETECTOR,
}


class CODetector(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.lights = self.get_app('lights')
    self.notifier = self.get_app('notifier')

    # Listen for all detectors turning ON
    for detector in co_detectors.values():
      self.listen_state(self._smoke_detector_triggered_callback, detector, new='on')

    # Notify us to test smoke detectors every X number of months on the first day at 7:30PM
    month_to_check = int(self.datetime().month / MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING) * MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
    if month_to_check == self.datetime().month and (self.datetime().day > TEST_NOTIFICATION_DAY or (self.datetime().hour > TEST_NOTIFICATION_HOUR and self.datetime().minute > TEST_NOTIFICATION_MINUTE)):
      month_to_check += MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
      month_to_check = month_to_check % 12
      if month_to_check == 0: month_to_check = 1
    dt_notify = self.datetime().replace(month=month_to_check, day=TEST_NOTIFICATION_DAY, hour=TEST_NOTIFICATION_HOUR, minute=TEST_NOTIFICATION_MINUTE) 
    three_months = dt_notify + relativedelta(months=MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING)
    seconds_next_three_months = (dt_notify - self.datetime()).total_seconds()
    self._next_smoke_detector_test_run_in = self.run_in(self._smoke_detector_periodic_test_notification, seconds_next_three_months)

    # Alternative method but might not be exact over the long run (AD would likely be reset before this would be an issue though)
    # self.run_every(self._smoke_detector_periodic_test_notification, dt_notify, (three_months - self.datetime()).total_seconds())


  def map_alias_to_entity(self, alias):
    """ Map name/alias to detector entity_id """
    entity_id = alias
    if not self.entity_exists(entity_id):
      # self._logger.log(f'{alias} (entity_id: {co_detectors.get(alias)}) does not exist.')
      return co_detectors.get(alias, None) 
    return entity_id


  def is_triggered(self, detector):
    """ return True if the smoke detector is currently triggered """
    detector = self.map_alias_to_entity(detector)
    if detector is not None:
      # self._logger.log(f'Testing {detector} is_triggered state: {self.get_state(detector)}')
      return self.get_state(detector) == 'on'
    return False


  def _smoke_detector_periodic_test_notification(self, entity, attribute, old, new, kwargs):
    """ Periodic Smoke detector test notification """
    log_msg = f'Please test the CO detectors. locals: {locals()}'
    self._logger.log(log_msg)
    tts_msg = f'Please test the carbon monoxide detectors.'
    self.notifier.tts_notify(tts_msg)
    self.notifier.telegram_notify(tts_msg)

    # Notify us to test smoke detectors every X number of months on the first day at 7:30PM
    month_to_check = self.datetime().month % MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING * MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
    if month_to_check == self.datetime().month and (self.datetime().day > 1 or (self.datetime().hour > 19 and self.datetime().minute > 30)):
      self._logger.log(f'same month and before 7:30PM on the first day of the month')
      month_to_check += MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
    dt_notify = self.datetime().replace(month=month_to_check, day=1, hour=19, minute=30) 
    seconds_next_three_months = (dt_notify - self.datetime()).total_seconds()

    if self._next_smoke_detector_test_run_in is not None:
      self.cancel_timer(self._next_smoke_detector_test_run_in)
      self._next_smoke_detector_test_run_in = None
    self._next_smoke_detector_test_run_in = self.run_in(self._smoke_detector_periodic_test_notification, seconds_next_three_months)
    self._logger.log(f'Next carbon monoxide detector test notification datetime: {dt_notify} (seconds: {seconds_next_three_months})')


  def _smoke_detector_triggered_callback(self, entity, attribute, old, new, kwargs):
    log_msg = f'The {self.friendly_name(entity)} ({entity}) has been triggered! Please have a look immediately. Locals: {locals()}'
    self._logger.log(log_msg)
    tts_msg = f'The {self.friendly_name(entity)} has been triggered!'
    self.notifier.tts_notify(tts_msg, speaker_override=True, volume=0.6)
    self.notifier.telegram_notify(tts_msg)


  def test(self, entity, attribute, old, new, kwargs):
    self.log(f'Testing CO & Smoke Module: ') 
    # self._test_detector_states()
    # self._test_detector_name_mapping()
    # self._smoke_detector_periodic_test_notification(None,None,None,None,None)

  def _test_detector_states(self):
    self._logger.log(f'---------------------')
    self._logger.log(f'Testing CO detector states: ')
    for name, detector in co_detectors.items():
      self._logger.log(f'{name} is currently {self.get_state(detector)} (is_triggered: {self.is_triggered(name)}).')
    self._logger.log(f'---------------------')

  def _test_detector_name_mapping(self):
    self._logger.log(f'---------------------')
    self._logger.log(f'Testing CO detector alias mapping: ')
    for name, detector in co_detectors.items():
      self._logger.log(f'"{name}" entity_id is "{self.map_alias_to_entity(name)}".')
      self._logger.log(f'"{detector}" entity_id is "{self.map_alias_to_entity(detector)}".')
    self._logger.log(f'---------------------')
