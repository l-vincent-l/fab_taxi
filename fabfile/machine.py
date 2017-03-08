from fabric.api import task, env, settings, sudo
from fabric.operations import run, put, sudo, prompt
from fabtools import require, supervisor, deb, python
from fabtools.files import is_file
from sqlalchemy.engine import url
from fabric.contrib import files
from fabric.context_managers import cd
from fabtools.cron import add_task
import re, time, os

@task
def install_system():
    deploy_user = env.user
    env.user = 'root'
    run('apt-get update')
    require.deb.package('sudo')
    password = prompt('{} password:'.format(deploy_user))
    require.users.user(deploy_user, password=password)
    require.users.sudoer(deploy_user)
    require.deb.uptodate_index()
    run('apt-get --force-yes upgrade')
    require.system.locale(env.postgres_locale)
    require.files.directory(env.uwsgi_logdir, owner='www-data', group='adm',
            use_sudo=True)
    require.files.directory(env.uwsgi_launcher_logdir, owner='www-data', group='adm',
            use_sudo=True)
    require.files.directory(env.uwsgi_pid_dir, owner='www-data', group='adm',
            use_sudo=True)
    require.files.directory(env.uwsgi_socket_dir, owner='www-data', group='adm',
            use_sudo=True)
    require.files.directory(env.deploy_dir, owner=deploy_user,
            use_sudo=True)
    require.files.directory('/var/log/celery', owner='www-data', group='adm',
            use_sudo=True)
    env.user = deploy_user


def install_postgres_postgis():
    require.postgres.server()
    u = url.make_url(env.conf_api.SQLALCHEMY_DATABASE_URI)
    require.postgres.user(u.username, u.password)
    require.postgres.database(u.database, owner=u.username, locale=env.postgres_locale)
    with settings(sudo_user='postgres'):
        sudo('psql -c "CREATE EXTENSION IF NOT EXISTS postgis;" --dbname={}'\
                .format(u.database))


def install_dependencies():
    require.deb.uptodate_index()
    require.deb.packages(['autoconf-archive', 'automake-1.14', 'autoconf2.59',
        'build-essential', 'check', 'libspatialindex-dev', 'git',
        'libgcrypt11-dev', 'unzip', 'cmake', 'libpq-dev', 'python2.7-dev',
        'supervisor', 'locales', 'postgis', 'curl', 'libpcre3', 'libpcre3-dev',
        'unzip','munin', 'libgeos-dev', 'libjpeg62-turbo-dev',
        'libfreetype6', 'libfreetype6-dev', 'ntp', 'libcurl4-openssl-dev',
        'libffi-dev'])
    install_postgres_postgis()
    require.nginx.server()

def add_users():
         require.users.user('taxis')

def install_redis():
    if files.exists('/usr/bin/redis-server'):
        print 'Redis is already installed'
        return
    with cd('/tmp/'):
        run('wget https://github.com/antirez/redis/archive/3.2.0.zip')
        run('unzip 3.2.0.zip')
        run('rm 3.2.0.zip')
        run('mv redis-3.2.0 redis')
        with cd('redis'):
            run('make')
            sudo('cp src/redis-server /usr/bin/redis-server')
            sudo('chown {0}:{0} /usr/bin/redis-server'.format(env.user))
            sudo('cp src/redis-cli /usr/bin/redis-cli')
            sudo('chown {0}:{0} /usr/bin/redis-cli'.format(env.user))

@task
def install_fluentd():
    if not is_file("/etc/init.d/td-agent"):
        sudo('curl -L https://toolbelt.treasuredata.com/sh/install-debian-jessie-td-agent2.sh | sh')
    sudo('usermod -a -G adm td-agent')
    sudo('/usr/sbin/td-agent-gem install fluent-plugin-elasticsearch')
    require.files.template_file("/etc/td-agent/td-agent.conf",
         template_source='templates/td-agent.conf',
         context={"host_elasticsearch":env.conf_api.TDAGENT_ES_HOST,
                  "env_name": env.name,
                  "host": env.conf_api.HOST},
         use_sudo=True)


def install_services():
    install_redis()
    run('rm -rf /tmp/redis')
    require.file('/etc/redis.conf', source='files/redis.conf', use_sudo=True)
    require.file('/etc/redis_cache.conf', source='files/redis_cache.conf', use_sudo=True)
    if not files.exists('/var/run/supervisor.sock'):
        sudo('supervisord -c /etc/supervisor/supervisord.conf')
    supervisor.update_config()
    install_fluentd()


@task
def install_acme():
    path_venv = "/home/deploy/venv/acme"
    renew_command = "{} -d {} && service nginx reload".format(
                os.path.join(path_venv, "bin", "acme-nginx"),
                getattr(env.conf_api, 'HOST', 'localhost'))
    require.python.virtualenv(path_venv)
    with python.virtualenv(path_venv):
        require.python.package("acme-nginx")
        if not is_file("/etc/ssl/private/letsencrypt-account.key", use_sudo=True):
            sudo(renew_command)
    add_task("renew-cert", "@monthly", "root", renew_command)


@task
def restart_services():
    command = 'redis-server /etc/redis.conf'
    require.files.directory('/var/log/redis', use_sudo=True, owner=env.user)
    require.files.file('/var/log/redis/error.log', owner=env.user, use_sudo=True)
    require.files.file('/var/log/redis/error_cache.log', owner=env.user, use_sudo=True)
    if not is_file('/etc/supervisor/conf.d/redis_cache.conf')\
       and is_file('/etc/supervisor/conf.d/redis.conf'):
        last_save = run('redis-cli lastsave')
        run('redis-cli bgsave')
        print "Saving redis, it may take time"
        for i in range(0, 600):
            if last_save != run('redis-cli lastsave'):
                break
            time.sleep(1)
        dbfile = run('redis-cli config get dbfilename|cut -f1|tail -n 1')
        dir_ = run('redis-cli config get dir|cut -f1|tail -n 1')
        run('sudo cp {} {}'.format(os.path.join(dir_, dbfile),
                              '/srv/dump_redis_save.rdb'))
    if not is_file('/etc/supervisor/conf.d/redis.conf'):
        require.supervisor.process('redis', command=command,
                stdout_logfile='/var/log/redis/error.log')
    require.supervisor.process('redis_cache',
            command='redis-server /etc/redis_cache.conf',
            stdout_logfile='/var/log/redis/error_cache.log')
    require.service.restarted('td-agent')
    install_acme()


@task
def install_machine():
    install_dependencies()
    add_users()
    install_services()
