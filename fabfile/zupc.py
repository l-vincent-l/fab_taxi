#coding: utf-8
from fabric.api import task, run, env, put
from fabric.context_managers import cd, shell_env
from fabtools import require, files, python
import requests, re, urllib, os
from sqlalchemy.engine import url
from sqlalchemy import create_engine
from utils import wget, list_dir

def table_exists(table_name, connection_string):
    return run('psql {} -tAc "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = \'{}\');"'.format(connection_string, table_name)) == 't'


def drop_table_communes(connection_string, table):
    if table_exists(table, connection_string):
        run("psql {} -c 'drop table \"{}\";'".format(connection_string, table))


def get_departement_id(departement, connection_string):
    return run("psql {} -tAc \"SELECT id from departement where numero='{}'\"".\
        format(connection_string, departement))


def import_contours():
    wget(env.contours_fichier)
    run(u'unzip communes-20150101-5m-shp.zip')
    table_name = 'communes-20150101-5m'
    drop_table_communes(env.conf_api.SQLALCHEMY_DATABASE_URI, table_name)
    run(u'shp2pgsql {} > communes.sql'.format(table_name))
    run(u'psql {} -f communes.sql'.format(env.conf_api.SQLALCHEMY_DATABASE_URI))
    run(u"""psql {} -c 'INSERT INTO \"ZUPC\" (nom, insee, shape,active)
            SELECT nom, insee, geom, false FROM \"{}\";'
            """.format(env.conf_api.SQLALCHEMY_DATABASE_URI, table_name))
    require.files.file('sql_update',
            contents="""UPDATE "ZUPC" SET departement_id = sub.id FROM
                (SELECT id, numero FROM departement) AS sub
                WHERE insee LIKE sub.numero||\'%\';""")
    run('psql {} -f /tmp/zupc/sql_update '.format(env.conf_api.SQLALCHEMY_DATABASE_URI))

@task
def import_zupc(import_='True'):
    require.files.directory('/tmp/zupc')
    with cd('/tmp/zupc/'):
        for f in list_dir():
            if f == '*' or f.endswith('zip'):
                continue
            run('rm -f {}'.format(f))
        if import_=='True':
            import_contours()

    base_dir = ''
    with cd(env.deploy_dir):
        for f in list_dir():
            if files.is_dir(f) and 'deployment' in f and f > base_dir:
                base_dir = f
    api_dir = env.deploy_dir+'/' + base_dir
    with cd('/tmp/zupc'):
        wget(env.zupc_fichier)
    with python.virtualenv(base_dir + '/venvAPITaxi'), cd(base_dir+'/APITaxi-master'):
        with shell_env(APITAXI_CONFIG_FILE='prod_settings.py'):
            run('python manage.py load_zupc /tmp/zupc/zupc.geojson')
