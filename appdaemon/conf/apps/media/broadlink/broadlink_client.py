
"""
MOST OF THIS APP IS FROM ANOTHER COMMUNITY MEMBER
  -> No config validation
  -> Needs a refactor to clean things up and bring it in line semantically with other apps

Broadlink App. With this app, all Broadlinks on the same network can be used to control device
requirements:
- python 3.6 minimum
- pip3 install broadlink
apps.yaml parameters:
  - local_ip (optional, default None): The local IP of the system running AD. Only important in a docker container
  - broadlinks: (not optional): A dictionary definition of the name and mac address of each broadlink device
    - mac: (not optional) the mac address from the broadlink device
    - friendly_name (optional, default broadlink name)
    - entity_domain (optional, default sensor): The domain to be used when defining the entities to be created
    - service_domain (optional, default broadlink): The domain from the services
    - namespace (optional, default default): The namespace in which the entities and services are created
    - learn_time (optional, default 5): the time that AD listens for a data packet to return
    - update_frequence (optional, default 60): the frequency with which the temperature attribute or sensor will be updated
  - 
  - broadlink_app:
  -     class: BroadlinkApp
  -     module: broadlink_app
  -     broadlinks:
  -         living_room:
  -             mac: xx:xx:xx:xx:xx:xx
  -             namespace: hass
  -             learn_time: 20
  -             entity_domain: sensor
  -             service_domain: living_room
  -             friendly_name: Broadlink living room
  
available services:
  - setup_broadlink, returns True or False
  - learn (expects entity_id="broadlink_entity_id") returns True or False
  - check_data (expects entity_id="broadlink_entity_id") returns True or False
  - send_data (expects entity_id="broadlink_entity_id", data_packet="", protocol = "") returns True or False, data_packet can be a name you have set in the yaml or an actual data packet. protocol is optional
"""

from base_app import BaseApp
import broadlink
import re
import base64
import binascii
import struct
import datetime
import json
import yaml

from file_watchdog import FileWatchdog

# Path used for parsing new data from RM Plugin Lite
RAW_CODES_PATH = 'apps/media/broadlink/codes_raw.json'
RAW_CODES_PATH_RESULTS = 'apps/media/broadlink/code_results.yml'

# IR Codes for various devices (Production version for use)
DEVICE_CODE_FOLDER = 'apps/media/broadlink/'
DEVICE_CODE_FILE = 'code_results.yml'
# DEVICE_CODE_PATH = 'apps/media/broadlink/code_results.yml'
DEVICE_CODE_PATH = DEVICE_CODE_FOLDER + DEVICE_CODE_FILE


class BroadlinkClient(BaseApp):

  def setup(self): 
    # return
    self.listen_state(self.test,'input_boolean.ad_testing_1')

    self.debug_level = 'DEBUG'
    self.broadlinks = self.args["broadlinks"]     # Broadlink config yaml settings
    self.entities = {}                            # HASS entities
    self.broadlinkObjects = {}                    # Broadlink objects
    self._code_data = {}                          # IR Code data for various devices: device name -> { commands names -> HEX codes }

    # Listen for any RF/IF code file changes
    self.code_file_watchdog = FileWatchdog(self, self.utils.ad_path(DEVICE_CODE_FOLDER), DEVICE_CODE_FILE, debug_level='NOTSET')

    self.run_in(lambda *_: self._setup(), 1)

    # Convert json code data to yaml file
    # self._convert_json_codes_to_yaml(RAW_CODES_PATH, RAW_CODES_PATH_RESULTS)


  def on_watchdog_file_update(self, file_name, event_type):
    """ Called when IR/RF data in file is modified via the file listener """
    self._logger.log(f'Broadlink RF/IR data updated. Reloading data now.', level='DEBUG')
    self._load_code_data(DEVICE_CODE_PATH)


  def _convert_json_codes_to_yaml(self, src_path, dest_path):
    """ Parse & Convert IR code data from RM Plugin Lite APP into YAML code data 
    
    param src_path: Path to JSON IR codes from RM Plugin Lite web API
    param dest_path: Path to save the newly parsed IR codes into YAML format
    """
    path = self.utils.ad_path(src_path)
    self._logger.log(f'Loading IR codes from {path}', level='DEBUG')
    with open(path, 'rb') as f:
      contents = json.load(f)

    devices = {}
    temp = {}
    for item in contents:
      if 'remoteName' in item:
        if item['remoteName'] not in devices:
          devices[item['remoteName']] = {}
        button = item['displayName'].replace('\u2022', '').replace(item['remoteName'], '').replace('Switch', 'Source').strip()
        devices[item['remoteName']][button] = item['code']

    path = self.utils.ad_path(dest_path)
    self._logger.log(f'Saving code data to {path}', level='DEBUG')
    with open(path, 'w') as f:
      f.write(yaml.dump(devices))


  def _setup(self):
    """ Run all setup for broadlink apps """
    self.setup_broadlink()
    self._load_code_data(DEVICE_CODE_PATH)


  def _load_code_data(self, path):
    """ Load device codes from YAML file """
    path = self.utils.ad_path(path)
    try:
      with open(path, 'r+') as f:
        contents = yaml.safe_load(f)
    except FileNotFoundError as e:
      self._logger.log(f'Code data file does not exist yet. Please manually create it to avoid security issues: {path}.', level='ERROR')
      contents = {}
    self._code_data = contents


  def setup_broadlink(self):
    self._logger.log("Setting up Broadlink Devices", level='DEBUG')
    try:
      devices = broadlink.discover(5, self.args.get("local_ip"))
    except Exception as e:
      self._logger.log(f'Error discovering broadlink devices: {e}', level='ERROR')
      return False

    num = len(devices)
    if num > 0:
      self._logger.log(f"Found {num} Broadlink Devices on the Network", level='DEBUG')
    else:
      self._logger.log(f"Coundn't find any Broadlink Device on the Network", level='WARNING')
      return False

    for device in devices:
      device.auth() # first get device authentication
      device_mac = re.findall('..?', device.mac.hex())
      # device_mac.reverse()
      device_mac = ":".join(device_mac)
      for bl, bl_settings in self.broadlinks.items():
        b_mac = bl_settings.get("mac").lower()
        if b_mac is None:
          raise ValueError("No Device MAC Address given, please provide MAC Address")

        if b_mac != device_mac:
          # Only setup broadlinks that match config entries using MAC address
          continue

        b_service_domain = bl_settings.get("service_domain")
        b_service_domain = "broadlink" if b_service_domain is None else f"broadlink_{b_service_domain}"

        b_friendly_name = bl_settings.get("friendly_name", bl.replace("_", " "))
        b_device_name = b_friendly_name.lower().replace(" ", "_")
        b_device_domain =  bl_settings.get("entity_domain", "sensor")

        (b_ip, b_port) = device.host
        b_type = device.devtype

        entity_id = f"{b_device_domain}.{b_device_name}"

        self.broadlinkObjects[bl] = device #store broadlink object

        self.entities[entity_id] = {}
        self.entities[entity_id]["attributes"] = {"friendly_name" : b_friendly_name, "mac" : b_mac,
                                "ip_address" : b_ip, "port" : b_port, "device_type" : b_type}

        self.set_state(entity_id, state="on", attributes=self.entities[entity_id]["attributes"])

        self._logger.log(f'Setup a broadlink device named {b_device_name} with attributes: {self.entities[entity_id]}', level='DEBUG')
    
    # Quick check to see if everything was setup
    if len(self.broadlinks) != len(self.entities):
      self._logger.log(f'One of more Broadlink devices from config was not setup.', level='WARNING')


  def map_alias_to_controlled_device(self, device):
    """ Map alias to device that broadlink will control (ex basement tv, receiver) """
    if device.lower() in ['living room tv', 'living room television']:
      return 'Living Room TV'
    elif device.lower() in ['living room receiver', 'living room sterio']:
      return 'Living Room Receiver'
    elif device.lower() in ['master tv', 'master bedroom tv']:
      return 'Master TV'
    return device


  def map_alias_to_broadlink_entity(self, name):
    """ Map broadlink alias to entity_id """
    if name in self.broadlinks: 
      return name
    if name.lower().replace(' ', '_') in self.broadlinks:
      return name.lower().replace(' ', '_')
    return name
    

  def _check_broadlink(self, name):
    if not name in self.broadlinkObjects:
      return False
    return True


  def learn(self, name):
    name = self.map_alias_to_broadlink_entity(name)
    if not self._check_broadlink(name):
      return

    self._logger.log(f"[{name}]: Now learning...", level='INFO')
    try:
      self.broadlinkObjects[name].enter_learning()
      learn_time = self.args["broadlinks"][name].get("learn_time", 5)
      self.run_in(lambda *_: self.check_data(name), learn_time)
      return True
    except Exception as e:
      self._logger.log(f'[{name}]: Error learning broadlink code: {e}', level='ERROR')
      return False


  def check_data(self, name):
    name = self.map_alias_to_broadlink_entity(name)
    if not self._check_broadlink(name):
      return

    try:
      data_packet = self.broadlinkObjects[name].check_data()
      data_packet_base64 = None
      data_packet_hex = None

      if data_packet != None:
        data_packet_base64 = base64.b64encode(data_packet)
        data_packet_hex = data_packet.hex()

      self._logger.log(f'data_packet: {data_packet}', level='INFO')
      self._logger.log(f'data_packet_base64: {data_packet_base64}', level='INFO')
      self._logger.log(f'data_packet_hex: {data_packet_hex}', level='INFO')
      
      return data_packet_base64
    except Exception as e:
      self._logger.log(f'[{name}]: Error checking broadlink data: {e}', level='ERROR')
      return False


  def send_data(self, name, data_packet, protocol=None):
    name = self.map_alias_to_broadlink_entity(name)
    self._check_broadlink(name)

    if data_packet in self.args.get("base64", {}):
      data_packet = self.args["base64"][data_packet]
      protocol = "base64"
    
    elif data_packet in self.args.get("pronto", {}):
      data_packet = self.args["pronto"][data_packet]
      protocol = "pronto"
    
    elif data_packet in self.args.get("hex", {}):
      data_packet = self.args["hex"][data_packet]
      protocol = "hex"
    
    elif data_packet in self.args.get("lirc", {}):
      data_packet = self.args["lirc"][data_packet]
      protocol = "lirc"
    
    else: # at this point, auto check what codec is used
      if protocol == None:
        if " " in data_packet: # its either pronto/lirc
          if all(list(map(lambda x: len(x) == 4, data_packet.split()))): # pronto
            protocol = "pronto"
          elif all(list(map(lambda x: len(x) == 2, data_packet.split()))): # hex
            protocol = "hex"
            data_packet = data_packet.replace(" ", "")
          else:
            protocol = "lirc"
        else:
          try:
            int(data_packet)
            protocol = "hex" # hex
          except ValueError:
            protocol = "base64" # base64
    
    if protocol == "pronto":
      code = data_packet.replace(" ", "")
      pronto = bytearray.fromhex(code)
      pulses = self.pronto2lirc(pronto)
      data_packet = self.lirc2broadlink(pulses)
    
    elif protocol == "lirc":
      data_packet = self.lirc2broadlink((data_packet).split())

    elif protocol == "hex":
      data_packet = bytearray.fromhex(data_packet)

    elif protocol == "base64":
      data_packet = base64.b64decode(data_packet)

    try:
      # self._logger.log(f'Sending broadlink command from {name} using protocol: {protocol}', level=self.debug_level)
      self.broadlinkObjects[name].auth()
      self.broadlinkObjects[name].send_data(data_packet)
      return True
    except Exception as e:
      self._logger.log(f'[{name}]: Error sending broadlink command: {e}', level='ERROR')
      return False


  def execute_command(self, broadlink, device, command, repeats=2, interval=3, protocol='hex'):
    """ Core method to execute a command on a broadlink to a specific device in the house 
    Always uses hex encoding when calling self.send_command()
    
    Example: self.execute_command('basement', 'basement tv', 'On')
    
    param broadlink: The broadlink device name to use ('basement', 'master', etc)
    param device: The device to control via the broadlink (TV, receiver, etc)
    param command: The command to send ('On', 'Off', etc)
    param repeats: Number of times to repeat command
    param interval: Number of seconds between each command
    """
    device = self.map_alias_to_controlled_device(device)
    command = command.title()
    try:
      code = self._code_data[device][command]
    except Exception as e:
      self._logger.log(f'Incorrect device ({device}) or command ({command}), no command executed.', level='WARNING')
      return

    broadlink = self.map_alias_to_broadlink_entity(broadlink)
    self.send_data(broadlink, code, protocol)
    self._logger.log(f'[{broadlink}] Sending "{command}" command to "{device}". Repeats left: "{repeats}", interval: "{interval}", protocol: "{protocol}"')

    # Repeat until 0
    if repeats > 0:
      self.run_in(lambda *_: self.execute_command(broadlink, device, command, repeats-1, interval), interval)



################    Utility modified from https://github.com/emilsoman/pronto_broadlink/blob/master/pronto2broadlink.py    #######################


  def pronto2lirc(self, pronto):
      codes = [int(binascii.hexlify(pronto[i:i+2]), 16) for i in range(0, len(pronto), 2)]

      if codes[0]:
          raise ValueError('Pronto code should start with 0000')
      if len(codes) != 4 + 2 * (codes[2] + codes[3]):
          raise ValueError('Number of pulse widths does not match the preamble')

      frequency = 1 / (codes[1] * 0.241246)

      lirc_code = [int(round(code / frequency)) for code in codes[4:]]

      # self._logger.log(lirc_code, level=self.debug_level)
      return lirc_code


  def lirc2broadlink(self, pulses):
      array = bytearray()

      for pulse in pulses:
          if not isinstance(pulse, int):
              pulse = int(pulse)

          pulse = int(pulse * 269 / 8192)  # 32.84ms units

          if pulse < 256:
              array += bytearray(struct.pack('>B', pulse))  # big endian (1-byte)
          else:
              array += bytearray([0x00])  # indicate next number is 2-bytes
              array += bytearray(struct.pack('>H', pulse))  # big endian (2-bytes)

      packet = bytearray([0x26, 0x00])  # 0x26 = IR, 0x00 = no repeats
      packet += bytearray(struct.pack('<H', len(array)))  # little endian byte count
      packet += array
      packet += bytearray([0x0d, 0x05])  # IR terminator

      # Add 0s to make ultimate packet size a multiple of 16 for 128-bit AES encryption.
      remainder = (len(packet) + 4) % 16  # rm.send_data() adds 4-byte header (02 00 00 00)
      if remainder:
          packet += bytearray(16 - remainder)

      return packet


  def terminate(self):
    try:
      self.code_file_watchdog.terminate()
    except AttributeError:
      # App didn't setup correctly, don't worry about it
      pass 


  def test(self, entity, attribute, old, new, kwargs):
    self._logger.log(f'Testing Braodlink_client Module: ')

    # self._logger.log(f'objects: {self.broadlinkObjects}, data: {self.broadlinks}, entities: {self.entities}')
    self.execute_command('living room', 'living room tv', 'On')
