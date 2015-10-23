from fabric.api import task, sudo, run, cd, env
from fabtools import service, files, require
from os import path

def install_influxdb():
    if files.is_file('/etc/init.d/influxdb'):
        return
    with cd('/tmp/'):
        package_name = 'influxdb_0.9.2_amd64.deb'
        run('wget http://influxdb.s3.amazonaws.com/{}'.format(package_name))
        sudo('dpkg -i {}'.format(package_name))
        run('rm {}'.format(package_name))



@task
def configure_influxdb():
    data_dir = path.join(env.influx_db_dir, 'data')
    meta_dir = path.join(env.influx_db_dir, 'meta')
    hinted_dir = path.join(env.influx_db_dir, 'hinted')
    require.files.directories([data_dir, meta_dir],
            use_sudo=True, owner='influxdb')
    tmp_conf_file = '/tmp/influx.conf'
    if files.is_file(tmp_conf_file):
        run('rm {}'.format(tmp_conf_file))
    require.files.template_file(tmp_conf_file, template_source='templates/influx_db.conf',
            context={"meta_dir": meta_dir, "data_dir": data_dir, "hinted_dir": hinted_dir,
                "hostname": env.conf_api.INFLUXDB_HOST,
                "port": env.conf_api.INFLUXDB_PORT})
    sudo('/opt/influxdb/influxd config -config {} > {}'.format(tmp_conf_file,
        env.influx_conf))
    run('rm {}'.format(tmp_conf_file))

@task
def restart_influxdb():
    if service.is_running('influxdb'):
        require.service.restart('influxdb')
    else:
        require.service.start('influxdb')

@task
def status_influxdb():
    sudo('service influxdb status')

@task
def create_db_influxdb():
    influx_url = 'http://{}:{}'.format(env.conf_api.INFLUXDB_HOST,
            env.conf_api.INFLUXDB_PORT)
    run('curl {} --data-urlencode "q=CREATE USER {} WITH PASSWORD \'{}\'"'\
            .format(influx_url, env.conf_api.INFLUXDB_USER,
                env.conf_api.INFLUXDB_PASSWORD))
    run('curl {} -u {} -p {} --data-urlencode "q=CREATE DATABASE {}"'.format(
        influx_url, env.conf_api.INFLUXDB_USER, 
        env.conf_api.INFLUXDB_PASSWORD, env.conf_api.INFLUXDB_TAXIS_DB))


@task
def restart_stats_workers():
    absolute_venv_path = run('readlink -f {}'.format(env.relative_venv_path))

    require.supervisor.process('stat_beat',
        command="{venv}/bin/celery beat --app=celery_worker.celery".format(venv=absolute_venv_path),
        directory=absolute_venv_path,
        environment='APITAXI_CONFIG_FILE="{}"'.format(env.config_filename))

    require.supervisor.process('stat_worker',
        command="{venv}/bin/celery worker --app=celery_worker.celery".format(venv=absolute_venv_path),
        directory=absolute_venv_path,
        environment='APITAXI_CONFIG_FILE="{}"'.format(env.config_filename))
@task
def install_dash():
    install_influxdb()
    configure_influxdb()
    restart_influxdb()
    create_db_influxdb()
    restart_stats_workers()
