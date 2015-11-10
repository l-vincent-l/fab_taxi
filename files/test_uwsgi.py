import sys, socket


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


def ask_uwsgi(addr_and_port, var):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(addr_and_port)
    s.send(pack_uwsgi_vars(var)+ 'Accept:application/json'.encode('utf8'))
    response = []
    while 1:
        data = s.recv(4096)
        if not data:
            break
        response.append(data)
    s.close()
    return b''.join(response).decode('utf8')


def curl(addr_and_port, host):
    var = {
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': '/ads/',
	'REQUEST_URI': '/ads/',
        'SERVER_NAME': host,
        'HTTP_HOST': host,
	'HTTP_ACCEPT': 'application/json',
    }
    return ask_uwsgi(addr_and_port, var)

if __name__ == '__main__':
    print curl(sys.argv[1], sys.argv[2])

