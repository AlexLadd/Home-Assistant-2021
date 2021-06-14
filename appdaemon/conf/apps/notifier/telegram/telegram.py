"""
Telegram Application

Handles/Processes incoming/outgoing telegram messages
"""

from base_app import BaseApp

CHATS = {
  'alex': -414341807,
  'steph': -414341807,
  'logging': -469980278,
  'status': -414341807,
  'alarm': -489764741,
  'reporting': -574720532,
  # 'alex': 1514688713,
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

    self.listen_event(self._message_sent_callback, 'telegram_sent')
    self.listen_event(self._incoming_text, 'telegram_text')
    self.listen_event(self._incoming_command, 'telegram_command')
    self.listen_event(self._incoming_callback, 'telegram_callback')


  def _message_sent_callback(self, event_name, data, kwargs):
    """ Callback for a message sent - Will provide the message ID and can be linked to a message via the 'tag' """
    # self._logger.log(f'_message_sent_callback() called: {event_name}, data: {data}, kwargs: {kwargs}')

    tag = data.get('message_tag')
    chat_id = data.get('chat_id')
    message_id = data.get('message_id')
    # self._logger.log(f'Message sent to "{REVERSE_CHATS.get(chat_id)}" with the tag: "{tag}", message_id: "{message_id}"')


  def _incoming_callback(self, event_name, data, kwargs):
    # Called when associated callback called (when keyboard button pressed)
    self._logger.log(f'_incoming_callback() called: {event_name}, data: {data}, kwargs: {kwargs}')
    cmd = data.get('command')
    user = data.get('from_first')
    callback_id = data.get('id')
    msg = data.get('message', {}).get('text')
    self._logger.log(f'Received {event_name} from {user} with command {cmd}. Callback_id: {callback_id}, message: {msg}')

    msg = 'Answering this user button press'
    self._answer_callback_query(msg, callback_id, show_alert=True)


  def _incoming_command(self, event_name, data, kwargs):
    # Command receiving from chat (Starts with '/')
    self._logger.log(f'_incoming_message() called: {event_name}, {data}, {kwargs}')


  def _incoming_text(self, event_name, data, kwargs):
    # Text receiving from chat (All other message that don'target_name start with '/')
    self._logger.log(f'_incoming_message() called: {event_name}, {data}, {kwargs}')

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


  def _escape_markdown(self, msg):
      msg = msg.replace("`", "\\`")
      msg = msg.replace("*", "\\*")
      msg = msg.replace("_", "\\_")
      return msg


  def map_alias_to_chat_id(self, t):
    """ Convert chat alias to chat_id """
    return CHATS[t.lower()] if isinstance(t, str) and t.lower() in CHATS else t


  def map_chat_id_list(self, target):
    """ Convert chat alias to chat ID's """
    if not isinstance(target, list):
      target = [target]
    res = [CHATS[v.lower()] if isinstance(v, str) and v.lower() in CHATS else v for v in target]

    # Debugging output to notify me when there is an invalid target provided
    if len(res) != len(target):
      self._logger.log(f'Invalid target in the given list: {target}', level='WARNING')
    return res


  def _answer_callback_query(self, msg, cb_id, show_alert=True):
    """
    Replay to a button press from a user

    param msg: Message to send as a temporary popup
    param cb_id: ID of the callback query
    param show_alert: True if popup will stay until dismissed by user
    """
    data = {'message': msg}
    data['callback_query_id'] = cb_id
    data['show_alert'] = show_alert

    self.call_service('telegram_bot/answer_callback_query', **data)
    self._logger.log(f'Ansering telegram callback query with parameters: {data}', level='INFO')


  def telegram_delete_message(self, target, message_id='last'):
    """
    Remove a telegram message from a specific chat

    param target: Group or user ID (list)
    param message_id: Message that should be deleted, Default: Last message sent
    """
    if not isinstance(target, list):
      target = [target]
  
    data = {'message_id': message_id}
    for t in target:
      data['chat_id'] = self.map_alias_to_chat_id(t)
      self.call_service('telegram_bot/delete_message', **data)
      self._logger.log(f'Deleting telegram message with parameters: {data}', level='INFO')


  def telegram_edit_message(self, msg, target, title='', message_id='last', inline_keyboard=[]):
    """
    Edit a telegram message from a specific chat

    param msg: Message to send
    param target: Group or user ID (list)
    param title: Notification title (string), Default: No title
    param message_id: Message that should be deleted, Default: Last message sent
    param inline_keyboard: Buttons (keyboard) displayed for recipient
    """
    if not isinstance(target, list):
      target = [target]
    if len(msg) > 4000:
      self._logger.log(f'Cannot edit a message with a new message longer than 4000 characters: {len(msg)}. Message will be truncated. Message: {msg}.', level='WARNING')
      msg = msg[:4000]
  
    data = {'message_id': message_id}
    data['title'] = title
    data['message'] = self._escape_markdown(msg)
    data['inline_keyboard'] = inline_keyboard
    for t in target:
      data['chat_id'] = self.map_alias_to_chat_id(t)
      self.call_service('telegram_bot/edit_message', **data)
      self._logger.log(f'Editing telegram message with parameters: {data}', level='INFO')

  
  def telegram_edit_caption(self, caption, target, message_id='last', inline_keyboard=[]):
    """
    Remove a telegram caption from a specific chat - Caption is used in sending photos, video, docs, etc

    param caption: Message to send
    param target: Group or user ID (list)
    param message_id: Message that should be deleted, Default: Last message sent
    param inline_keyboard: Buttons (keyboard) displayed for recipient
    """
    if not isinstance(target, list):
      target = [target]
    if len(caption) > 4000:
      self._logger.log(f'Cannot edit a message with a new message longer than 4000 characters: {len(caption)}. Message will be truncated. Message: {caption}.', level='WARNING')
      caption = caption[:4000]
  
    data = {'message_id': message_id}
    data['caption'] = self._escape_markdown(caption)
    data['inline_keyboard'] = inline_keyboard
    for t in target:
      data['chat_id'] = self.map_alias_to_chat_id(t)
      self.call_service('telegram_bot/edit_caption', **data)
      self._logger.log(f'Editing telegram caption with parameters: {data}', level='INFO')

  
  def telegram_edit_keyboard(self, target, message_id='last', inline_keyboard=[]):
    """
    Remove a telegram caption from a specific chat - Caption is used in sending photos, video, docs, etc

    param target: Group or user ID (list)
    param message_id: Message that should be deleted, Default: Last message sent
    param inline_keyboard: Buttons (keyboard) displayed for recipient
    """
    if not isinstance(target, list):
      target = [target]
  
    data = {'message_id': message_id}
    data['inline_keyboard'] = inline_keyboard
    for t in target:
      data['chat_id'] = self.map_alias_to_chat_id(t)
      self.call_service('telegram_bot/edit_replymarkup', **data)
      self._logger.log(f'Editing telegram inline_keyboard with parameters: {data}', level='INFO')
  
  
  def telegram_notify(self, msg, target=[], title='', disable_notification=False, tag='', inline_keyboard=[]):
    """
    Send a telegram notification to a specific target

    param msg: Message to send
    param target: Group or user ID (list), Default: Logging group
    param title: Notification title (string), Default: No title
    param disable_notification: Silence the notification, Default: False (Makes a sound)
    param tag: Tag for sent message. (not sure if this is useful other then to identify the message in the event callback if needed), Default: No tag
    param inline_keyboard: Buttons (keyboard) displayed for recipient
    """
    data = {'message': self._escape_markdown(msg)}
    data['target'] = self.map_chat_id_list(target)
    data['title'] = f'{title} - Part 1' if title else ''
    data['message_tag'] = f'{tag}_1' if tag else ''
    # data['inline_keyboard'] = inline_keyboard
    target_name = [REVERSE_CHATS.get(target, target) for target in data['target']]

    # Break up long messages
    part = 1
    while len(msg) > 4096:
      data['message'] = self._escape_markdown(msg[:4000])
      self._logger.log(f'Length of message: {len(data["message"])}')
      self._logger.log(f'Sending telegram message to {target_name}: {data}')
      self.call_service('telegram_bot/send_message', **data)
      msg=msg[4000:]
      part += 1
      data['title'] = f'{title} - Part {part}' if title else ''
      data['message_tag'] = f'{tag}_{part}' if tag else ''

    # Send final message or a single message if smaller than 4000 characters
    data['message'] = self._escape_markdown(msg)
    self._logger.log(f'Sending telegram message to {target_name}: {data}')  
    data['inline_keyboard'] = inline_keyboard
    self.call_service('telegram_bot/send_message', **data)


  def test(self, entity, attributes, old, new, kwargs):
    self._logger.log(f'Testing telegram Module: ')

    # targets = 1514688713 
    targets = ['logging']
    # targets = 1507304452
    msg = f'Test message from Appdaemon {self.time()}!'
    ik = ['Task 1:/command1 1, Task 2:/command2 2', 'Task 3:/command3 3, Task 4:/command4 4']
    
    self.telegram_notify(msg, title='Telegram Testing!', target=targets, disable_notification=True, tag='this-message-is-tagged', inline_keyboard=ik)


    # self.telegram_delete_message('logging', 503)
    # self.telegram_delete_message('logging')

    # self.telegram_edit_message('This message was just edited', 'logging', 'Edited Message!')

    # ik = ['Edit 1:/command1 1, Edit 2:/command2 2', 'Edit 3:/command3 3, Edit 4:/command4 4']
    # self.telegram_edit_keyboard('logging', inline_keyboard=ik)
    
    





