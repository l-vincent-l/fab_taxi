from os import path
from fabric.api import env, task

def make_default_values():
    env.shell = '/bin/bash -l -i -c'
    env.user = 'deploy'
    env.apitaxi_dir = lambda now: env.deployment_dir(now) + '/APITaxi-master'
    env.fronttaxi_dir = lambda now: env.deployment_dir(now) + '/APITaxi_front-master'
    env.uwsgi_api_config_path = lambda now: env.apitaxi_dir(now) + '/uwsgi_api.ini'
    env.uwsgi_front_config_path = lambda now: env.fronttaxi_dir(now) + '/uwsgi_front.ini'
    env.uwsgi_api_file = lambda now: env.apitaxi_dir(now) + '/api_taxi.uwsgi'
    env.uwsgi_front_file = lambda now: env.fronttaxi_dir(now) + '/front_taxi.uwsgi'
    env.apitaxi_venv_path = lambda now: env.deployment_dir(now) + '/venvAPITaxi'
    env.apitaxi_config_path = lambda now: env.apitaxi_dir(now) + '/APITaxi/prod_settings.py'
    env.fronttaxi_config_path = lambda now: env.fronttaxi_dir(now) + '/APITaxi_front/prod_settings.py'
    env.wsgi_processes = 8
    env.wsgi_threads = 10
    env.geotaxi_authentication = False
    env.use_ssh_config = True
    env.deploy_dir = '/srv/www'
    env.deployment_dir = lambda now: env.deploy_dir + '/deployment_{}'.format(now)
    env.uwsgi_logdir = '/var/log/uwsgi'
    env.uwsgi_launcher_logdir = '/var/log/uwsgi_launcher'
    env.uwsgi_pid_dir = '/var/run/uwsgi'
    env.uwsgi_api_pid_file = lambda now: '{}/uwsgi_api_{}.pid'.format(env.uwsgi_pid_dir, now)
    env.uwsgi_front_pid_file = lambda now: '{}/uwsgi_front_{}.pid'.format(env.uwsgi_pid_dir, now)
    env.somaxconn = 65535
    env.tcp_max_syn_backlog = 65535
    env.uwsgi_socket_dir = '/var/run/uwsgi_socket'
    env.uwsgi_socket_api = lambda now: env.uwsgi_socket_dir + '/apitaxi_{}.sock'.format(now)
    env.uwsgi_socket_front = lambda now: env.uwsgi_socket_dir + '/fronttaxi_{}.sock'.format(now)
    env.postgres_locale = 'fr_FR.UTF-8'
    env.local_redis_conf = 'files/redis.conf'

    env.influx_conf = '/etc/influxdb/influxdb.conf'
    env.influx_db_dir = '/var/influx'
    env.geoserver_port = 80
    env.apitaxi_archive = u'https://github.com/openmaraude/APITaxi/archive/{}.zip'
    env.fronttaxi_archive = u'https://github.com/openmaraude/APITaxi_front/archive/master.zip'
    env.geotaxi_authentication = True

    env.contours_fichier = u'http://osm13.openstreetmap.fr/~cquest/openfla/export/communes-20150101-5m-shp.zip'
    env.zupc_fichier = u'https://www.data.gouv.fr/s/resources/zones-uniques-de-prises-en-charge-des-taxis-zupc/20151023-174638/zupc.geojson'

@task
def load_config_dev():
    env.name = 'dev'
    env.server_name = 'dev.api.taxi'
    env.hosts = [env.server_name]
    env.influx_db_dir = '/home/deploy/influx'

@task
def load_config_local():
    env.name = 'local'
    env.hosts = ['127.0.0.1:2223']
    env.server_name = 'localhost'

@task
def load_config_test():
    env.name = 'test'
    env.server_name = 'test.api.taxi'
    env.hosts = [env.server_name]

@task
def load_config_prod():
    env.name = 'prod'
    env.server_name = 'api.taxi'
    env.hosts = [env.server_name]

    env.wsgi_processes = 24
    env.geotaxi_authentication = False

make_default_values()
