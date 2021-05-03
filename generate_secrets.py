from subprocess import check_call
import os
import random
import string
try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus
import binascii
import pyotp

try:
    letters=string.letters
except AttributeError:
    letters=string.ascii_letters

def genPassword(length=24,charset=letters+string.digits+string.punctuation):
    return ''.join([random.choice(charset) for i in range(length)])

def write_password(filename,overwrite=False,password=None,*args,**kwargs):
    if not os.path.exists(filename) or overwrite:
        if password is None:
            pw=genPassword(*args,**kwargs)
        else:
            pw=password
        open(filename,'w').write(pw)
    else:
        pw=open(filename).read()
    return pw

def generate_secrets(secrets_dir='secrets',ini_template='production.ini.tpl',iniout='production.ini'):
    if not os.path.exists(secrets_dir):
        os.mkdir(secrets_dir)

    if not (os.path.exists(secrets_dir+'/ca-key.pem') or os.path.exists(secrets_dir+'/ca.pem')):
        print('Generating root certificate')
        call(['openssl','genrsa','2048'],stdout=open(secrets_dir+'/ca-key.pem','w'))
        check_call(['openssl','req','-new','-x509','-nodes','-days','365000',
              '-key',secrets_dir+'/ca-key.pem','-out',secrets_dir+'/ca.pem'])

    if not (os.path.exists(secrets_dir+'/server-key.pem') or os.path.exists(secrets_dir+'/server-req.pem')):

        print('Generating server key')
        check_call(['openssl','req','-newkey','rsa:2048','-days','365000','-nodes',
              '-keyout',secrets_dir+'/server-key.pem','-out',secrets_dir+'/server-req.pem'])
        check_call(['openssl','rsa','-in',secrets_dir+'/server-key.pem',
                    '-out',secrets_dir+'/server-key.pem'])

    if not os.path.exists(secrets_dir+'/server-cert.pem'):

        print('Generating server certificate')
        check_call(['openssl','x509','-req','-in',secrets_dir+'/server-req.pem',
              '-days','365000','-CA',secrets_dir+'/ca.pem',
              '-CAkey',secrets_dir+'/ca-key.pem','-set_serial','01',
              '-out',secrets_dir+'/server-cert.pem'])

    check_call(['openssl','verify','-CAfile',secrets_dir+'/ca.pem',secrets_dir+'/server-cert.pem'])

    if not os.path.exists(secrets_dir+'/storage_key.keyfile'):

        # Generate key for MariaDB at-rest encryption
        storage_key=open(secrets_dir+'/storage_key.keyfile','w')
        storage_key.write('1;')
        storage_key.flush()
        check_call(['openssl','rand','-hex','32'],stdout=storage_key)

    if not os.path.exists(secrets_dir+'/dhparams.pem'):

        # Generate dhparams.pem
        check_call(['openssl','dhparam',
              '-out',os.path.join(secrets_dir,'dhparams.pem'),
              '4096'])

    app_admin_otp_secret = write_password(secrets_dir+'/admin_otp_secret',
                                      password=pyotp.random_base32())

    mysql_pwd_chars=(letters+string.digits+string.punctuation)
    for c in ["'"]:
        mysql_pwd_chars=mysql_pwd_chars.replace(c,'')

    db_root_pw=write_password(secrets_dir+'/db_root_pw',charset=mysql_pwd_chars)
    db_app_pw=write_password(secrets_dir+'/db_app_pw',charset=mysql_pwd_chars)
    app_admin_pw=write_password(secrets_dir+'/app_admin_pw')
    pyramid_auth_secret=write_password(secrets_dir+'/pyramid_auth_secret')
    pyramid_session_secret=binascii.hexlify(
        bytes(write_password(secrets_dir+'/pyramid_session_secret',length=32),'ascii'))

    ini_text=open(ini_template).read().format(
        mysql_production_password_encoded=quote_plus(db_app_pw).replace('%','%%'),
        mysql_production_password=db_app_pw.replace('%','%%'),
        mysql_root_password_encoded=quote_plus(db_root_pw).replace('%','%%'),
        app_admin_password=app_admin_pw.replace('%','%%'),
        app_admin_otp_secret=app_admin_otp_secret.replace('%','%%'),
        pyramid_auth_secret=pyramid_auth_secret.replace('%','%%'),
        session_secret=pyramid_session_secret.decode('ascii').replace('%','%%')
    )
    open(os.path.join(secrets_dir,iniout),'w').write(ini_text)

if __name__=='__main__':
    from argparse import ArgumentParser

    parser=ArgumentParser()
    parser.add_argument('--secretsdir',default='secrets',
                        help='Directory where secrets should be written')
    parser.add_argument('--ini-template',default='production.ini.tpl',
                        help='Template for Pyramid config file')
    parser.add_argument('--ini-filename',default='production.ini',
                        help='Name of ini file')
    args=parser.parse_args()

    generate_secrets(args.secretsdir,
                     ini_template=args.ini_template,iniout=args.ini_filename)
