from os import path
from fabric.api import env, task

def make_default_values():
    if not hasattr(env, 'apitaxi_dir'):
        env.apitaxi_dir = env.uwsgi_dir + '/APITaxi'
    if not hasattr(env, 'uwsgi_config_path'):
        env.uwsgi_config_path = env.apitaxi_dir + '/uwsgi.ini'
    if not hasattr(env, 'uwsgi_file'):
        env.uwsgi_file = env.apitaxi_dir + '/api_taxi.uwsgi'
    if not hasattr(env, 'apitaxi_venv_path'):
        env.apitaxi_venv_path = env.uwsgi_dir + '/venvAPITaxi'
    if not hasattr(env, 'apitaxi_config_path'):
        env.apitaxi_config_path = env.apitaxi_dir + '/APITaxi/prod_settings.py'

@task
def load_config_dev():
    env.hosts = ['dev.api.taxi']
    env.user = 'deploy'
    env.use_ssh_config = True

    env.uwsgi_dir = '/srv/www'

    env.wsgi_processes = 1
    env.wsgi_threads = 10
    env.wwwdata_logdir = '/var/log/uwsgi'
    env.wwwdata_piddir = '/var/run/uwsgi'

    env.server_name = 'dev.api.taxi'

    env.uwsgi_socket = '/tmp/uwsgi.sock'
    env.postgres_locale = 'fr_FR.UTF-8'
    env.local_redis_conf = 'files/redis.conf'

    env.influx_conf = '/etc/opt/influxdb/influxdb.conf'
    env.influx_db_dir = '/var/influx'
    env.geoserver_port = 80
    make_default_values()
