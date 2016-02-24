from fabric.api import task, sudo, run, cd, env
from fabtools import service, files, require
from os import path
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError
import time

def install_influxdb():
    data_dir = path.join(env.influx_db_dir, 'data')
    meta_dir = path.join(env.influx_db_dir, 'meta')
    hinted_dir = path.join(env.influx_db_dir, 'hinted')
    require.users.user('influxdb')
    require.files.directories([data_dir, meta_dir],
            use_sudo=True, owner='influxdb')
    if files.is_file('/usr/bin/influxd'):
        return
    with cd('/tmp/'):
        package_name = 'influxdb_0.9.6.1_amd64.deb'
        run('wget http://influxdb.s3.amazonaws.com/{}'.format(package_name))
        sudo('dpkg -i {}'.format(package_name))
        run('rm {}'.format(package_name))
    require.service.start('influxdb')
    time.sleep(5)
    r = run('influx -execute "{}"'.format(
            "CREATE USER {} WITH PASSWORD '{}' WITH ALL PRIVILEGES".format(
                env.conf_api.INFLUXDB_USER, env.conf_api.INFLUXDB_PASSWORD)
        ))
    run('influx -execute "CREATE DATABASE IF NOT EXISTS {}"'.format(
        env.conf_api.INFLUXDB_TAXIS_DB))



@task
def configure_influxdb():
    data_dir = path.join(env.influx_db_dir, 'data')
    meta_dir = path.join(env.influx_db_dir, 'meta')
    hinted_dir = path.join(env.influx_db_dir, 'hinted')
    tmp_conf_file = '/tmp/influx.conf'
    if files.is_file(tmp_conf_file):
        run('rm {}'.format(tmp_conf_file))
    require.files.template_file(tmp_conf_file, template_source='templates/influx_db.conf',
            context={"meta_dir": meta_dir, "data_dir": data_dir,
                "hinted_dir": hinted_dir,
                "hostname": env.conf_api.INFLUXDB_HOST,
                "port": env.conf_api.INFLUXDB_PORT})
    sudo('influxd config -config {} > {}'.format(tmp_conf_file,
        env.influx_conf))
    run('rm {}'.format(tmp_conf_file))

@task
def restart_influxdb():
    if service.is_running('influxdb'):
        sudo('service influxdb restart', pty=False)
    else:
        require.service.start('influxdb')

@task
def status_influxdb():
    sudo('service influxdb status')


@task
def restart_stats_workers(now=None):
    l = run('for i in {}/deployment_*; do echo $i; done'.format(env.deploy_dir)).split("\n")
    if not now:
        now = int(sorted(l)[-1].split('_')[-1])
    celery = path.join(env.apitaxi_venv_path(now), 'bin', 'celery')
    commandline = '{} {{command}} --app=celery_worker.celery --workdir={} --pidfile={}'
    commandline = commandline.format(celery, env.apitaxi_dir(now),
            path.join(env.uwsgi_pid_dir, 'stat_{command}.pid'))
    celery_directory = path.join(env.deploy_dir, 'celery')
    require.files.directory(celery_directory, owner='www-data', group='adm',
            use_sudo=True)
    require.supervisor.process('stat_beat',
        command=commandline.format(command='beat'),
        directory=env.apitaxi_venv_path(now),
        environment='APITAXI_CONFIG_FILE="{}"'.format(
            env.apitaxi_config_path(now)),
    user='www-data')

    require.supervisor.process('stat_worker',
        command=commandline.format(command='worker'),
        directory=env.apitaxi_venv_path(now),
        environment='APITAXI_CONFIG_FILE="{}"'.format(
            env.apitaxi_config_path(now)),
        user='www-data')
@task
def install_dash():
    install_influxdb()
    configure_influxdb()
    restart_influxdb()
    restart_stats_workers()
