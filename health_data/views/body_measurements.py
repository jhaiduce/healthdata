from pyramid.events import subscriber
from pyramid.view import view_config
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent
from ..models import BodyMeasurements, Note
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
from .header import view_with_header
from ..models.people import Person
from colanderalchemy import SQLAlchemySchemaNode
import colander
import deform

notes_schema = colander.SchemaNode(colander.String(),
                                   name='notes',
                                   widget=deform.widget.TextAreaWidget(),
                                   missing=None)

def notes(obj):
    """
    Return the text of a notes object (for display in the
    BodyMeasurementsViews table)
    """

    return obj.text

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def finalize_bodymeasurements_fields(event):
    """
    Post-process an automatically deserialized BodyMeasurements object
    """

    if isinstance(event.obj,BodyMeasurements):

        # Store the notes field
        if event.appstruct['notes'] is not None:

            if event.obj.notes is None:
                # Create a new notes object
                event.obj.notes=Note()

            # Set/update the notes properties
            event.obj.notes.date=event.obj.time
            event.obj.notes.text=event.appstruct['notes']

        else:

            event.obj.notes=None

class BodyMeasurementsCrudViews(IndividualRecordCRUDView,CRUDView):
   model=BodyMeasurements
   schema=SQLAlchemySchemaNode(
       BodyMeasurements,
       includes=['time','bust','under_ribcage','fullest_belly','waist','hips',notes_schema]
   )
   url_path = '/body_measurements'
   list_display=['time','bust','under_ribcage','fullest_belly','waist','hips',notes]

   def get_list_query(self):
       query=super(BodyMeasurementsCrudViews,self).get_list_query()
       query=query.outerjoin(BodyMeasurements.notes)
       query=query.with_entities(
          BodyMeasurements.id,
          BodyMeasurements.time,BodyMeasurements.bust,
          BodyMeasurements.under_ribcage,
          BodyMeasurements.fullest_belly,BodyMeasurements.waist,
          BodyMeasurements.hips,Note.text)

       return query.order_by(BodyMeasurements.time.desc())

   def dictify(self,obj):
        """
        Serialize a BodyMeasurementsCrudViews object to a dict
        """

        # Default serialization for built-in fields
        appstruct=super(BodyMeasurementsCrudViews,self).dictify(obj)

        if obj.notes is not None:
            appstruct['notes']=obj.notes.text

        return appstruct
