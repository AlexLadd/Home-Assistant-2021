"""
Utility for watching a file for modifications

on_watchdog_file_update(file_name) method called when a file is updated
block() & unblock() can be called on this class to stop any updates from occuring

NOTE: file_watchdog.terminate() MUST BE CALLED WHEN THE APP IS TERMINATED TO STOP THE THREAD

Defaults to listen to modified files only. Change this by settings:
track_modified, track_created, track_moved, track_deleted, use_any
"""

# TODO:
#   - Create a factory style class that can create different types of watchdogs depending on input parameters? (If this becomes a requirement)

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler 
from pathlib import Path

class FileWatchdog:

  def __init__(self, app, directory, file_pattern, single_file=True, ignore_directories=True, debug_level='NOTSET',
              track_modified=True, track_created=False, track_deleted=False, track_moved=False, use_any=False):
    """
    param app: AD app
    param directory: The directory to watch
    param file_pattern: The file name or file pattern to listen for ('*' means everything)
    param single_file: No longer does anything, in here for backwards compatability...
    param ignore_directories: Ignore any nested directories
    param debug_level: Logger debugging level
    param use_*: Listen for that option to occur to the file(s)
    """
    self.app = app
    self.debug_level = debug_level
    self._observer = None

    if use_any:
      track_modified = track_created = track_deleted = track_moved = True
    self._file_handler = FileHandler(app, file_pattern, single_file, ignore_directories, debug_level,
                                     track_modified, track_created, track_deleted, track_moved)

    # If the directory does not exists it will throw error when setting up the observer
    if not Path(directory).is_dir():
      self.app._logger.log(f'[{self.app.name}] The directory "{directory}" does not currenctly exist. The file watchdog will not be setup to watch for "{file_pattern}".', level='WARNING')
      return

    self._observer = Observer()
    self._observer.schedule(self._file_handler, directory)
    self._observer.start()

    self.app._logger.log('Setup a file watchdog for {} & file: {}'.format(directory, file_pattern), self.debug_level)
    
    

  def block(self):
    """ Prevent the watchdog from updating """
    self._file_handler.block()

  def unblock(self):
    """ Allow watchdog to update """
    self._file_handler.unblock()

  def terminate(self):
    # Stop the watchdog thread
    if self._observer is not None:
      try:
        self._observer.stop()
        self._observer.join(timeout=2)
      except Exception as e:
        self.app._logger.log('Error joining watchdog _observer for app {}: {}.'.format(self.app.__module__, e), level='ERROR')


class FileHandler(PatternMatchingEventHandler):

  def __init__(self, app, file_pattern, single_file=True, ignore_directories=True, debug_level='NOTSET', 
              track_modified=True, track_created=False, track_deleted=False, track_moved=False):
    if not isinstance(file_pattern, list): file_pattern = [file_pattern]
    # app._logger.log(f'pattern: ({file_pattern} ({type(file_pattern)}))')
    super(FileHandler, self).__init__(patterns=file_pattern, ignore_directories=ignore_directories)
    self.app = app
    self.single_file = single_file
    self.file_pattern = file_pattern
    self.debug_level = debug_level
    self._updating = False
    self._blocked = False

    self.track_modified = track_modified
    self.track_created = track_created
    self.track_moved = track_moved
    self.track_deleted = track_deleted


  def block(self):
    """ Call this to prevent HA scene reloads """
    self.app._logger.log('App "{}" FileWatchdog is blocked.' \
        .format(self.app.__module__), level=self.debug_level)
    self._blocked = True


  def unblock(self):
    """ Call this to allow HA scene reloads """
    self.app._logger.log('App "{}" FileWatchdog is no longer updating.' \
        .format(self.app.__module__), level=self.debug_level)
    self._blocked = False


  def _directory_change(self, file_name, event_type):
    """ Reload upon a change to the directory 
    
    param file_name: The absolute path & name of the file modified
    param event_type: What change occured (modified, created, deleted, moved)
    """
    if self._updating or self._blocked:
      # If currently updating or blocked than skip
      self.app._logger.log('App "{}" FileWatchdog file event observed but is currently updating or blocked. No update will be called.' \
          .format(self.app.__module__), level=self.debug_level)
      return

    self._updating = True
    try:
      self.app.on_watchdog_file_update(file_name, event_type)
    except Exception as e:
      self.app._logger.log('App "{}" does not contain the on_watchdog_file_update(file_name, event_type) method.'.format(self.app.__module__), level='ERROR')
      self.app._logger.log('Error: {}'.format(e), level='ERROR')
    self.app.run_in(lambda *_: self._release(), 2)


  def _release(self):
    """ Allow another update to be done """
    self.app._logger.log('App "{}" FileWatchdog is no longer updating.'.format(self.app.__module__), level=self.debug_level)
    self._updating = False


  def _should_update(self, path):
    """ Old method that isn't used anymore """
    return True
    # self.app._logger.log(f"[{self.app.name}] pattern: {self.file_pattern}, event_path_file: {path.split('/')[-1]}")
    # if not self.single_file: return True
    # return bool(path.split('/')[-1] == self.file_pattern)


  def on_modified(self, event):
    """ Listen for modifications to the file(s) """
    if not self.track_modified or not self._should_update(event.src_path):
      return
    self.app._logger.log('File modified: "{}" (listening app: "{}").'.format(event.src_path, self.app.__module__), level=self.debug_level)
    self._directory_change(event.src_path, 'modified')

  def on_created(self, event):
    if not self.track_created or not self._should_update(event.src_path):
      return
    self.app._logger.log('File created: {} (listening app: "{}").'.format(event.src_path, self.app.__module__), level=self.debug_level)
    self._directory_change(event.src_path, 'created')

  def on_deleted(self, event):
    if not self.track_deleted or not self._should_update(event.src_path):
      return
    self.app._logger.log('File deleted: {} (listening app: "{}").'.format(event.src_path, self.app.__module__), level=self.debug_level)
    self._directory_change(event.src_path, 'deleted')

  def on_moved(self, event):
    if not self.track_moved or not self._should_update(event.dest_path):
      return
    self.app._logger.log('File moved: {} (listening app: "{}").'.format(event.dest_path, self.app.__module__), level=self.debug_level)
    self._directory_change(event.dest_path, 'moved')


