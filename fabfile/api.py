from fabric.contrib import files
from fabtools import require, git, python, nginx, supervisor, service
from fabric.context_managers import cd, shell_env
from fabric.api import put, run, task, env
from os import environ, path


def deploy_nginx_api_site():
    absolute_api_path = run('readlink -f {}'.format(env.relative_api_path))
    absolute_venv_path = run('readlink -f {}'.format(env.relative_venv_path))
    absolute_uwsgi_config_path = run('readlink -f {}'.format(env.relative_uwsgi_config_path))
    absolute_wsgi_file = run('readlink -f {}'.format(env.relative_wsgi_file))


    uwsgi = path.join(absolute_venv_path, 'bin', 'uwsgi')
    files.upload_template('templates/uwsgi.ini',  absolute_uwsgi_config_path,
        context={
           'config_filename': env.config_filename,
           'absolute_api_path': absolute_api_path,
           'absolute_venv_path': absolute_venv_path,
           'uwsgi_socket': env.uwsgi_socket,
           'wsgi_file': absolute_wsgi_file,
           'wsgi_pid': env.uwsgi_pid,
           'wsgi_log': env.uwsgi_log,
           'socket': env.uwsgi_socket,
           'processes': env.wsgi_processes,
           'threads': env.wsgi_threads
           }
    )

    require.supervisor.process('uwsgi',
        command='{} --ini {}'.format(uwsgi, absolute_uwsgi_config_path),
        directory=absolute_venv_path,
        stdout_logfile = '/var/log/nginx/apitaxi.log')

    require.nginx.site('apitaxi',
        template_source='templates/nginx_site.conf',
        domain_name=getattr(env.conf_api, 'HOST', 'localhost'),
        port=getattr(env.conf_api, 'PORT', 80),
        socket=env.uwsgi_socket
    )


@task
def deploy_api():
    if not files.exists('APITaxi'):
        git.clone('https://github.com/openmaraude/APITaxi')
    require.python.virtualenv(env.relative_venv_path)
    with python.virtualenv(env.relative_venv_path):
        python.install_pip()
        put(environ['APITAXI_CONFIG_FILE'], env.relative_config_path)
    deploy_nginx_api_site()


@task
def upgrade_api():
    git.pull('APITaxi')
    with python.virtualenv(env.relative_venv_path), cd(env.relative_api_path):
        with shell_env(APITAXI_CONFIG_FILE=env.config_filename):
            python.install_requirements('requirements.txt')
            require.python.package('uwsgi')
            run('python manage.py db upgrade')
    restart_api()

@task
def restart_api():
    supervisor.restart_process('uwsgi')
    if service.is_running('nginx'):
        service.restart('nginx')
    else:
        service.start('nginx')
