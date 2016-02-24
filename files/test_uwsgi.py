#!/usr/bin/python
import sys, socket, json, six

def sz(x):
    s = hex(x if isinstance(x, int) else len(x))[2:].rjust(4, '0')
    s = bytes.fromhex(s) if sys.version_info[0] == 3 else s.decode('hex')
    return s[::-1]

def pack_uwsgi_vars(var):
    pk = b''
    for k, v in var.items() if hasattr(var, 'items') else var:
        pk += sz(k) + k.encode('utf8') + sz(v) + v.encode('utf8')
    return b'\x00' + sz(pk) + b'\x00' + pk

def get_host_from_url(url):
    if '//' in url:
        url = url.split('//', 1)[1]
    host, _, url = url.partition('/')
    return (host, url)


def ask_uwsgi(socket_file, var, content=None):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(socket_file)
    to_send = pack_uwsgi_vars(var)
    if content:
        to_send += content.encode('utf8')
    s.send(to_send)

    response = []
    while 1:
        data = s.recv(4096)
        if not data:
            break
        response.append(data)
    s.close()
    return b''.join(response).decode('utf8')


def curl(socket_file, url, apikey, method='GET', content=None):
    host, uri = get_host_from_url(url)
    path, _, qs = uri.partition('?')
    var = {
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
	'REQUEST_URI': uri,
        'SERVER_NAME': host,
        'HTTP_HOST': host,
        'QUERY_STRING': qs,
	'HTTP_ACCEPT': 'application/json',
        'HTTP_X_VERSION': '2',
        'HTTP_X_API_KEY': apikey,
    }
    if content:
        if not isinstance(content, six.string_types):
            content = json.dumps(content)
        if content.startswith('@'):
            content = open(content[1:], 'rb').read()
        var['CONTENT_LENGTH'] = str(len(content))
        var['CONTENT_TYPE'] = 'application/json'
    return ask_uwsgi(socket_file, var, content)

if __name__ == '__main__':
    print curl(*sys.argv[1:])

