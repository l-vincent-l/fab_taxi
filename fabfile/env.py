from os import path
from fabric.api import env, task

def make_default_values():
    if not hasattr(env, 'apitaxi_dir'):
        env.apitaxi_dir = lambda now: env.deployment_dir(now) + '/APITaxi-master'
    if not hasattr(env, 'uwsgi_config_path'):
        env.uwsgi_config_path = lambda now: env.apitaxi_dir(now) + '/uwsgi.ini'
    if not hasattr(env, 'uwsgi_file'):
        env.uwsgi_file = lambda now: env.apitaxi_dir(now) + '/api_taxi.uwsgi'
    if not hasattr(env, 'apitaxi_venv_path'):
        env.apitaxi_venv_path = lambda now: env.deployment_dir(now) + '/venvAPITaxi'
    if not hasattr(env, 'apitaxi_config_path'):
        env.apitaxi_config_path = lambda now: env.apitaxi_dir(now) + '/APITaxi/prod_settings.py'

@task
def load_config_dev():
    env.hosts = ['vbox']
    env.user = 'deploy'
    env.use_ssh_config = True

    env.uwsgi_dir = '/srv/www'
    env.deployment_dir = lambda now: env.uwsgi_dir + '/deployment_{}'.format(now)

    env.wsgi_processes = 1
    env.wsgi_threads = 10
    env.uwsgi_logdir = '/var/log/uwsgi'
    env.uwsgi_launcher_logdir = '/var/log/uwsgi_launcher'
    env.uwsgi_pid_dir = '/var/run/uwsgi'
    env.uwsgi_pid_file = lambda now: '{}/uwsgi_{}.pid'.format(env.uwsgi_pid_dir, now)

    env.server_name = 'dev.api.taxi'

    env.uwsgi_socket_dir = '/var/run/uwsgi_socket'
    env.uwsgi_socket = lambda now: env.uwsgi_socket_dir + '/apitaxi_{}.sock'.format(now)
    env.postgres_locale = 'fr_FR.UTF-8'
    env.local_redis_conf = 'files/redis.conf'

    env.influx_conf = '/etc/opt/influxdb/influxdb.conf'
    env.influx_db_dir = '/var/influx'
    env.geoserver_port = 80
    env.apitaxi_archive = u'https://github.com/openmaraude/APITaxi/archive/master.zip'
    make_default_values()

env.contours_fichier = u'http://osm13.openstreetmap.fr/~cquest/openfla/export/communes-20150101-5m-shp.zip'
env.zupc_fichier = u'https://www.data.gouv.fr/s/resources/zones-uniques-de-prises-en-charge-des-taxis-zupc/20151023-174638/zupc.geojson'
