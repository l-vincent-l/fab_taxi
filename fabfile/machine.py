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
    require.postgres.server(10)
    u = url.make_url(env.conf_api.SQLALCHEMY_DATABASE_URI)
    require.postgres.user(u.username, u.password)
    require.postgres.database(u.database, owner=u.username, locale=env.postgres_locale)
    with settings(sudo_user='postgres'):
        sudo('psql -c "CREATE EXTENSION IF NOT EXISTS postgis;" --dbname={}'\
                .format(u.database))


def install_dependencies():
    require.deb.source("postgresql", "http://apt.postgresql.org/pub/repos/apt/",
                       "jessie-pgdg", "main")
    sudo("wget --no-check-certificate -q https://www.postgresql.org/media/keys/ACCC4CF8.asc -O- | apt-key add -")
    sudo("apt-get update")
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
        version = run('redis-server --version')
        if 'v=4.0' in version:
            print 'Redis 4.0 is already installed'
            return
    with cd('/tmp'):
        run('wget http://download.redis.io/releases/redis-4.0.8.tar.gz')
        run('tar -xf redis-4.0.8.tar.gz')
        run('rm redis-4.0.8.tar.gz')
        run('mv redis-4.0.8 redis')
        with cd('redis'):
            run('make')
            supervisor.stop_process('redis')
            supervisor.stop_process('redis_cache')
            sudo('cp src/redis-server /usr/bin/redis-server')
            sudo('chown {0}:{0} /usr/bin/redis-server'.format(env.user))
            supervisor.start_process('redis')
            supervisor.start_process('redis_cache')
            sudo('cp src/redis-cli /usr/bin/redis-cli')
            sudo('chown {0}:{0} /usr/bin/redis-cli'.format(env.user))

@task
def install_fluentd():
    deb.add_apt_key(url="https://packages.treasuredata.com/GPG-KEY-td-agent")
    require.deb.source("treasure-data",
                       "http://packages.treasuredata.com/2/debian/jessie/",
                       "jessie", "contrib")
    require.deb.package("td-agent")
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
    require.files.directory("/etc/ssl/private", use_sudo=True)
    path_venv = "/home/deploy/venv/acme"
    renew_command = "{} -d {} && service nginx reload".format(
                os.path.join(path_venv, "bin", "acme-nginx"),
                getattr(env.conf_api, 'HOST', 'localhost'))
    require.python.virtualenv(path_venv, python_cmd="python3")
    with python.virtualenv(path_venv):
        require.python.package("acme-nginx")
        if not is_file("/etc/ssl/private/letsencrypt-account.key", use_sudo=True)\
        or not is_file("/etc/ssl/private/letsencrypt-domain.pem", use_sudo=True):
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
