
"""
Household Smoke Detectors

TODO:
  - Add periodic notification to test detectorsolp
  - Add some sort of household 'Alarm' like flashing lights once we are confident in this module not producing false alarms
"""

from base_app import BaseApp
import datetime
from dateutil.relativedelta import relativedelta

# Testing Notification Parameters
MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING = 3
TEST_NOTIFICATION_DAY = 1
TEST_NOTIFICATION_HOUR = 19
TEST_NOTIFICATION_MINUTE = 20

MAIN_HALLWAY_SMOKE_DETECTOR = 'binary_sensor.main_hallway_smoke_detector'
LAUNDRY_ROOM_SMOKE_DETECTOR = 'binary_sensor.laundry_room_smoke_detector'
OFFICE_SMOKE_DETECTOR = 'binary_sensor.office_smoke_detector'

smoke_detectors = {
  'main_hallway': MAIN_HALLWAY_SMOKE_DETECTOR,
  'laundry_room': LAUNDRY_ROOM_SMOKE_DETECTOR,
  'office': OFFICE_SMOKE_DETECTOR,
}


class Smoke(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.lights = self.get_app('lights')
    self.notifier = self.get_app('notifier')

    # Listen for all detectors turning ON
    for detector in smoke_detectors.values():
      self.listen_state(self._smoke_detector_triggered_callback, detector, new='on')

    # Notify us to test smoke detectors every X number of months on the first day at 7:30PM - OLD CODE
    # month_to_check = self.datetime().month % MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING * MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
    # if month_to_check == self.datetime().month and (self.datetime().day > 1 or (self.datetime().hour > 19 and self.datetime().minute > 30)):
    #   self._logger.log(f'same month and before 7:30PM on the first day of the month')
    #   month_to_check += MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
    # dt_notify = self.datetime().replace(month=month_to_check, day=1, hour=19, minute=30) 
    # three_months = dt_notify + relativedelta(months=MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING)
    # seconds_next_three_months = (dt_notify - self.datetime()).total_seconds()
    # self._next_smoke_detector_test_run_in = self.run_in(self._smoke_detector_periodic_test_notification, seconds_next_three_months)

    # Notify us to test smoke detectors every X number of months on the first day at 7:30PM
    # month_to_check = int(self.datetime().month / MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING) * MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
    # if month_to_check == self.datetime().month and (self.datetime().day > TEST_NOTIFICATION_DAY or (self.datetime().hour > TEST_NOTIFICATION_HOUR and self.datetime().minute > TEST_NOTIFICATION_MINUTE)):
    #   month_to_check += MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
    #   month_to_check = month_to_check % 12
    #   if month_to_check == 0: month_to_check = 1
    # dt_notify = self.datetime().replace(month=month_to_check, day=TEST_NOTIFICATION_DAY, hour=TEST_NOTIFICATION_HOUR, minute=TEST_NOTIFICATION_MINUTE) 
    # three_months = dt_notify + relativedelta(months=MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING)
    # seconds_next_three_months = (dt_notify - self.datetime()).total_seconds()
    # self._next_smoke_detector_test_run_in = self.run_in(self._smoke_detector_periodic_test_notification, seconds_next_three_months)


    # Notify us to test smoke detectors every X number of months on the first day at 7:30PM
    month_to_check = int(self.datetime().month / MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING) * MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
    if month_to_check == 0: month_to_check = 3
    dt_check = self.datetime().replace(month=month_to_check, day=TEST_NOTIFICATION_DAY, hour=TEST_NOTIFICATION_HOUR, minute=TEST_NOTIFICATION_MINUTE) 

    if month_to_check == self.datetime().month and self.datetime() < dt_check:
      # It is notification day but we have not reached the notify time yet!
      pass
    else:
      month_to_check += MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
      if month_to_check > 12: month_to_check = 3

    next_notify = self.datetime().replace(month=month_to_check, day=TEST_NOTIFICATION_DAY, hour=TEST_NOTIFICATION_HOUR, minute=TEST_NOTIFICATION_MINUTE) 
    seconds_next_three_months = (next_notify - self.datetime()).total_seconds()
    self._next_smoke_detector_test_run_in = self.run_in(self._smoke_detector_periodic_test_notification, seconds_next_three_months)

    # self._logger.log(f'month_to_check: {month_to_check}, check: {int(3/3)}')
    # self._logger.log(f'next_notify: {next_notify}, seconds_next_three_months: {seconds_next_three_months}, today: {self.datetime()}, delta: {next_notify - self.datetime()}')


  def map_alias_to_entity(self, alias):
    """ Map name/alias to detector entity_id """
    entity_id = alias
    if not self.entity_exists(entity_id):
      # self._logger.log(f'{alias} (entity_id: {smoke_detectors.get(alias)}) does not exist.')
      return smoke_detectors.get(alias, None) 
    return entity_id


  def is_triggered(self, detector):
    """ return True if the smoke detector is currently triggered """
    detector = self.map_alias_to_entity(detector)
    if detector is not None:
      # self._logger.log(f'Testing {detector} is_triggered state: {self.get_state(detector)}')
      return self.get_state(detector) == 'on'
    return False


  def _smoke_detector_periodic_test_notification(self, kwargs):
    """ Periodic Smoke detector test notification """
    log_msg = f'Please test the smoke detectors. locals: {locals()}'
    self._logger.log(log_msg)
    tts_msg = f'Please test the smoke detectors.'
    self.notifier.tts_notify(tts_msg)
    self.notifier.telegram_notify(tts_msg)

    # Notify us to test smoke detectors every X number of months on the first day at 7:30PM
    month_to_check = int(self.datetime().month / MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING) * MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING + MONTHS_BETWEEN_SMOKE_DETECTOR_TESTING
    dt_notify = self.datetime().replace(month=month_to_check, day=TEST_NOTIFICATION_DAY, hour=TEST_NOTIFICATION_HOUR, minute=TEST_NOTIFICATION_MINUTE) 
    seconds_next_three_months = (dt_notify - self.datetime()).total_seconds()

    if self._next_smoke_detector_test_run_in is not None:
      self.cancel_timer(self._next_smoke_detector_test_run_in)
      self._next_smoke_detector_test_run_in = None
    self._next_smoke_detector_test_run_in = self.run_in(self._smoke_detector_periodic_test_notification, seconds_next_three_months)
    self._logger.log(f'Next smoke detector test notification datetime: {dt_notify} (seconds: {seconds_next_three_months})')


  def _smoke_detector_triggered_callback(self, entity, attribute, old, new, kwargs):
    log_msg = f'The {self.friendly_name(entity)} ({entity}) has been triggered! Please have a look immediately. Locals: {locals()}'
    self._logger.log(log_msg)
    tts_msg = f'The {self.friendly_name(entity)} has been triggered!'
    self.notifier.tts_notify(tts_msg, speaker_override=True, volume=0.6)
    self.notifier.telegram_notify(tts_msg)


  def test(self, entity, attribute, old, new, kwargs):
    self.log(f'Testing Smoke Module: ') 
    # self._test_detector_states()
    # self._test_detector_name_mapping()
    self._smoke_detector_periodic_test_notification(None, None)

  def _test_detector_states(self):
    self._logger.log(f'---------------------')
    self._logger.log(f'Testing smoke detector states: ')
    for name, detector in smoke_detectors.items():
      self._logger.log(f'{name} is currently {self.get_state(detector)} (is_triggered: {self.is_triggered(name)}).')
    self._logger.log(f'---------------------')

  def _test_detector_name_mapping(self):
    self._logger.log(f'---------------------')
    self._logger.log(f'Testing smoke detector alias mapping: ')
    for name, detector in smoke_detectors.items():
      self._logger.log(f'"{name}" entity_id is "{self.map_alias_to_entity(name)}".')
      self._logger.log(f'"{detector}" entity_id is "{self.map_alias_to_entity(detector)}".')
    self._logger.log(f'---------------------')

