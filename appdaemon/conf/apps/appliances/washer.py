
"""
Washing Machine app that uses a plug that monitors power to determine when the washer is running.
Also monitors if the power exceeds the plugs rated level

NOTE: When using any parent class method must call super().parent_method() when using
"""

from appliance_base import PowerAppliance

class Washer(PowerAppliance):

  def setup(self):
    super().setup()
    # self.listen_state(self.test,'input_boolean.ad_testing_1')

    # Force an update on restart
    self.update(self.sensor_state)


  def terminate(self):
    super().terminate()


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing Washing Machine Module: ')
    self._logger.log('test() called from {}'.format(self.friendly_name))
