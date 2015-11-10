from os import path
from fabric.api import env, task

@task
def load_config_dev():
    env.hosts = ['dev.api.taxi']
    env.user = 'deploy'
    env.use_ssh_config = True
    env.relative_api_path = 'APITaxi'
    env.config_filename = 'dev_settings.py'
    env.relative_config_path = path.join(env.relative_api_path, 'APITaxi',
        env.config_filename)
    env.relative_venv_path = path.join(env.relative_api_path, 'venvAPITaxi')
    env.relative_uwsgi_config_path = path.join(env.relative_api_path, 'uwsgi.ini')
    env.relative_wsgi_file = path.join(env.relative_api_path, 'api_taxi.uwsgi')

    env.wsgi_processes = 1
    env.wsgi_threads = 10
    env.wwwdata_logdir = '/var/log/uwsgi'
    env.wwwdata_piddir = '/var/run/uwsgi'
    env.uwsgi_log = env.wwwdata_logdir
    env.uwsgi_pid = env.wwwdata_piddir

    env.server_name = 'dev.api.taxi'

    env.uwsgi_socket = '/tmp/uwsgi.sock'
    env.postgres_locale = 'fr_FR.UTF-8'
    env.local_redis_conf = 'files/redis.conf'

    env.influx_conf = '/etc/opt/influxdb/influxdb.conf'
    env.influx_db_dir = '/var/influx'
    env.geoserver_port = 80
