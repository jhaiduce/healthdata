from subprocess import call
import os
import random
import string

if not os.path.exists('secrets'):
    os.mkdir('secrets')

call(['openssl','genrsa','2048'],stdout=open('secrets/ca-key.pem','w'))
call(['openssl','req','-new','-x509','-nodes','-days','365000','-key','secrets/ca-key.pem','-out','secrets/ca.pem'])
call(['openssl','req','-newkey','rsa:2048','-days','365000','-nodes','-keyout','secrets/server-key.pem','-out','secrets/server-req.pem'])
call(['openssl','rsa','-in','secrets/server-key.pem','-out','secrets/server-key.pem'])
call(['openssl','x509','-req','-in','secrets/server-req.pem','-days','365000','-CA','secrets/ca.pem','-CAkey','secrets/ca-key.pem','-set_serial','01','-out','secrets/server-cert.pem'])
call(['openssl','verify','-CAfile','secrets/ca.pem','secrets/server-cert.pem'])

def genPassword(length=24,charset=string.printable):
    return ''.join([random.choice(charset) for i in range(length)])

open('secrets/db_root_pw','w').write(genPassword())
open('secrets/db_app_pw','w').write(genPassword())
open('secrets/app_admin_pw','w').write(genPassword())

