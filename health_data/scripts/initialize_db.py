import argparse
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession):
    """
    Add or update models / fixtures in the database.

    """
    Base=models.Base
    engine=dbsession.bind
    Base.metadata.create_all(engine)

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
            setup_models(dbsession)
    except OperationalError:
        raise
