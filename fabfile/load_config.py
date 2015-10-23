import importlib
from fabric.api import env, task
from os import environ
from types import ModuleType

@task
def load_config():
    env.conf_api = ModuleType('config')
    env.conf_api.__file__ = environ['APITAXI_CONFIG_FILE']
    with open(env.conf_api.__file__) as f:
        exec(compile(f.read(), env.conf_api.__file__, 'exec'), env.conf_api.__dict__)
