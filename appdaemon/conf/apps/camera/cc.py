
"""
Master Camera App

TODO:
  - Only remove pics/vids older than specific number of days? (incase we get lots of photos per day)
  - Consider doing the cleanup once per day? or periodically?
"""

from base_app import BaseApp 
import datetime
import os, errno
import copy
import math
from glob import glob
import re
import requests
from utils import ha_path, ad_path, html5_notify_path
import imageio
from shutil import copyfile, copytree
import voluptuous as vol

import utils_validation
from const import CONF_FRIENDLY_NAME, CONF_ALIASES, CONF_ENTITY_ID


NOTIFY_TARGET = ['status']
NOTIFY_TITLE = 'Cameras'

BASE_URL = '{}://{}:{}/cgi-bin/CGIProxy.fcgi?usr={}&pwd={}&{}'

# Garage snapshot config info
NUMBER_DAILY_GARAGE_SNAPSHOTS = 5
DAILY_GARAGE_SNAPSHOP_INTERVAL = 5*60

CONF_START_KEY = 'settings'
CONF_USERNAME = 'username'
CONF_PASSWORD = 'password'
CONF_PORT = 'port'
CONF_HOST = 'host'
CONF_VIDEO_FOLDER = 'video_folder'
CONF_PICTURE_FOLDER = 'picture_folder'
CONF_LOCATION = 'location'
CONF_USE_MOTION = 'use_motion'
CONF_DEFAULT_PRESET = 'default_preset'
CONF_DEFAULTS = 'defaults'

# Camera Default Settings
DEFAULTS_SCHEMA = vol.Schema(
  {
    vol.Optional(CONF_DEFAULT_PRESET, default=''): str,
  }
)

# Master camera schema
CAMERA_SCHEMA = {
  CONF_START_KEY: vol.Schema(
    {str: vol.Schema(
        {
          vol.Required(CONF_ENTITY_ID): utils_validation.entity_id,
          vol.Required(CONF_USERNAME): str,
          vol.Required(CONF_PASSWORD): str,
          vol.Required(CONF_HOST): utils_validation.ensure_ip_address,
          vol.Required(CONF_PORT, default=88): int,
          vol.Required(CONF_LOCATION): str,

          vol.Optional(CONF_VIDEO_FOLDER): utils_validation.ensure_abs_path,
          vol.Optional(CONF_PICTURE_FOLDER): utils_validation.ensure_abs_path,
          vol.Optional(CONF_USE_MOTION, default=False): bool,
          vol.Optional(CONF_DEFAULTS): DEFAULTS_SCHEMA,
        }
      ),
    })
  }


class CameraController(BaseApp):

  APP_SCHEMA = BaseApp.APP_SCHEMA.extend(CAMERA_SCHEMA)

  def setup(self):
    self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.mp = self.get_app('media_players')
    self.notifier = self.get_app('notifier')
    self.presence = self.get_app('presence')
    self.tv = self.get_app('living_room_tv')

    self.cameras = {}
    self.taking_snapshot = {}
    self.taking_recording = {}
    self.casting = {}

    self.run_in(lambda *_: self._setup_cameras(self.cfg), 0.2)
    self.run_daily(self._daily_garage_snapshot, "11:00:00")


  def _setup_cameras(self, config):
    """ Setup all cameras using settings app config """
    self._logger.log(f'Setting up cameras now...')
    cfg = copy.deepcopy(config[CONF_START_KEY])

    for c in self.cameras.values():
      c.cleanup()
    self.cameras = {}

    for room, settings in cfg.items():
      self.cameras[settings['entity_id']] = CameraEntity(self, settings)

    self._logger.log(f'Cameras setup: {self.cameras}')


  def command_url(self, camera):
    camera = self.cameras[camera]
    protocol_identifier = 'https' if camera.port == '443' else 'http'
    return BASE_URL.format(protocol_identifier, camera.CONF_HOST, camera.CONF_PORT, camera.CONF_USERNAME, camera.CONF_PASSWORD, '{}')


  def preset_url(self, camera):
    """ Camera preset URL with the scene name as an option [usage: preset_url.format(my_scene_name)] """
    command = 'cmd=ptzGotoPresetPoint&name={}'
    return self.command_url(camera).format(command)


  def default_preset_url(self, camera):
    """ Default camera preset URL [Return None if no default preset] """
    if not self.cameras[camera].default_preset:
      self._logger.log(f'No default preset for {camera} camera.', level='WARNING')
      return None
    return self.preset_url(camera).format(self.cameras[camera].default_preset)


  def set_time_url_template(self, camera):
    """ Camera set time URL with the Y/M/D & H/M/S as options - 24 Hour time format [usage: time_url.format(Y,M,D,H,M,S)] """
    command = 'cmd=setSystemTime&timeSource=1&ntpServer=&dateFormat=0&timeFormat=1&timeZone=0&isDst=0&dst=0&year={}&mon={}&day={}&hour={}&minute={}&sec={}'
    return self.command_url(camera).format(command)


  def set_current_time_url(self, camera):
    """ Return the url with the currently time embedded """
    dt = datetime.datetime.now()
    return self.set_time_url_template(camera).format(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


  def _get_camera_obj(self, camera):
    """ Get the camera object for given camera """
    return self.cameras[camera]


  def map_cameras(self, camera):
    """ Map common camera name to camera entity id """
    if camera in self.cameras:
      # This is already an entity id
      return camera

    for c_name, c_obj in self.cameras.items():
      if c_obj.entity_id == camera.lower().replace(' ', '_'):
        return c_name
      if c_obj.entity_id == camera.lower().replace('_', ' '):
        return c_name
      if c_obj.entity_id.split('.')[1] == camera.lower().replace('_', ' '):
        return c_name
      if c_obj.entity_id.split('.')[1] == camera.lower().replace(' ', '_'):
        return c_name
      if c_obj.location.lower() == camera.lower().replace(' ', '_'):
        return c_name
      if c_obj.location.lower() == camera.lower().replace('_', ' '):
        return c_name

    return camera


  def set_camera_dt(self, camera, dt=None):
    """ Set cameras time [Defaults to current datetime] """
    camera = self.map_cameras(camera)

    url = None
    if dt is None:
      url = self.set_current_time_url(camera)
    else:
      url = self.set_time_url_template(camera)
      url = url.format(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    if not url:
      self._logger.log('Please specify a camera ({}) that exists.'.format(camera), level='WARNING')
      return False

    try:
      response = requests.get(url)
      if response.status_code != 200:
        return False
    except Exception as e:
      self._logger.log('Exception setting {} camera datetime ({}): {}.'.format(camera, dt, e), level='WARNING')
      return False
    self._logger.log('Set {} camera time to {}.'.format(camera, (dt if dt else 'current time')), level='INFO')
    return True
          

  def set_camera_preset(self, camera, preset='default'):
    """ Set camera to given preset location [Using preset='default' will try to set to default preset for that camera] """
    camera = self.map_cameras(camera)

    url = None
    if preset == 'default':
      url = self.default_preset_url(camera)
    else:
      url = self.preset_url(camera)
      url = url.format(preset)

    if not url:
      self._logger.log('Please specify a camera ({}) or preset ({}) that exists.'.format(camera, preset), 'WARNING')
      return False

    try:
      response = requests.get(url)
      if response.status_code != 200:
        return False
    except Exception as e:
      self._logger.log('Exception setting {} camera preset ({}): {}.'.format(camera, preset, e), level='WARNING')
      return False
    self._logger.log('Set {} camera to {} preset position.'.format(camera, preset), level='INFO')
    return True


  def cast_to_tv(self, camera, tv):
    """ Cast a live feed of the camera to a TV """
    self._logger.log('Casting camera ("{}") to TV ("{}").'.format(camera, tv), level='INFO')
    camera = self.map_cameras(camera)
    if not self.get_state(camera):
      self._logger.log('No camera ("{}") found in HA.'.format(camera), level='ERROR')
      return

    if tv != 'living_room_tv':
      self._logger.log(f'The only TV currently connected to HA is the living room TV.')
      return 

    if tv not in self.casting:
      self.casting[tv] = False

    if not self.casting[tv]:
      self.casting[tv] = True
      self.call_service('camera/play_stream', entity_id=camera, media_player=tv)


  def stop_casting(self, tv):
    """ Stop casting of particular TV - This must be called after starting the cast """
    self._logger.log('Stopping Cast to TV ("{}").'.format(tv), level='INFO')
    self.casting[tv] = False
    self.call_service('media_player/media_stop', entity_id=tv)


  def record(self, camera, duration=30, lookback=10, notify=False):
    """ Top level call - prevent calling thread from being tied up using callbacks """
    self.run_in(lambda *_: self.record_execute(camera, duration, lookback, notify), 0)


  def record_execute(self, camera, duration=30, lookback=10, notify=False):
    """
    Core record call
    param duration: Length of video from 'now'
    param lookback: How much time in past to use
    param notify: Notify with the recording after the recording is finished
    """
    camera = self.map_cameras(camera)
    if not self.get_state(camera):
      self._logger.log('No camera ("{}") found in HA.'.format(camera), level='ERROR')
      return

    if camera not in self.taking_recording:
      self.taking_recording[camera] = False

    if self.taking_snapshot[camera] or self.taking_recording[camera]:
      self._logger.log('A recording is already being taken from "{}".'.format(camera), level='WARNING')
      self._logger.log(f'[{camera}] self.taking_snapshot: {self.taking_snapshot[camera]} self.taking_recording: {self.taking_recording[camera]}', level='DEBUG')
    else:
      self.taking_recording[camera] = True
      self._get_camera_obj(camera).record(duration, lookback, notify)
      self._logger.log(f'A recording is being taken from "{camera}" with duration and lookback of {duration} and {lookback}.', level='INFO')
      self.run_in(lambda *_: self._release_video_callback(camera), duration + lookback + 60)


  def _release_video_callback(self, camera):
    """ Stop 'blocking' video recording on a given camera """
    self.taking_recording[camera] = False


  def snapshot(self, camera, repeat=1, interval=1, notify=False, create_gif=False):
    """ Top level call - prevent calling thread from being tied up using callbacks """
    self.run_in(lambda *_: self.snapshot_execute(camera, repeat, interval, notify, create_gif), 0)


  def snapshot_execute(self, camera, repeat=1, interval=1, notify=False, create_gif=False):
    """
    Core snapshot method
    param repeat: How many snapshots to take
    param interval: Number of seconds between each interval
    param notify: Whether to notify after taking snapshots
    """
    camera = self.map_cameras(camera)
    if not self.get_state(camera):
      self._logger.log('No camera ("{}") found in HA.'.format(camera), level='ERROR')
      return

    if camera not in self.taking_snapshot:
      self.taking_snapshot[camera] = False

    if self.taking_snapshot[camera] or self.taking_recording[camera]:
      self._logger.log(f'Trying to take a snapshot but one is already being taken: {camera}.', level='WARNING')
      self._logger.log(f'[{camera}] self.taking_snapshot: {self.taking_snapshot[camera]} self.taking_recording: {self.taking_recording[camera]}', level='DEBUG')
    else:
      self.taking_snapshot[camera] = True
      self._get_camera_obj(camera).snapshot(repeat, interval, notify=notify, create_gif=create_gif)
      self._logger.log('Taking {} snapshot(s) from "{}".'.format(repeat, camera), level='INFO')
      self.run_in(lambda *_: self._release_snapshot_callback(camera), repeat * interval + 10)


  def _release_snapshot_callback(self, camera):
    """ Stop 'blocking' snapshots on a given camera """
    self.taking_snapshot[camera] = False


  def _daily_garage_snapshot(self, kwargs=None):
    snap_num = kwargs.get('number', 1)
    self._logger.log(f'Taking daily garage snapshot.', level='INFO')
    self.snapshot('carport', repeat=1, notify=False, create_gif=False)

    if snap_num >= NUMBER_DAILY_GARAGE_SNAPSHOTS:
      self.run_in(self._daily_garage_snapshot, DAILY_GARAGE_SNAPSHOP_INTERVAL, number=snap_num+1)


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing Camera Module: ')
    # self.record('front_entrance', 30, 10, notify=True)
    # self.snapshot('carport', repeat=1, notify=True, create_gif=False)
    # self.set_camera_dt('front_entrance', self.datetime())

    # self._logger.log(f'map carport: {self.map_cameras("carport")}')


  def terminate(self):
    pass



SNAPSHOT_CLEANUP_DELAY_TIME = 1*60
# VIDEO_TIME = 2*60
# CLEANUP_DELAY_TIME = 60

CLEANUP_ENABLE = False

# Max pics/videos per camera
MAX_PICTURES = 3000
MAX_VIDEOS = 25

class CameraEntity:

  def __init__(self, app, config={}):
    """
    param app: AD app reference
    param config: Camera configuration settings
    """
    self.app = app
    self.attrs = {**config}
    self.original_attrs = {**config}
    self.camera = self.entity_id
    self._logger = app._logger
    self.notifier = app.notifier

    self.camera_name = self.entity_id.split('.')[-1]
    self.handle_snapshot = None
    self.handle_recording = None
    self._event_handles = []

    self.name_pattern = self.camera_name + '_{}.{}'
    self.snapshot_path = self.base_picture_folder  + self.name_pattern.format({}, 'jpg')
    self.video_path = self.base_video_folder + self.name_pattern.format({}, 'mp4')
    self.notify_path = 'local/media/{}/' + self.camera_name + '_last_captured.{}' # .format(media_type, extention)

    # Create snapshot folders for both AD and HA
    fd = self.base_picture_folder
    if not os.path.exists(fd):
      os.makedirs(fd)
      self._logger.log('Created folder: {}'.format(fd), level='INFO')
    fd = self._ad_to_ha_camera_sensor_path(fd)
    if not os.path.exists(fd):
      os.makedirs(fd)
      self._logger.log('Created folder: {}'.format(fd), level='INFO')

    # Create video folders for both AD and HA
    fd = self.base_video_folder
    if not os.path.exists(fd):
      os.makedirs(fd)
      self._logger.log('Created folder: {}'.format(fd), level='INFO')
    fd = self._ad_to_ha_camera_sensor_path(fd)
    if not os.path.exists(fd):
      os.makedirs(fd)
      self._logger.log('Created folder: {}'.format(fd), level='INFO')


  @property
  def entity_id(self):
    return self.attrs['entity_id']

  @property
  def friendly_name(self):
    return self.attrs.get('friendly_name', self.entity_id.split('.')[1])

  @property
  def username(self):
    return self.attrs['username']

  @property
  def password(self):
    return self.attrs['password']

  @property
  def host(self):
    return self.attrs['host']

  @property
  def port(self):
    return self.attrs['port']

  @property
  def location(self):
    return self.attrs['location']

  @property
  def use_motion(self):
    return self.attrs['use_motion']

  @property
  def default_preset(self):
    return self.attrs['default_preset']

  @property
  def base_video_folder(self):
    return self.attrs['video_folder']

  @property
  def base_picture_folder(self):
    return self.attrs['picture_folder']


  def __str__(self):
    return self.camera_name.replace('_', ' ').capitalize() + ' camera'


  def _reset(self):
    """ Reset using the original config """
    self._logger.log('Resetting {} to its original settings.'.format(self), level='INFO')
    self.attrs = {**self._original_attrs}


  def _save_media(self, media_type='pictures'):
    """ 
      Make a copy of the picture/video folder for backup (Save as folder with same name and datetime appended to the end)
      media_type: Either pictures or videos
    """
    if media_type == 'pictures':
      folder = self.base_picture_folder
    elif media_type == 'videos':
      folder = self.base_video_folder

    if not os.path.exists(folder):
      self._logger.log('Trying to make a copy of a folder ({}) that does not exist.'.format(folder))

    new_folder = folder[:-1] + '_copy_' + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
      copytree(folder, new_folder)
      self._logger.log('Copying {} in folder {} to {}.'.format(media_type, folder, new_folder))
    except:
      self._logger.log('Cound not duplicate folder ({}) while trying to save {}.'.format(folder, media_type), level='ERROR')


  def _ad_to_ha_camera_sensor_path(self, folder):
    """ 
    Conver AD path into path where HA camera accesses files (/hass/www/...)
    Input: /conf/media/(pictues/videos)/camera_name/(pic/vid_name).xxx, Output: /hass/www/(pictues/videos)/camera_name/(pic/vid_name).xxx
    """
    return folder.replace('/hass/appdaemon/conf', '/hass/www')


  def _rename_if_exists(self, folder):
    """ If file exists, increment name by 1 second 
    
    param folder: Media file path that should be in HA format ('/hass/some/path/to/file.xxx') 
    """
    if os.path.exists(folder):
      dt = (datetime.datetime.now() + datetime.timedelta(seconds=1)).strftime("%Y%m%d-%H%M%S")
      # return '/'.join(folder.split('/')[:-1]) + '/' + self.name_pattern.format(dt, folder.split('.')[-1])
      r = re.split('\/|\.', folder)
      return '/'.join(r[:-2]) + '/' + self.name_pattern.format(dt, r[-1])
    return folder


  def snapshot(self, repeat=1, interval=1, notify=False, count=0, create_gif=False):
    """ 
    Take picture/repeating pictures 
    param repeat: The number of pictures to take
    param interval: The time between repeat pictures
    param count: Internal variable to keep track of how many snapshots have been taken
    param notify: Send HTML5 notify of picture after taken
    """
    repeat -= 1

    # Cancel the cleanup if it is queued up. It will happen after this batch
    if self.handle_snapshot:
      self.app.cancel_timer(self.handle_snapshot)
      self.handle_snapshot = None

    dt = datetime.datetime.now()
    path = ha_path(self.snapshot_path.format(dt.strftime("%Y%m%d-%H%M%S")), service_call_path=True)
    fn = self._rename_if_exists(path)

    try:
      self.app.call_service('camera/snapshot', entity_id=self.camera, filename=fn)
    except Exception as e:
      self.app._logger.log('Error taking HA snapshot using {} camera with params: filename={}. Error: {}' \
          .format(self.camera, fn, e), level='ERROR')
      return
    # self._logger.log('Snapshot was taken from "{}" and saved to {}.'.format(self.camera_name, fn), level='INFO')

    if repeat > 0:
      self.app.run_in(lambda *_: self.snapshot(repeat, interval, notify, count+1, create_gif), interval)
    elif repeat == 0:
      self.handle_snapshot = self.app.run_in(self._snapshot_finsished_callback, SNAPSHOT_CLEANUP_DELAY_TIME+20, media_type='pictures', count=count+1, notify=notify, create_gif=create_gif)


  def _snapshot_finsished_callback(self, kwargs):
    """ Preform any post snapshot cleanup and send notification if requested """
    self._cleanup_folder(kwargs['media_type'], kwargs['count'])
    self.handle_snapshot = None
    if kwargs['notify']:
      # self._logger.log('Sending snapshot notification to {} from {}.'.format(NOTIFY_TARGET, self))
      path = self.notify_path.format(kwargs['media_type'], 'jpg')
      # self.notifier.html5_notify(NOTIFY_TARGET, 'Click to see picture.', '{} Motion'.format(self), renotify=True, image_path=path)
      self.notifier.telegram_notify(f'Done taking pictures from {self} camera to: {path}.')
    if kwargs['create_gif']:
      self.create_gif()


  def record(self, duration=30, lookback=10, notify=False):
    """ Take recording """
    # Cancel the cleanup if it is queued up. It will happen after this video
    if self.handle_recording:
      self.app.cancel_timer(self.handle_recording)
      self.handle_recording = None

    dt = datetime.datetime.now()
    path = ha_path(self.video_path.format(dt.strftime("%Y%m%d-%H%M%S")), service_call_path=True)
    fn = self._rename_if_exists(path)

    try:
      self.app.call_service('camera/record', entity_id=self.camera, filename=fn, duration=duration, lookback=lookback)
    except Exception as e:
      self.app._logger.log('Error taking HA recording using "{}" camera with params: filename={}, duration={}, lookback={}. Error: {}' \
          .format(self.camera, fn, duration, lookback, e), level='ERROR')
      return
    # self._logger.log('Video recording taken from "{}" and saved to {} with a duration of {} seconds.'.format(self.camera_name, fn, duration+lookback), level='INFO')
    self.handle_recording = self.app.run_in(self._recording_finished_callback, (duration+lookback+60), media_type='videos', notify=notify)


  def _recording_finished_callback(self, kwargs):
    """ Preform any post video cleanup and send notification if requested """
    self._cleanup_folder(kwargs['media_type'])
    self.handle_recording = None
    if kwargs['notify']:
      # self._logger.log('Sending snapshot notification to {} from {}, url: {}.'.format(NOTIFY_TARGET, self))
      path = self.notify_path.format(kwargs['media_type'], 'mp4')
      self.notifier.html5_notify(NOTIFY_TARGET, 'Click to see video.', '{} Motion'.format(self), renotify=True, image_path=path)
      self.notifier.telegram_notify(f'Done taking video from {self} camera to: {path}.')


  def _cleanup_folder(self, media_type, lookback=1):
    """ 
      Update latest picture/video for HA camera entity and remove files if exceeding MAX 
      media_type: Either pictures or videos
      lookback: Number of files back to use as latest pic/video
    """
    if media_type == 'pictures':
      folder = self.base_picture_folder
      extention = 'jpg'
      limit = MAX_PICTURES
    elif media_type == 'videos':
      folder = self.base_video_folder
      extention = 'mp4'
      limit = MAX_VIDEOS

    search_pattern = self.name_pattern.format('*', extention)
    last_taken_file_name = self.name_pattern.format('last_captured', extention)

    media_list = sorted(glob(os.path.join(folder, search_pattern)))

    if media_list:
      last_taken_path = os.path.join(folder, last_taken_file_name)

      if last_taken_path in media_list:
        # Remove the *_last_captured.jpg from the list if it exists
        media_list.remove(last_taken_path)
        try:
          os.remove(last_taken_path)
        except:
          self._logger.log('Could not remove file: {}.'.format(last_taken_path), level='WARNING')

      lb = max(math.ceil(lookback/2), 1)
      lf = media_list[-lb]
      # lf = media_list[-lookback] # New motion sensor is much faster and the first pictures in a grouping usually contain minimal 'action'
      try:
        copyfile(lf, last_taken_path) # Make copy in AD folder (not required once camera is switched over)
        copyfile(lf, self._ad_to_ha_camera_sensor_path(last_taken_path)) # Make copy for HA frontend camera to use
      except:
        self._logger.log('Cound not duplicate file: {}'.format(lf), level='ERROR')

      if CLEANUP_ENABLE:
        for f in media_list[:-limit]:
          os.remove(f)


  def create_gif(self, max_pics=30, min_seq_len=5, max_time_between_pics=6):
    """ Get sequences of pictures that were taken in close succession to each other 
    Picture format: front_entrance_20191124-201952.jpg
    param max_pics: Max number of pictures to consider in the folder
    param min_seq_len: Minimum number of pictures in sequence
    param max_time_between_pics: The max number of seconds between sequential pictures
    """
    folder = self.base_picture_folder
    search_pattern = self.name_pattern.format('*', 'jpg')
    path = os.path.join(folder, search_pattern)

    pictures = sorted(glob(path))[-max_pics:]
    results = [] # List of lists of similar dated pictures
    similar = [] 
    prev_dt = None
    for pic in pictures:
      try:
        # Example name pattern: front_entrance_20191108-203654.jpg
        date = pic.split('/')[-1].split('_')[-1].split('.')[0]
        dt = datetime.datetime.strptime(date, "%Y%m%d-%H%M%S")
      except: 
        # Simply discard files named differently
        continue

      if len(similar) == 0:
        # First item, nothing to compare to
        prev_dt = dt
        similar.append(pic)
        continue

      if prev_dt and dt - prev_dt < datetime.timedelta(seconds=max_time_between_pics):
        similar.append(pic)
      else:
        results.append(similar)
        similar = []
      prev_dt = dt

    if len(similar) > 0:
      results.append(similar)

    # Find the most recent sequence of pics >= than the min_seq_pics
    images = []
    for seq in reversed(results):
      if len(seq) >= min_seq_len:
        images = seq
        break

    if images:
      path = os.path.join(self.base_picture_folder, self.name_pattern.format('last_captured', 'gif'))
      self._logger.log('Creating a gif using {} pictures at {}.'.format(len(images), path), level='INFO')
      ims = []
      for i in images:
        ims.append(imageio.imread(i))
      imageio.mimsave(path, ims)
      try:
        copyfile(path, self._ad_to_ha_camera_sensor_path(path)) # Make copy for HA frontend camera to use
        self._logger.log('Copying from: {} to: {}.'.format(path, self._ad_to_ha_camera_sensor_path(path)), level='INFO')
      except:
        self._logger.log('Cound not duplicate file: {}'.format(path), level='ERROR')
    else:
      self._logger.log('No gif image sequence found, nothing will be created.')


  def cleanup(self):
    for h in self._event_handles:
      self.app.cancel_listen_event(h)
    self.app.cancel_timer(self.handle_recording)
    self.app.cancel_timer(self.handle_snapshot)
