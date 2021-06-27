
"""
Rockwood Garbage Collection Reminder App

TODO:
- verify week email updates every sunday correctly
"""

from base_app import BaseApp
import datetime

# SMTP LIBRARIES
import smtplib
import time
import imaplib
import email
import traceback 
from bs4 import BeautifulSoup


SMTP_SERVER = "imap.gmail.com" 
SMTP_PORT = 993

EMAIL_CHECK_DAY = 6
EMAIL_CHECK_HOUR = 10
EMAIL_CHECK_MINUTE = 30
EMAIL_CHECK_FREQUENCY = 7*24*60

HA_SENSOR = 'sensor.ha_rockwood_garbage'


class Garbage(BaseApp):
  
  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')
    self.notifier = self.get_app('notifier')
    self.update_sensor(None)

    if self.datetime().weekday() == EMAIL_CHECK_DAY and self.datetime().hour <EMAIL_CHECK_HOUR and self.datetime().minute < EMAIL_CHECK_MINUTE:
      # Currently sunday before the check time
      dt_notify = self.datetime().replace(hour=EMAIL_CHECK_HOUR, minute=EMAIL_CHECK_MINUTE)
    else:
      # Schedule for next sunday at 10:30
      dt_notify = self.utils.next_weekday(self.datetime(), EMAIL_CHECK_DAY).replace(hour=EMAIL_CHECK_HOUR, minute=EMAIL_CHECK_MINUTE) 

    self.handle_weekly_check = self.run_every(self.read_email_from_gmail, dt_notify, EMAIL_CHECK_FREQUENCY)
    # self._logger.log(f'Next Recycling Remind Email Check: {dt_notify}')


  def update_sensor(self, kwargs):
    """ Update the HA garbage sensor """
    attrs = {
      'friendly_name': 'Rockwood Garbage Schedule',
      'next_yard_waste': 'unknown'
    }

    res = self.read_email_from_gmail()
    for d, items in res.items():
      if 'Yard Waste' in items:
        attrs['next_yard_waste'] = d 
      else:
        attrs['date'] = d 
        attrs['items'] = items

    self.set_state(HA_SENSOR, state='on', attributes=attrs)
    self._logger.log(f'Updates the Rockwood garbage sensor using: {res}. Sensor result: {self.get_state(HA_SENSOR, attribute="all")}')    


  def read_email_from_gmail(self):
    """ Check email for Recycling reminder and parse info """
    # Login to email account
    mail = imaplib.IMAP4_SSL(SMTP_SERVER)
    mail.login(self.args['gmail_account'], self.args['gmail_password'])
    mail.select('inbox')

    data = mail.search(None, 'ALL')
    mail_ids = data[1]
    id_list = mail_ids[0].split()   
    first_email_id = int(id_list[0])
    latest_email_id = int(id_list[-1])

    # Parse all emails until we find first recycling reminder
    for i in range(latest_email_id, first_email_id, -1):
      parsed_emails = self.check_email_for_garbage_schedule(mail.fetch(str(i), '(RFC822)' ))
      for split_info in parsed_emails:
        res = self.parse_raw_garbage_list(split_info)
        if len(res) > 0:
          # Save Most recent recycling email and stop searching...
          self._logger.log(f'[ID: {i}] All tasks {res}')
          return res


  def check_email_for_garbage_schedule(self, email_list):
    """ Check if given email(s) is the recycling reminder 

    Returns relavent data from email(s) if one is found """
    results = []
    for response_part in email_list:
      arr = response_part[0]
      split_info = []
      if isinstance(arr, tuple):
        msg = email.message_from_string(str(arr[1],'utf-8'))
        email_subject = msg['subject']
        email_from = msg['from']
        if email_subject is not None and 'Recycle Coach Weekly Reminder' in email_subject:
          # self._logger.log(f'Found garbage email: {email_subject}, msg: {msg}')

          msg_as_str = arr[1].decode('utf-8')
          start_key = 'This is a waste and recycling reminder'
          end_key = '*Know any other committed recyclers?*'
          start_loc = msg_as_str.find(start_key)
          end_loc = msg_as_str.find(end_key)
          key_info = msg_as_str[start_loc+len(start_key):end_loc].replace('\r', '').strip()
          split_info = key_info.split('\n')
          results.append(split_info)
          self._logger.log(f'Split info: {split_info}')
    return results
    

  def parse_raw_garbage_list(self, email_info):
    """ Parse the stripped down email information for which days and what needs to be done this week 
    
    Returns a dictionary of a DT object -> list of items to put to curb"""
    tasks_this_week = {}
    dt_object = None
    for info in email_info:
      if info == '':
        continue

      # Date is the start of a new location - make sure it isn't a different location - Example: Friday, June 25 07:00 AM 2021
      contains_date = self.utils.string_contains_date(info)
      if contains_date != '' and ('HHW Month' not in info or 'HHW Month' in info and 'Rockwood' in info):
        dt_str = self.utils.string_contains_date(info)
        dt_object = datetime.datetime.strptime(dt_str.strip() + ' ' + str(self.datetime().year), '%A, %B %d %I:%M %p %Y')
        idx = info.find(dt_str) + len(dt_str)
        tasks_this_week[dt_object] = tasks_this_week.get(dt_object, []) + [info[idx:].strip()]
      elif contains_date != '' and 'HHW Month' in info:
        self._logger.log(f'Discarding: {info}')
      else:
        key = '07:00 AM '
        idx = info.find(key) + len(key)
        tasks_this_week[dt_object] = tasks_this_week.get(dt_object, []) + [info[idx:].strip()]

    return tasks_this_week

 
  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing Garbage Module: ')
    # self.read_email_from_gmail()
    self.update_sensor(None)

