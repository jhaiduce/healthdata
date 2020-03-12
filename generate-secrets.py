from subprocess import call
import os
import random
import string
from urllib import quote_plus

def generate_secrets(secrets_dir='secrets',ini_template='production.ini.tpl',iniout='production.ini'):
    if not os.path.exists(secrets_dir):
        os.mkdir(secrets_dir)

    if not (os.path.exists(secrets_dir+'/ca-key.pem') or os.path.exists(secrets_dir+'/ca.pem')):
        print('Generating root certificate')
        call(['openssl','genrsa','2048'],stdout=open(secrets_dir+'/ca-key.pem','w'))
        call(['openssl','req','-new','-x509','-nodes','-days','365000',
              '-key',secrets_dir+'/ca-key.pem','-out',secrets_dir+'/ca.pem'])

    if not (os.path.exists(secrets_dir+'/server-key.pem') or os.path.exists(secrets_dir+'/server-req.pem')):

        print('Generating server key')
        call(['openssl','req','-newkey','rsa:2048','-days','365000','-nodes',
              '-keyout',secrets_dir+'/server-key.pem','-out',secrets_dir+'/server-req.pem'])
        call(['openssl','rsa','-in',secrets_dir+'/server-key.pem',
              '-out',secrets_dir+'/server-key.pem'])

    if not os.path.exists(secrets_dir+'/server-cert.pem'):

        print('Generating server certificate')
        call(['openssl','x509','-req','-in',secrets_dir+'/server-req.pem',
              '-days','365000','-CA',secrets_dir+'/ca.pem',
              '-CAkey',secrets_dir+'/ca-key.pem','-set_serial','01',
              '-out',secrets_dir+'/server-cert.pem'])

    call(['openssl','verify','-CAfile',secrets_dir+'/ca.pem',secrets_dir+'/server-cert.pem'])

    if not os.path.exists(secrets_dir+'/storage_key.keyfile'):

        # Generate key for MariaDB at-rest encryption
        storage_key=open(secrets_dir+'/storage_key.keyfile','w')
        storage_key.write('1;')
        storage_key.flush()
        call(['openssl','rand','-hex','32'],stdout=storage_key)

    def genPassword(length=24,charset=string.letters+string.digits+string.punctuation):
        return ''.join([random.choice(charset) for i in range(length)])

    def write_password(filename,overwrite=False,*args,**kwargs):
        if not os.path.exists(filename) or overwrite:
            pw=genPassword(*args,**kwargs)
            open(filename,'w').write(pw)
        else:
            pw=open(filename).read()
        return pw

    db_root_pw=write_password(secrets_dir+'/db_root_pw')
    db_app_pw=write_password(secrets_dir+'/db_app_pw')
    app_admin_pw=write_password(secrets_dir+'/app_admin_pw')
    pyramid_auth_secret=write_password(secrets_dir+'/pyramid_auth_secret')

    ini_text=open(ini_template).read().format(
        mysql_production_password=quote_plus(db_app_pw).replace('%','%%'),
        mysql_root_password=quote_plus(db_root_pw).replace('%','%%'),
        app_admin_password=app_admin_pw.replace('%','%%'),
        pyramid_auth_secret=pyramid_auth_secret.replace('%','%%')
    )
    open(os.path.join(secrets_dir,iniout),'w').write(ini_text)

if __name__=='__main__':
    generate_secrets('integration_test_secrets',ini_template='integration_test.ini.tpl',iniout='integration_test.ini')
