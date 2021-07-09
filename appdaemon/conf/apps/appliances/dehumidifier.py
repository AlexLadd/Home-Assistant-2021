
"""
Dehumidifier App
Use this instead of appliance_base.py in the yaml to allow us custom modification down the road

NOTE: When using any parent class method must call super().parent_method() when using
"""

from appliance_base import PowerAppliance


class Dehumidifier(PowerAppliance):

  def setup(self):
    super().setup()
    # self.listen_state(self.test,'input_boolean.ad_testing_1')

    # Force an update on restart
    self.update(self.sensor_state)


  def terminate(self):
    super().terminate()


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing Dehumidifier Module: ')
    self._logger.log('test() called from {}'.format(self.friendly_name))
    self._logger.log(f'Currently on: {self.is_on}')