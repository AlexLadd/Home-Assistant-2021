"""

TODO:
  - Add disable_state check for each speaker

"""


from base_app import BaseApp
import datetime
import voluptuous as vol

from const import CONF_ENTITY_ID, CONF_LOG_LEVEL, CONF_ALIASES, CONF_FRIENDLY_NAME
import utils_validation


CONF_START_KEY = 'speakers'
CONF_IS_GROUP = 'is_group'
CONF_CHILD_SPEAKERS = 'child_speakers'
CONF_DEFAULT_VOLUME = 'default_volume'
CONF_SPEAKER_DISABLE_STATES = 'speaker_disable_states'

CONF_DEFAULT_LOG_LEVEL = 'NOTSET'
CONF_DEFAULT_VOLUME_VALUE = 0.30

DEFAULT_VOLUME = 0.33


SPEAKER_SCHEMA = {
  CONF_START_KEY: vol.Schema(
    {str: 
      vol.Schema(
        {
          vol.Required(CONF_ENTITY_ID): utils_validation.entity_id,
          vol.Optional(CONF_FRIENDLY_NAME): str,
          vol.Optional(CONF_ALIASES): utils_validation.ensure_list,
          vol.Optional(CONF_LOG_LEVEL, default=CONF_DEFAULT_LOG_LEVEL): str,
          vol.Required(CONF_IS_GROUP, default=False): bool,
          vol.Optional(CONF_CHILD_SPEAKERS): utils_validation.ensure_list,
          vol.Required(CONF_DEFAULT_VOLUME, default=CONF_DEFAULT_VOLUME_VALUE): utils_validation.try_parse_float,
          vol.Optional(CONF_SPEAKER_DISABLE_STATES, default=[]): utils_validation.ensure_constraint_list,
        }
      ),
  })
}


class Speakers(BaseApp):

  APP_SCHEMA = BaseApp.APP_SCHEMA.extend(SPEAKER_SCHEMA)

  def setup(self):
    # self.listen_state(self.test, 'input_boolean.ad_testing_1')

    self.settings = self.get_app('settings')
    self.sleep = self.get_app('sleep')

    # Main config data
    self._speaker_data = {}
    self._process_cfg(self.cfg)


  def _process_cfg(self, config):
    """ Prep yaml data - Ensure we keep integrety of original data """
    import copy
    cfg = copy.deepcopy(config)

    for name, data in cfg[CONF_START_KEY].items():
      key = data[CONF_ENTITY_ID]
      self._speaker_data[key] = data 
      # Add the room name to aliases (add aliases if it doesnt exists)
      self._speaker_data[key].setdefault(CONF_ALIASES, []).append(name)
      # Set friendly name to room
      self._speaker_data[key].setdefault(CONF_FRIENDLY_NAME, name.replace('_', ' ').title())

  @property
  def all_speakers(self):
    """ Return a list of all speaker entity_id's """
    return self.all_speaker_no_groups + self.all_speaker_groups

  @property
  def all_speaker_no_groups(self):
    """ Return a list of all speaker entity_id's that are not part of a group """
    return [data[CONF_ENTITY_ID] for room, data in self._speaker_data.items() if not data[CONF_IS_GROUP]]

  @property
  def all_speaker_groups(self):
    """ Return a list of all speaker entity_id's that are part of a group """
    return [data[CONF_ENTITY_ID] for room, data in self._speaker_data.items() if data[CONF_IS_GROUP]]

  def is_group_speaker(self, speaker):
    """ True if speaker is a group """
    return self.get_speaker_data(speaker)[CONF_IS_GROUP]

  def get_speaker_data(self, speaker):
    """ Provide all config data for a media player """
    return self._speaker_data.get(self.map_speaker_to_entity(speaker), {})

  def default_volume(self, room):
    """ Return the default volume for a speaker in a given room/location """
    try:
      return self._speaker_data[self.map_speaker_to_entity(room)][CONF_DEFAULT_VOLUME]
    except KeyError:
      self._logger.log(f'Speaker does not exists: {room}', level='WARNING')
      return CONF_DEFAULT_VOLUME_VALUE


  def map_speaker_to_entity(self, media_player):
    """ Map common speaker name to entity_id """
    if isinstance(media_player, str) and media_player in self._speaker_data:
      return self._speaker_data[media_player][CONF_ENTITY_ID]
    else:
      for data in self._speaker_data.values():
        if media_player in data[CONF_ALIASES]:
          return data[CONF_ENTITY_ID]
    return media_player


  def map_tv(self, media_player):
    return 'Not implemented yet!'
  

  def current_volume(self, media_player):
    """ Return the current volume level of desired media player as a float """
    try:
      speaker = self.map_speaker_to_entity(media_player)
      vol = self.get_state(speaker, attribute='volume_level')
      return float(vol)
    except:
      self._logger.log(f'Failed to get current volume level for "{media_player}" speaker.', level='WARNING')
      return 0.0


  def is_on(self, device):
    return bool(self.get_state(device) == 'on')


  def is_playing(self, media_player):
    """ Check if media_player are currently playing
    param media_player: List of string or media_player(s) to check
    """
    if not isinstance(media_player, list):
      media_player = [media_player]
    media_players = [self.map_speaker_to_entity(s) for s in media_player]

    for mp in media_players:
      try:
        if self.get_state(mp) == 'playing':
          return True
      except Exception as e:
        self._logger.log('Media Player does not exists: {} (Error: {})'.format(m, e))
    return False



  def _idle_media_players(self, media_player=None):
    """ Return idle media players [Default: Check all Speakers that are not groups] """
    if media_player is None:
      media_player = self.all_speaker_no_groups
    
    mp = []
    for player in media_player:
      try:
        if self.get_state(player).lower() not in ['playing', 'unavailable', 'unkown']:
          mp.append(player)
      except Exception as e:
        self._logger.log('Media player does not exists in AD/HA: {} (Error: {})'.format(m, e))
    return mp


  def validate_media_players(self, media_player=None):
    """ Return a list of media_player(s) that exists in HA and are a valid speaker 
    
    param media_player: Media player(s) to check. Default: All speakers (no groups)
    """
    if media_player is None:
      media_player = self.all_speaker_no_groups
    if isinstance(media_player, str):
      media_player = [media_player]

    mp = []
    for m in media_player:
      try:
        if self.get_state(m) is not None:
          mp.append(m)
      except Exception as e:
        self._logger.log('Media player is not a valid media_player: {} (Error: {})'.format(m, e))
    return mp


  def get_group_speakers(self, group):
    """ Return child speakers of the groups as a list if they exists, otherwise, [] """
    if isinstance(group, str):
      group = [group]

    result = []
    for sp in group:
      data = self.get_speaker_data(sp)
      try:
        result = result + data.get(CONF_CHILD_SPEAKERS, [data[CONF_ENTITY_ID]])
      except KeyError:
        self._logger.log(f'Speaker does not exists: {sp} (group: {group})', level='WARNING')
        pass
    return list(set(result))


  def get_sanitized_speakers(self, speaker=None, speaker_override=False, use_groups=False):
    """ 
    Takes in speaker(s) as a string/list and maps speaker aliases to media_player(s)
    Returns available speakers (unless overridden) as a list
    Calling with no params returns all idle speakers
    Calling with speaker_override returns all speakers
    param speaker: Optional speaker to attempt to use if idle or everyone awake [or speaker_override forces its use]
    param speaker_override: Will use all speakers regardless of who is sleeping or if they're in use
    param use_groups: Will use speaker groups if possible
    """
    if speaker is not None: 
      if isinstance(speaker, str):
        speaker = [speaker]
      speaker = [self.map_speaker_to_entity(s) for s in speaker]

    mp = []

    if self.get_state(self.const.EMERGENCY_MODE_BOOLEAN) == 'on':
      if use_groups:
        mp = [self.map_speaker_to_entity('all')]
      else:
        mp = self.all_speaker_no_groups

    elif speaker and ((not self.is_playing(speaker) \
      and ((self.map_speaker_to_entity('master') in speaker and self.sleep.everyone_awake) \
      or self.map_speaker_to_entity('master') not in speaker)) or speaker_override):
        mp = speaker

    else:
      if speaker_override:
        if use_groups:
          mp = [self.map_speaker_to_entity('all')]
        else:
          mp = self.all_speaker_no_groups
      else:
        mp = self._idle_media_players()
        if not self.sleep.everyone_awake:
          if self.map_speaker_to_entity('master') in mp:
            mp.remove(self.map_speaker_to_entity('master'))
          if use_groups and set(mp) == set(self.map_speaker_to_entity('no_bedrooms')):
            mp = [self.map_speaker_to_entity('no_bedrooms')]

        if use_groups and set(mp) == set(self.all_speaker_no_groups):
          mp = [self.map_speaker_to_entity('all')]

    # Make sure the speakers are currently available
    mp = self.validate_media_players(mp)
    return mp


  def reset_volume(self):
    """ Set every speaker to their default volume """
    for speaker in self.all_speaker_no_groups:
      self.set_volume(speaker)


  def set_volume(self, media_player, volume=None):
    """ Set speaker volume
    param media_player: The speaker to set the volume for
    param volume: Desired volume [Default: Use the settings config default value]
    """
    if not media_player:
      self._logger.log(f'No media_player was supplied: {media_player}')
      return

    if isinstance(media_player, str):
      media_player = [media_player]
    media_player = [self.map_speaker_to_entity(s) for s in media_player]

    # Only individual speaker volumes can be set (not entire groups)
    group_speakers = self.get_group_speakers(media_player)
    if group_speakers:
      media_player = group_speakers

    if volume is not None:
      if volume > 100:
        volume = 100
      elif 1 < volume <= 100:
        volume = volume/100

    for mp in media_player:
      if not self.validate_media_players(mp):
        self._logger.log(f'Media player does not exist in HA: {mp}, the volume will not be adjusted.')
        continue

      # if self.get_state(self.const.EMERGENCY_MODE_BOOLEAN) == 'on':
      #   vol = 0.7
      if volume is not None:
        vol = volume
      elif self.sleep.someone_asleep and mp == self.map_speaker_to_entity('master'):
        vol = self.default_volume('asleep')
      elif mp == self.map_speaker_to_entity('master') and self.now_is_between(self.const.DEFAULT_ASLEEP, self.const.DEFAULT_WAKEUP):
        vol = self.default_volume('night')
      elif 'all' in mp or 'speakers' in mp:
        vol = self.default_volume('groups')
      else:
        vol = self.default_volume(mp)

      self._logger.log(f'{mp} set to {vol*100} percent volume', level='DEBUG')
      self.call_service('media_player/volume_set', entity_id=mp, volume_level=vol)


  def terminate(self):
    pass


  def test(self, entity, attribute, old, new, kwargs):
    res = self.get_sanitized_speakers()
    self._logger.log(f'Result: {res}')

    self.set_volume('master_bedroom', 0.51)

