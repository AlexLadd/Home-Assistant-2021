"""
Base Notifier App

Delegates to all other notifier platforms (TTS, Telegram, HTML5, etc)
"""

from base_app import BaseApp


class Notifier(BaseApp):

  def setup(self):
    self.listen_state(self.test,'input_boolean.ad_testing_3')

    self.telegram = self.get_app('telegram')
    self.tts = self.get_app('tts')

    self.listen_event(self._logger_message_event_cb, 'notifier.log_message')


  def html5_notify(self, target, message, title='Home Assistant', tag='', actions=[], renotify=False, image_path=None):
    # self.html5.html5_notify(target, message, title, tag, actions, renotify, image_path)
    self._logger.log(f'html5_notify not implemented', level='WARNING')
    self.persistent_notify(message, title, tag)


  def html5_dismiss(self, target=None, tag=''):
    self.html5.html5_dismiss(target, tag)


  def persistent_notify(self, message, title='', tag=''):
    """ 
    Send an HA persistent notification (Display on HA UI like other internal messages)
    
    param tag: Tag name to use for the message 
      - tag=None will force duplicate messages to be sent
    """
    self._logger.log('Notifying via Persistent Notification: "{}"'.format(message), level=self.debug_level)
    if tag == '':
      tag = message.replace(' ','-')
    self.persistent_notification(message, title, tag)


  @property
  def tts_is_playing(self):
    return self.tts.tts_playing

  def tts_notify(self, message, media_player=None, volume=None, speaker_override=False, no_greeting=False, options={}):
    self.tts.tts_notify(message, media_player, volume, speaker_override, no_greeting, options)


  def _logger_message_event_cb(self, event_name, data, kwargs):
    # self._logger.log(f'_logger_message_event_cb called: {locals()}')
    self.telegram_notify(data.get('message', 'ERROR: No Message Provided'), 'logging', 'Log Error')


  def telegram_notify(self, msg, target=[], title='', disable_notification=False, tag=''):
    self.telegram.telegram_notify(msg, target, title, disable_notification, tag)


  def terminate(self):
    pass


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing Notifier Module:')
    # self._test_all_notifiers()


  def _test_all_notifiers(self):
    title = 'Testing Notifiers'
    msg = 'Testing the various notifier platforms...'
    
    self.telegram_notify('Test Telegram message.', 'logging')
    self.tts_notify(msg)
    self.persistent_notify(msg, title)
    self.html5_notify('alex', msg, title)

    self._logger.log(f'tts_playing: {self.tts_is_playing}')
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 0.1)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 0.3)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 0.5)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 0.7)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 0.9)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 1.5)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 2)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 3)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 4)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 5)
    self.run_in(lambda *_: self._logger.log(f'tts_playing: {self.tts_is_playing}'), 10)


