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
   title='body measurements'

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

class BodyMeasurementsViews(object):
    def __init__(self,request):
        self.request=request

    @view_with_header
    @view_config(route_name='bodymeasurements_plot',renderer='../templates/generic_plot.jinja2')
    def plot(self):

        import json
        import plotly

        import pandas as pd
        import numpy as np

        dbsession=self.request.dbsession

        session_person=dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).first()
        query=dbsession.query(BodyMeasurements).with_entities(
            BodyMeasurements.time, BodyMeasurements.bust,
            BodyMeasurements.under_ribcage, BodyMeasurements.waist,
            BodyMeasurements.fullest_belly, BodyMeasurements.hips
        ).filter(
            BodyMeasurements.person==session_person
        ).order_by(BodyMeasurements.time.desc())

        measurements=pd.read_sql(query.statement,dbsession.bind)
        measurements=measurements.dropna(subset=['time'])
        dates=measurements['time']
        dates=dates.apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))

        from .plotly_defaults import default_axis_style

        graphs=[
            {
                'data':[
                   {
                      'x':list(dates),
                      'y':list(measurements.fullest_belly),
                      'type':'scatter',
                      'mode':'lines+markers',
                      'name':'Fullest belly',
                   },
                   {
                      'x':list(dates),
                      'y':list(measurements.bust),
                      'type':'scatter',
                      'mode':'lines+markers',
                      'name':'Bust',
                   },
                   {
                      'x':list(dates),
                      'y':list(measurements.under_ribcage),
                      'type':'scatter',
                      'mode':'lines+markers',
                      'name':'Under ribcage',
                   },
                   {
                      'x':list(dates),
                      'y':list(measurements.waist),
                      'type':'scatter',
                      'mode':'lines+markers',
                      'name':'Waist',
                   },
                   {
                      'x':list(dates),
                      'y':list(measurements.hips),
                      'type':'scatter',
                      'mode':'lines+markers',
                      'name':'Hips',
                   },
                ],
                'layout':{
                    'margin':{
                        'l':55,
                        'r':25,
                        'b':50,
                        't':45,
                        'pad':2,
                    },
                    'plot_bgcolor': '#E5ECF6',
                    'yaxis':{
                        **default_axis_style,
                        'title':{
                            'text':'Length (in)'
                        }
                    },
                    'xaxis':default_axis_style
                },
                'config':{'responsive':True}
            }
        ]

        # Add "ids" to each of the graphs to pass up to the client
        # for templating
        ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]

        # Convert the figures to JSON
        # PlotlyJSONEncoder appropriately converts pandas, datetime, etc
        # objects to their JSON equivalents
        graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)

        return {'graphJSON':graphJSON, 'ids':ids}
