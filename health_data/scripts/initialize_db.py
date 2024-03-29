import argparse
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession,ini_file):
    """
    Add or update models / fixtures in the database.

    """

    import alembic.config
    alembicArgs = [
        '-c',ini_file,
        '--raiseerr',
        'upgrade', 'head',
    ]
    try:
        alembic.config.main(argv=alembicArgs)
    except OperationalError:
        engine=dbsession.bind
        conn=engine.connect()
        result=conn.execute('SHOW WARNINGS')
        for row in result:
            print(row)
        raise

def create_database(engine,settings):

    from sqlalchemy.sql import text
    from MySQLdb import escape_string
    
    conn=engine.connect()
    conn.execute('commit')
    conn.execute('create database if not exists healthdata')
    s=text("create or replace user healthdata identified by '{pw}'".format(
        pw=escape_string(settings['mysql_production_password']).decode('ascii')))
    conn.execute(s)
    conn.execute("grant all on healthdata.* to healthdata")
    conn.execute("use healthdata")
    
def create_admin_user(dbsession,settings):

    import sqlalchemy.exc

    try:
        user=models.User(
            name='admin'
        )

        user.set_password(settings['admin_password'])

        dbsession.add(user)

        person=models.Person(
            name='default'
        )
        dbsession.add(person)

        dbsession.flush()
    except sqlalchemy.exc.IntegrityError:
        pass

def configure_admin_otp(dbsession,settings):
    user = dbsession.query(models.User).filter(
        models.User.name=='admin').one()

    if user.otp_secret_ is None:
        user.otp_secret_=settings['admin_otp_secret']
        dbsession.add(user)
        dbsession.flush()

def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini',
    )
    parser.add_argument(
        '--delete-existing',
        help='Delete existing database',
        action='store_true'
    )
    return parser.parse_args(argv[1:])


def main(argv=sys.argv):
    args = parse_args(argv)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)

    settings=env['request'].registry.settings

    engine_admin=models.get_engine(settings,prefix='sqlalchemy_admin.')

    while True:

        # Here we try to connect to database server until connection succeeds.
        # This is needed because the database server may take longer
        # to start than the application

        import sqlalchemy.exc

        try:
            print("Checking database connection")
            conn=engine_admin.connect()
            conn.execute("select 'OK'")

        except sqlalchemy.exc.OperationalError:
            import time
            print("Connection failed. Sleeping.")
            import traceback
            traceback.print_exc()
            time.sleep(2)
            continue

        # If we get to this line, connection has succeeded so we break
        # out of the loop
        break

    try:

        if engine_admin.dialect.name!='sqlite':
            if args.delete_existing:
                conn=engine_admin.connect()
                try:
                    conn.execute('drop database healthdata')
                except OperationalError:
                    pass
            create_database(engine_admin,settings)

        with env['request'].tm:
            dbsession = env['request'].dbsession
            setup_models(dbsession,args.config_uri)

            admin_exists=dbsession.query(models.User).filter(
                models.User.name=='admin').count()
            if not admin_exists:
                create_admin_user(dbsession,settings)
            configure_admin_otp(dbsession,settings)

    except OperationalError:
        raise

    print('Database setup complete.')
