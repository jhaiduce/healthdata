from pyramid.events import subscriber
from pyramid.view import view_config
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent
from ..models import MenstrualCupFill, Note
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
import deform
import colander

# Notes is a foreign key reference to the symptomtype table. Since we
# only want to expose one field of notes, we declare a custom SchemaNode
# for it
notes_schema = colander.SchemaNode(colander.String(),
                                   name='notes',
                                   widget=deform.widget.TextAreaWidget(),
                                   missing=None)

def notes(obj):
    """
    Return the text of a notes object (for display in the SymptomViews table)
    """

    return obj.notes.text if obj.notes else None

class MenstrualCupFillCrudViews(IndividualRecordCRUDView,CRUDView):
    model=MenstrualCupFill
    schema=SQLAlchemySchemaNode(
       MenstrualCupFill,
       includes=['time','fill',notes_schema],
       overrides={
           'notes':{
               'widget':deform.widget.TextAreaWidget()
           },
       }
    )
    title='menstrual cup fill'
    url_path = '/period/menstrual_cup_fill'
    list_display=('time','fill',notes)

    def get_list_query(self):
       query=super(MenstrualCupFillCrudViews,self).get_list_query()

       return query.order_by(MenstrualCupFill.time.desc())

    def dictify(self,obj):
        """
        Serialize a MenstrualCupFill object to a dict for CRUD view
        """

        appstruct=super(MenstrualCupFillCrudViews,self).dictify(obj)

        if obj.notes is not None:
           appstruct['notes']=obj.notes.text

        return appstruct

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def finalize_menstrualcupfill_fields(event):

    """
    Post-process an automatically deserialized MenstrualCupFill object
    """

    if isinstance(event.obj,MenstrualCupFill):
        if event.appstruct['notes']:
            if event.obj.notes is None:
               event.obj.notes=Note()
               event.obj.notes.text=event.appstruct['notes']
               event.obj.notes.date=event.obj.time

        else:

            event.obj.notes=None

        event.request.dbsession.flush()
