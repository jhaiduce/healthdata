from ..models import User
from ..models import Person

def view_with_header(view_callable):

    def wrapper(context):

        # Run view callable
        data=view_callable(context)

        request=context.request

        # Turn on the header
        data['show_header']=True

        if request.authenticated_userid is not None:
            # Get the user information
            user=request.dbsession.query(User).filter(
                User.id==request.authenticated_userid).one()
            data['username']=user.name
            data['userid']=user.id
            data['request_url']=request.url

        # Get the list of people to select from
        data['people']=request.dbsession.query(Person)

        data['session_person']=request.dbsession.query(Person).filter(
            Person.id==request.session.get('person_id',None)).first()

        return data

    return wrapper
