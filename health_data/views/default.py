from pyramid.view import view_config
from pyramid.response import Response

from sqlalchemy.exc import DBAPIError

from .. import models


from .header import view_with_header

class default_views(object):

    def __init__(self,request):
        self.request=request

    @view_with_header
    @view_config(route_name='home', renderer='../templates/home.jinja2')
    def my_view(self):
        return {'project': 'Health Data'}

db_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to initialize your database tables with `alembic`.
    Check your README.txt for descriptions and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""
