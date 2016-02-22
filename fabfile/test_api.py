#coding: utf-8
from fabric.api import task, put, env, run, sudo
from fabric.contrib import files
import tempfile, json
from jsondiff import diff

def get_diff(expected, result):
    return diff(json.loads(expected), json.loads(result))

def check_root(diff):
    if not diff.get('data', None):
        raise KeyError('data is expected')
    if len(diff.keys()) != 1:
        raise KeyError('There are too many keys at root')

def check_unique_object(diff):
    if len(diff['data']) != 1:
        raise ValueError('Data expect one object')

def except_id_added(expected, result):
    diff = get_diff(expected, result)
    check_root(diff)
    check_unique_object(diff)
    if not diff['data'][0].get('id'):
        raise KeyError('id wanted')
    if len(diff['data'][0].keys()) != 1:
        raise KeyError('[{}] are unexpected keys'.format(
            ", ".join(diff['data'][0].keys())))

def no_diff(expected, result):
    return get_diff(expected, result) == {}

def test_add_vehicle(curl):
    local_file = 'files/vehicle.json'
    remote_file = '/tmp/testing_uwsgi_vehicle'
    put(local_file, remote_file)
    header, data = curl('/vehicles/', env.conf_api.TESTING_APIKEY_OPERATEUR,
            'POST', '@{}'.format(remote_file))
    except_id_added(open(local_file).read(), data)
    return json.loads(data)['data'][0]['id']


def test_add_ads(curl, vehicle_id):
    remote_file = '/tmp/ads.json'
    context = {'vehicle_id': vehicle_id}
    files.upload_template('templates/ads.json', remote_file, context=context)
    header, data = curl('/ads/',  env.conf_api.TESTING_APIKEY_OPERATEUR, 'POST',
            '@{}'.format(remote_file))
    expected = open('templates/ads.json').read() % context
    if not no_diff(expected, data):
        raise ValueError('{} {} has to be equal'.format(expected, data))


def test_add_driver(curl):
    remote_file = '/tmp/driver.json'
    put('files/driver.json', remote_file)
    header, data = curl('/drivers/',  env.conf_api.TESTING_APIKEY_OPERATEUR,
        'POST', '@{}'.format(remote_file))
    expected = open('files/driver.json').read()
    if not no_diff(expected, data):
        raise ValueError('{} {} has to be equal diff: {}'.format(
                expected, data, get_diff(expected, data)))

def test_add_taxi(curl):
    remote_file = '/tmp/taxi.json'
    put('files/taxi.json', remote_file)
    header, data = curl('/taxis/', env.conf_api.TESTING_APIKEY_OPERATEUR,
        'POST', '@{}'.format(remote_file))
    expected = open('files/taxi_expected.json').read()
    except_id_added(expected, data)
    return json.loads(data)['data'][0]['id']

def send_position_taxi(taxi_id):
    remote_file = '/tmp/send_position_taxi.py'
    put('files/send_position_taxi.py', remote_file)
    run('python {} {} {} {}'.format(remote_file, taxi_id,
        env.conf_api.TESTING_APIKEY_OPERATEUR, env.geoserver_port))


def test_get_taxi(curl, taxi_id):
    header, data = curl('/taxis/{}/'.format(taxi_id),
            env.conf_api.TESTING_APIKEY_OPERATEUR)
    expected = open('files/taxi_expected.json').read()
    diff = get_diff(expected, data)
    check_root(diff)
    check_unique_object(diff)
    if not diff['data'][0].get('id'):
        raise KeyError('id wanted')
    assert json.loads(data)['data'][0]['id'] == taxi_id


def test_get_taxis(curl, taxi_id):
    header, data = curl('/taxis/?lon=0.1&lat=0.1'.format(taxi_id),
            env.conf_api.TESTING_APIKEY_MOTEUR)
    expected = open('files/taxi_expected.json').read()
    diff = get_diff(expected, data)
    check_root(diff)
    if not diff['data'][0].get('id'):
        raise KeyError('id wanted')
    assert json.loads(data)['data'][0]['id'] == taxi_id


def add_departement_zupc():
    remote_file = '/tmp/add_departement_zupc.sql'
    put('files/add_departement_zupc.sql', remote_file)
    run('psql -f {} {}'.format(remote_file, env.conf_api.SQLALCHEMY_DATABASE_URI,))

@task
def test_api(testing_file, socket, server_name):
    add_departement_zupc()
    def curl(*v):
        command = 'python {} {} {} {}'.format(testing_file, socket, 
                server_name+v[0], " ".join(v[1:]))
        return run(command).split(u'\r\r\n\r\r\n', 1)
    vehicle_id = test_add_vehicle(curl)
    test_add_ads(curl, vehicle_id)
    test_add_driver(curl)
    taxi_id = test_add_taxi(curl)
    send_position_taxi(taxi_id)
    test_get_taxi(curl, taxi_id)
    test_get_taxis(curl, taxi_id)
