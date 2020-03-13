###
# app configuration
# https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/environment.html
###

[app:main]
use = egg:health_data

pyramid.reload_templates = true
pyramid.debug_authorization = false
pyramid.debug_notfound = false
pyramid.debug_routematch = false
pyramid.default_locale_name = en
pyramid.includes =
    pyramid_debugtoolbar

sqlalchemy.url = mysql://healthdata:{mysql_production_password_encoded}@healthdata_db:3306/healthdata
sqlalchemy.pool_recycle=3600
sqlalchemy.pool_pre_ping = true

retry.attempts = 3

filter-with = proxy-prefix

auth.secret={pyramid_auth_secret}

sqlalchemy_admin.url = mysql://root:{mysql_root_password_encoded}@healthdata_db:3306
mysql_production_password={mysql_production_password}
admin_password={app_admin_password}

# By default, the toolbar only appears for clients from IP addresses
# '127.0.0.1' and '::1'.
# debugtoolbar.hosts = 127.0.0.1 ::1

[pshell]
setup = health_data.pshell.setup

###
# wsgi server configuration
###

[alembic]
# path to migration scripts
script_location = health_data/alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s
# file_template = %%(rev)s_%%(slug)s
sqlalchemy.url = mysql://root:{mysql_root_password_encoded}@cycling_stack_db:3306/cycling
sqlalchemy.pool_recycle=14400

[server:main]
use = egg:waitress#main
listen = *:80

###
# logging configuration
# https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/logging.html
###

[loggers]
keys = root, health_data, sqlalchemy

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = INFO
handlers = console

[logger_health_data]
level = DEBUG
handlers =
qualname = health_data

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine
# "level = INFO" logs SQL queries.
# "level = DEBUG" logs SQL queries and results.
# "level = WARN" logs neither.  (Recommended for production systems.)

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(asctime)s %(levelname)-5.5s [%(name)s:%(lineno)s][%(threadName)s] %(message)s

[filter:proxy-prefix]
use = egg:PasteDeploy#prefix
scheme=https
