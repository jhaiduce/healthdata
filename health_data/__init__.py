from pyramid.config import Configurator

from pyramid.session import JSONSerializer
from pyramid_nacl_session import EncryptedCookieSessionFactory

import binascii

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    with Configurator(settings=settings,
                      root_factory='.resources.Root') as config:
        config.include('.models')
        config.include('pyramid_jinja2')
        config.include('.routes')
        config.include('.security')
        config.scan(ignore=['.tests','.migration_tests'])
        config.set_default_permission('view')
        hex_secret = config.get_settings()['session_secret'].strip()
        secret = binascii.unhexlify(hex_secret)
        factory = EncryptedCookieSessionFactory(
            secret=secret,serializer=JSONSerializer(),
            timeout=86400
        )
        config.set_session_factory(factory)

    return config.make_wsgi_app()
