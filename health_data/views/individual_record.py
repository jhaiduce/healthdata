from pyramid.events import subscriber
from .crud import ViewDbInsertEvent,ViewDbUpdateEvent
from ..models.records import IndividualRecord
from ..models.people import Person
from .crud import CRUDView

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def set_record_person(event):

    if isinstance(event.obj,IndividualRecord) and event.obj.person==None:

        session_person=event.request.dbsession.query(Person).filter(
            Person.id==event.request.session['person_id']).one()

        event.obj.person=session_person

class IndividualRecordCRUDView(object):

    def get_list_query(self):
        session_person=self.request.dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).one()
        return self.dbsession.query(self.model).filter(
            self.model.person==session_person)
