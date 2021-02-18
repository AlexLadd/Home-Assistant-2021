
"""
  App for scene operations in HA
  Perform tasks such as:
    - taking light snapshots and outputing a scene
    - creating a new scene
    - reloading scenes in HA
    - watching the scene folder for changes and reloading
"""

from base_app import BaseApp 
import json
import yaml
import itertools
import os
import random

from file_watchdog import FileWatchdog

# TODO:
#   - Fix looping through all lights (around line 80-85 - LIGHT variable not longer accessable)

SCENES_DIRECTORY = 'scenes/'
SCENES_SNAPSHOT_DIRECTORY = 'scenes/snapshots/'
SCENES_AUTOMATED_DIRECTORY = 'scenes/automated/'


class Scenes(BaseApp):

  def setup(self):
    # self.listen_state(self.test,'input_boolean.ad_testing_1')

    self.observer = None
    # self.scene_handler = None

    # Add a file listen for the holiday/season config file
    self.scene_file_watchdog = FileWatchdog(self, self.utils.ha_path(SCENES_DIRECTORY), '*.yaml', single_file=False, debug_level='NOTSET',
                                              track_modified=True, track_created=True, track_deleted=True)


  def on_watchdog_file_update(self, file_name, event_type):
    """ A scene file was updated - This is called from the watchdog file listener """
    self._logger.log('A scene data file ("{}") was "{}", reloading and syncing HA scenes now.'.format(file_name, event_type), level='DEBUG')
    self.reload_scenes(None)


  def _save_scene(self, scene_name, scene_dict, folder=SCENES_SNAPSHOT_DIRECTORY):
    """ Save the given scene to the scenes directory """
    # Prepare string for yaml file (add '- ' to start and 2 spaces before every other new line)
    # Prevent anchors from being used in the output (references to objects and not the actual values)
    self.scene_file_watchdog.block()
    yaml.Dumper.ignore_aliases = lambda *args : True 
    res = yaml.dump(scene_dict, default_flow_style=False, sort_keys=False)
    res = '- ' + res.replace('\n', '\n  ')
    scene_name = scene_name.replace('scene.', '')
    file_path = self.utils.ha_path(folder + scene_name + '.yaml')
    with open(file_path, 'w') as f:
      f.write(str(res))
    self.run_in(lambda *_: self.scene_file_watchdog.unblock(), 5)


  def scene_snapshot(self, scene_name=None, include_lights=[], exclude_lights=[], reload_scenes=False):
    """ Take a snapshot of lights and save in the scenes snapshot folder 
    
    param scene_name: The desired name of the scene (Default: current datetime)
    param include_lights: The light entity ids to include as a list (Only include or exclude, not both)
    param exclude_lights: The light entity ids to exclude as a list
    param reload_scenes: Reload new scene snapshot after created
    """
    if all([include_lights, exclude_lights]):
      self._logger.log('Only one of include_lights or exclude_lights can be specified.', level='WARNING')
      return

    if not scene_name:
      scene_name = str(self.datetime().replace(microsecond=0)).replace('.', '-').replace(':', '-').replace(' ', '_')
    else:
      scene_name = scene_name.replace(' ', '_')

    friendly_name = scene_name.replace('_', ' ').title()
    output = { 'name':friendly_name, 'entities':{} }

    # for lt in LIGHTS:
    for lt in all_lights:
      entity_id = lt.value
      if include_lights and (entity_id not in include_lights and lt.name not in include_lights):
        continue
      elif exclude_lights and (entity_id in exclude_lights or lt.name in exclude_lights):
        continue

      light_info = self.get_state(entity_id, attribute='all')
      state = light_info.get('state', 'unknown')
      
      light_state = {}
      if state == 'off':
        light_state['state'] = 'off'
      elif state == 'on':
        attrs = light_info.get('attributes', {})

        light_state['state'] = 'on'

        brightness = attrs.get('brightness', None)
        if brightness:
          light_state['brightness'] = brightness

        colour_temp = attrs.get('color_temp', None)
        if colour_temp:
          light_state['color_temp'] = colour_temp
        else:
          rgb = attrs.get('rgb_color', None)
          if rgb:
            light_state['rgb_color'] = rgb

      if 'state' in light_state:
        output['entities'].update( { entity_id:light_state } )

    self._save_scene(scene_name, output, folder=SCENES_SNAPSHOT_DIRECTORY)
    if reload_scenes:
      self._logger.log('Reloading scenes in HA as requested.', level='INFO')
      self.reload_scenes('scene.' + scene_name)


  def create_scene(self, scene_name, lights, brightness, colours, transition=1, overwrite=False):
    """ Create a new scene and save it to the scenes folder
    param scene_name: The name to use for this scene 
    param lights: Lights that will be ON for this scene
    param brightness: The percent brightness of the lights
    param colours: An array of rgb colours to use for this scene
    param overwrite: recreate this scene even if it exists
    """
    scene_name = scene_name.lower().replace(' ', '_').replace('scene.', '').replace('.yaml', '')
    proper_scene_name = 'scene.' + scene_name.lower()
    file_path = self.utils.ha_path(SCENES_AUTOMATED_DIRECTORY + scene_name + '.yaml')
    if not overwrite and os.path.isfile(file_path):
      # Make sure scene is loaded
      if not self.entity_exists(proper_scene_name):
        self._logger.log(f'Scene {proper_scene_name} exists in the scenes folder but not in HA, attempting to reload now.')
        self.reload_scenes(proper_scene_name)
      return proper_scene_name

    # Create dictionary map of light entities -> light states
    friendly_name = scene_name.replace('_', ' ').title()
    output = { 'name':friendly_name, 'entities':{} }
    random.shuffle(colours)
    for res in zip(itertools.cycle(colours), lights):
      entity_state = {
        'state':'on',
        'rgb_color':res[0],
        'brightness':int((brightness*255)/100),
      }
      if res[1].startswith('light.'):
        entity_state['transition'] = transition
      output['entities'].update( { res[1]:entity_state } )

    self._save_scene(scene_name, output, folder=SCENES_AUTOMATED_DIRECTORY)
    self.reload_scenes(proper_scene_name)

    self._logger.log(f'Created a scene called {scene_name} ({proper_scene_name}).', level='DEBUG')
    return proper_scene_name


  def reload_scenes(self, proper_scene_name=None):
    """ Reload HA scene and verify the desired scene was found """
    self.call_service('scene/reload')
    if proper_scene_name:
      self.run_in(self._on_post_scene_reload, 2, proper_scene_name=proper_scene_name)


  def _on_post_scene_reload(self, kwargs):
    """ Verify scene was correctly loading into HA """
    proper_scene_name = kwargs.get('proper_scene_name', 'None specified')
    try:
      if self.get_state(proper_scene_name):
      # if self.entity_exists(proper_scene_name):
        self._logger.log('Successfully created a new scene ({}) and reloaded HA scenes.'.format(proper_scene_name), level='INFO')
      else:
        self._logger.log('Failed to reload new scene ({}) into HA.'.format(proper_scene_name), level='WARNING')
    except TypeError:
      self._logger.log('Error trying to get state for scene ({}) in HA.'.format(proper_scene_name), level='WARNING')


  def terminate(self):
    # Stop the watchdog thread
    self.scene_file_watchdog.terminate()


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log('Testing Scene Module: ')

