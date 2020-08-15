from pyramid.events import subscriber
from .crud import CRUDView, ViewDbInsertEvent
from ..models import Symptom,SymptomType
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
import colander
import deform

@subscriber(ViewDbInsertEvent)
def set_record_person(event):

    if isinstance(event.obj,Symptom):

        session_person=event.request.dbsession.query(Person).filter(
            Person.id==event.request.session['person_id']).one()

        if event.obj.notes.person is None:
            event.obj.notes.person=session_person

class SymptomViews(IndividualRecordCRUDView,CRUDView):
    model=Symptom
    schema=SQLAlchemySchemaNode(
        Symptom,
        includes=['symptomtype','start_time','end_time','notes'],
        overrides={
            'symptomtype':{'includes':['name'],'widget':deform.widget.TextInputWidget()},
            'start_time':{
                'title':'First noted',
            },
            'end_time':{
                'title':'Last noted',
            },
            'notes':{
                'includes':['text'],
                'widget':deform.widget.TextAreaWidget()
            }
        }
    )
    url_path = '/symptom'
    list_display=('symptomtype','start_time','end_time',)
