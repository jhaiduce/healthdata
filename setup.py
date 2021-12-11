import os

from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info

import subprocess

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'plaster_pastedeploy',
    'pyramid',
    'pyramid_jinja2',
    'pyramid_debugtoolbar',
    'waitress',
    'alembic',
    'pyramid_retry',
    'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'bcrypt',
    'deform',
    'pandas',
    'paginate',
    'pyramid_nacl_session',
    'six',
    'colanderalchemy',
    'plotly',
    'pyotp'
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest >= 3.7.4',
    'pytest-cov',
    'alembic-verify',
    'sqlalchemy-diff == 0.1.5'
]

class NPMInstall(install):
    def run(self):
        subprocess.run(['npm','install'],cwd='health_data',check=True)
        install.run(self)

class NPMDevelop(develop):
    def run(self):
        subprocess.run(['npm','install'],cwd='health_data',check=True)
        develop.run(self)

class NPMEggInfo(egg_info):
    def run(self):
        subprocess.run(['npm','install'],cwd='health_data',check=True)
        egg_info.run(self)

setup(
    name='health_data',
    version='0.0',
    description='Health Data',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    cmdclass={
        'install': NPMInstall,
        'develop': NPMDevelop,
        'egg_info': NPMEggInfo,
    },
    author='',
    author_email='',
    url='',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = health_data:main',
        ],
        'console_scripts': [
            'initialize_health_data_db=health_data.scripts.initialize_db:main',
        ],
    },
)
