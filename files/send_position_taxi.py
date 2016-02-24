import time, socket, json, sys, hashlib
if __name__ == '__main__':
    payload = {
        "timestamp": str(int(time.time())),
        "operator": sys.argv[4],
        "taxi": sys.argv[1],
        "lat":"0.1",
        "lon":"0.1",
        "device":"phone",
        "status":"0",
        "version":"1"
    }
    concat = "".join(map(lambda k: payload[k], ['timestamp', 'operator',
        'taxi', 'lat', 'lon', 'device', 'status', 'version']))
    concat += sys.argv[2]
    payload['hash'] = str(hashlib.sha1(concat))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(payload), ('127.0.0.1', int(sys.argv[3])))
