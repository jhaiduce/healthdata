from pyramid.events import subscriber
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent

from ..models import Symptom,SymptomType,Note
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
import colander
import deform

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def finalize_symptom_fields(event):

    if isinstance(event.obj,Symptom):

        if event.appstruct['notes'] is not None:
            if event.obj.notes is None:
                event.obj.notes=Note()
            event.obj.notes.date=event.obj.start_time
            event.obj.notes.text=event.appstruct['notes']
        else:
            event.obj.notes=None

symptomtype_schema = colander.SchemaNode(colander.String(),
                                         name='symptomtype',
                                         title='Symptom',
                                         widget=deform.widget.TextInputWidget())

notes_schema = colander.SchemaNode(colander.String(),
                                   name='notes',
                                   widget=deform.widget.TextAreaWidget(),
                                   missing=None)

class SymptomViews(IndividualRecordCRUDView,CRUDView):
    model=Symptom
    schema=SQLAlchemySchemaNode(
        Symptom,
        includes=[symptomtype_schema,'start_time','end_time',notes_schema],
        overrides={
            'start_time':{
                'title':'First noted',
            },
            'end_time':{
                'title':'Last noted',
            },
        }
    )
    url_path = '/symptom'
    list_display=('symptomtype','start_time','end_time',)

    def dictify(self,obj):

        appstruct=super(SymptomViews,self).dictify(obj)

        if obj.notes is not None:
            appstruct['notes']=obj.notes.text

        return appstruct
