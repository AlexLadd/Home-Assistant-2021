"""
Telegram Application

Handles/Processes incoming/outgoing telegram messages
"""

from base_app import BaseApp


CHATS = {
  'logging': -469980278,
  'status': -414341807,
  'alarm': -489764741,
  'reporting': -574720532,
  'alex': 1514688713
}
REVERSE_CHATS = {id: name for name, id in CHATS.items()}
VALID_IDS = [v for v in CHATS.values()]

BUG_REPORT_FILE = 'apps/notifier/telegram/bug_reports.txt'
BUG_REPORT_TEXT_KEY = 'Bug report'

FEATURE_REQUEST_FILE = 'apps/notifier/telegram/feature_requests.txt'
FEATURE_REQUEST_TEXT_KEY = 'Feature request'


class Telegram(BaseApp):

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    # self.listen_event(self._handle_message, 'telegram_sent')
    self.listen_event(self._incoming_text, 'telegram_text')
    self.listen_event(self._incoming_command, 'telegram_command')


  def _handle_message(self, event_name, data, kwargs):
    # Called when telegram message sent
    self.log(f'_handle_message() called: {event_name}, {data}, {kwargs}')


  def _incoming_command(self, event_name, data, kwargs):
    # Command receiving from chat (Starts with '/')
    self.log(f'_incoming_message() called: {event_name}, {data}, {kwargs}')


  def _incoming_text(self, event_name, data, kwargs):
    # Text receiving from chat (All other message that don't start with '/')
    self.log(f'_incoming_message() called: {event_name}, {data}, {kwargs}')

    chat_id = data.get('chat_id', 0)
    if chat_id in REVERSE_CHATS:    
      self._reporting_text_processing(event_name, data, kwargs)


  def _reporting_text_processing(self, event_name, data, kwargs):
    """ Handle bug reports and feature requests here """
    msg = chat_id = data.get('text', 'Unknown Telegram Message...')
    self._logger.log(f'Report text processing recieved a message: {msg}')

    # Save feature requests
    if msg.lower().startswith(FEATURE_REQUEST_TEXT_KEY.lower()):
      self._save_request_to_log(FEATURE_REQUEST_TEXT_KEY, FEATURE_REQUEST_FILE, msg, data['from_first'])

    # Save bug reports
    if msg.lower().startswith(BUG_REPORT_TEXT_KEY.lower()):
      self._save_request_to_log(BUG_REPORT_TEXT_KEY, BUG_REPORT_FILE, msg, data['from_first'])


  def _save_request_to_log(self, request_key, path, msg, user):
    """ Save a Feature/Bug request to file for future use

    request key: The key that indicated they type of requests in the user message
    path: Path to log file
    msg: The user telegram message
    user: User who send request
    """
    idx = len(request_key.split(' '))
    msg = msg.split(' ', idx)[idx] # Remove the request key (this method ensures a ":" is also removed)
    log_msg = f'{self.dt_str} {user}: {msg}'
    path = self.utils.ad_path(path)
    with open(self.utils.ad_path(path), 'a') as f:
      f.write(f'\n{log_msg}\n')
    self._logger.log(f'Saving message to {path}: "{msg}"')


  def map_chat_id_list(self, target):
    """ Convert chat alias to chat ID's """
    if not isinstance(target, list):
      target = [target]
    res = [CHATS[v.lower()] for v in target if v.lower() in CHATS]

    # Debugging output to notify me when there is an invalid target provided
    if len(res) != len(target):
      self._logger.log(f'Invalid target in the given list: {target}', level='WARNING')
    return res

  
  def telegram_notify(self, msg, target=[], title='', disable_notification=False, tag=''):
    """
    Send a telegram notification to a specific target

    param target: Group or user ID (list), Default: Logging group
    param title: Notification title (string), Default: No title
    param disable_notification: Silence the notification, Default: False (Makes a sound)
    param tag: Tag for sent message. (not sure if this is useful other then to identify the message in the event callback if needed), Default: No tag
    """
    data = {'message': msg}
    data['target'] = self.map_chat_id_list(target)
    data['title'] = title
    data['message_tag'] = tag

    t = [REVERSE_CHATS.get(target) for target in data['target']]
    self._logger.log(f'Sending telegram message to {t}: {data}')
    self.call_service('telegram_bot/send_message', **data)


  def test(self, entity, attributes, old, new, kwargs):
    self._logger.log(f'Testing telegram Module: ')

    # targets = ['status', 'alarm']
    targets = 'reporting'
    # targets = 'alex'
    self.telegram_notify('Test message from Appdaemon 5!', title='Telegram Testing!', target=targets, disable_notification=True, tag='this-message-is-tagged')





