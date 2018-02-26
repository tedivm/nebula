#!/usr/bin/env python3

import json
import urllib.parse
import urllib.request
import sys
import ssl
import os

nebulus_host = 'https://example.com/ssh/export'
sshsecret = ''

def get_keys(ignore_ssl = False):
    url = nebulus_host
    user_agent = 'openssh authorized keys command'
    headers = {'User-Agent': user_agent, 'sshsecret': sshsecret}

    try:
        # python3 on OSX does not use the system certs, so for testing we can bypass
        ctx = ssl.create_default_context()
        if ignore_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers = headers)
        with urllib.request.urlopen(req, context=ctx) as response:
          raw_keys = response.read().decode('utf-8')
          return json.loads(raw_keys)
    except urllib.error.HTTPError as e:
        print(e, file=sys.stderr)
        return False

if len(sys.argv) < 2 or sys.argv[1] == 'help':
    print ('authorized_keys.py username')
    print ('authorized_keys.py username ignore_ssl')
    exit()

username = sys.argv[1]


keyfile = os.path.expanduser('~%s/.ssh/authorized_keys' % (username,))
if os.path.isfile(keyfile):
    with open(keyfile) as f:
        print(f.read())

if len(sys.argv) > 2 and sys.argv[2] == 'ignore_ssl':
    ssh_keys = get_keys(True)
else:
    ssh_keys = get_keys()

if not ssh_keys:
    print('No keys found on server', file=sys.stderr)
    exit()

if username not in ssh_keys:
    print('User %s does not have any keys' % (username,), file=sys.stderr)
    exit()

for key in ssh_keys[username]:
  print(key)
