from pyramid.httpexceptions import HTTPFound
from pyramid.security import (
    remember,
    forget,
    )
from pyramid.view import (
    forbidden_view_config,
    view_config,
)
from pyramid.security import NO_PERMISSION_REQUIRED

from ..models import User, Person

@view_config(route_name='login', renderer='../templates/login.jinja2',permission=NO_PERMISSION_REQUIRED)
def login(request):
    next_url = request.params.get('next', request.referrer)
    if not next_url:
        next_url = request.route_url('period_plot')
    message = ''
    login = ''
    if 'form.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']
        otp = request.params['otp']
        user = request.dbsession.query(User).filter_by(name=login).first()
        if user is not None and user.check_password(password) and user.check_otp(otp):
            headers = remember(request, user.id)

            first_person=request.dbsession.query(Person).order_by(
                    Person.name).first()
            request.session['person_id']=request.session.get(
                'person_id',
                first_person.id if first_person else None)
            return HTTPFound(location=next_url, headers=headers)
        message = 'Failed login'

    return dict(
        message=message,
        url=request.route_url('login'),
        next_url=next_url,
        login=login,
        )

@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    next_url = request.route_url('period_plot')
    return HTTPFound(location=next_url, headers=headers)

@forbidden_view_config()
def forbidden_view(request):
    next_url = request.route_url('login', _query={'next': request.url})
    return HTTPFound(location=next_url)
