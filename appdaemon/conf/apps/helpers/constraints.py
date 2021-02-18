"""
File Must be saved as constaints.py
Usage: 
  - Import: from constraints import load_constraints
  - In initialize add load_constraints(self)
  - Add any constraints from this file to your app config (See each function below for config examples)
"""

from functools import partial
import operator

def load_constraints(app):
  """ 
  Loads and registers all constraints from app config
  Constraint names must be the same as defined in this file
  """
  for arg in app.args:
    if 'constraint' in arg:
      try:
        func = getattr(__import__('constraints'), arg)
      except AttributeError:
        app.log('In {} app config constraint "{}" does not exist and will be ignored.'.format(app.name, arg), level='WARNING')
        continue

      method = partial(func, app)
      setattr(app, arg, method)
      app.register_constraint(arg)


def constraint_compare(app, value): 
  """ 
  All entities are required to satisfy the provided operator with their respective listed state(s)
  constraint_compare:
    - sensor.temperature, <, 25.2
    - sensor.humidity, >, 60
    - input_boolean.dark_mode, =, on
    - sensor.people_home, !=, 1, 3
  """
  ops = { 
    "+" : operator.add,
    "-" : operator.sub,
    ">" : operator.gt,
    ">=" : operator.ge,
    "<" : operator.lt,
    "<=" : operator.le,
  }

  if not isinstance(value, list):
    value = [value]

  for v in value:
    if len(v) < 3:
      app.log('Invalid config for constraint_compare in {} app. Specify: entity, operator, state(s). It will be ignored.'.format(app.name))
      continue

    values = [x.strip(' ') for x in v.split(',')]
    entity = values[0]
    op = values[1]
    desired_states = values[2:]
    current_state = app.get_state(entity)

    if op in ['=', '==']:
      if current_state not in desired_states:
        return False
    elif op in ['!=']:
      if current_state in desired_states:
        return False
    elif op in ops:
      for state in desired_states:
        if not ops[op](float(current_state), float(state)):
          return False
    else:     
      app.log('Invalid config for constraint_compare in {} app. Specify: entity, operator, state(s). It will be ignored.'.format(app.name))

  return True


def constraint_all_match(app, value): 
  """ 
  All entities must be in one of their respective listed state(s)
  constraint_all_match:
    - sensor.holiday, My Birthday, Your Birthday
    - input_boolean.dark_mode, on
    - input_boolean.speech_mode
    - sensor.people_home, 2, 3
  """
  if not isinstance(value, list):
    value = [value]

  for v in value:
    values = [x.strip(' ') for x in v.split(',')]
    entity = values[0]
    if len(values) == 1:
      desired_states = ["on"]
    else:
      desired_states = values[1:]

    if app.get_state(entity) not in desired_states:
      return False

  return True


def constraint_any_match(app, value): 
  """ 
  Any entities must be in one of their respective listed state(s)
  constraint_any_match:
    - sensor.holiday, My Birthday, Your Birthday
    - input_boolean.dark_mode, on
    - input_boolean.speech_mode
  """
  if not isinstance(value, list):
    value = [value]

  for v in value:
    values = [x.strip(' ') for x in v.split(',')]
    entity = values[0]
    if len(values) == 1:
      desired_states = ["on"]
    else:
      desired_states = values[1:]

    if app.get_state(entity) in desired_states:
      return True

  return False

