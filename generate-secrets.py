from subprocess import call
import os
import random
import string

if not os.path.exists('secrets'):
    os.mkdir('secrets')

if not (os.path.exists('secrets/ca-key.pem') or os.path.exists('secrets/ca.pem')):
    print('Generating root certificate')
    call(['openssl','genrsa','2048'],stdout=open('secrets/ca-key.pem','w'))
    call(['openssl','req','-new','-x509','-nodes','-days','365000',
          '-key','secrets/ca-key.pem','-out','secrets/ca.pem'])

if not (os.path.exists('secrets/server-key.pem') or os.path.exists('secrets/server-req.pem')):

    print('Generating server key')
    call(['openssl','req','-newkey','rsa:2048','-days','365000','-nodes',
          '-keyout','secrets/server-key.pem','-out','secrets/server-req.pem'])
    call(['openssl','rsa','-in','secrets/server-key.pem',
          '-out','secrets/server-key.pem'])
        
if not os.path.exists('secrets/server-cert.pem'):

    print('Generating server certificate')
    call(['openssl','x509','-req','-in','secrets/server-req.pem',
          '-days','365000','-CA','secrets/ca.pem',
          '-CAkey','secrets/ca-key.pem','-set_serial','01',
          '-out','secrets/server-cert.pem'])

call(['openssl','verify','-CAfile','secrets/ca.pem','secrets/server-cert.pem'])

if not os.path.exists('secrets/storage_key.keyfile'):

    # Generate key for MariaDB at-rest encryption
    storage_key=open('secrets/storage_key.keyfile','w')
    storage_key.write('1;')
    storage_key.flush()
    call(['openssl','rand','-hex','32'],stdout=storage_key)

def genPassword(length=24,charset=string.printable):
    return ''.join([random.choice(charset) for i in range(length)])

def write_password(filename,overwrite=False,*args,**kwargs):
    if not os.path.exists(filename) or overwrite:
        open(filename,'w').write(genPassword(*args,**kwargs))

write_password('secrets/db_root_pw')
write_password('secrets/db_app_pw')
write_password('secrets/app_admin_pw')
write_password('secrets/pyramid_auth_secret')
