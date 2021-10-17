from pyramid.events import subscriber
from pyramid.view import view_config
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent
from ..models import HeightWeight, Note
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
from .header import view_with_header
from ..models.people import Person
from colanderalchemy import SQLAlchemySchemaNode
import colander
import deform

def bmi(obj):
   if obj.bmi is None: return '-'
   return '{:0.2f}'.format(obj.bmi)

notes_schema = colander.SchemaNode(colander.String(),
                                   name='notes',
                                   widget=deform.widget.TextAreaWidget(),
                                   missing=None)

def notes(obj):
    """
    Return the text of a notes object (for display in the
    HeightWeightViews table)
    """

    return obj.text

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def finalize_heightweight_fields(event):
    """
    Post-process an automatically deserialized HeightWeight object
    """

    if isinstance(event.obj,HeightWeight):

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

class HeightWeightCrudViews(IndividualRecordCRUDView,CRUDView):
   model=HeightWeight
   schema=SQLAlchemySchemaNode(
       HeightWeight,
       includes=['time','weight','height',notes_schema]
   )
   url_path = '/height_weight'
   list_display=('time','weight','height',bmi,notes)

   def get_list_query(self):
       query=super(HeightWeightCrudViews,self).get_list_query()
       query=query.outerjoin(HeightWeight.notes)
       query=query.with_entities(
          HeightWeight.id,
          HeightWeight.time,HeightWeight.weight,
          HeightWeight.height,HeightWeight.bmi,Note.text)

       return query.order_by(HeightWeight.time.desc())

   def dictify(self,obj):
        """
        Serialize a HeightWeightCrudViews object to a dict
        """

        # Default serialization for built-in fields
        appstruct=super(HeightWeightCrudViews,self).dictify(obj)

        if obj.notes is not None:
            appstruct['notes']=obj.notes.text

        return appstruct

class HeightWeightViews(object):
    def __init__(self,request):
        self.request=request

    @view_with_header
    @view_config(route_name='weight_plot',renderer='../templates/weight_plot.jinja2')
    def plot(self):

        import json
        import plotly

        import pandas as pd
        import numpy as np

        dbsession=self.request.dbsession

        session_person=dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).first()
        query=dbsession.query(HeightWeight).with_entities(
           HeightWeight.time, HeightWeight.weight, HeightWeight.height, HeightWeight.bmi
        ).filter(
            HeightWeight.person==session_person
        ).order_by(HeightWeight.time)

        weights=pd.read_sql(query.statement,dbsession.bind)
        weights=weights.dropna(subset=['time'])
        dates=weights['time']
        dates=dates.apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))

        from .plotly_defaults import default_axis_style

        graphs=[
            {
                'data':[
                   {
                      'x':list(dates),
                      'y':list(weights.weight),
                      'type':'scatter',
                      'mode':'lines+markers',
                      'name':'Weight',
                      'yaxis':'y3'
                   },
                   {
                      'x':list(dates),
                      'y':list(weights.height),
                      'type':'scatter',
                      'mode':'lines+markers',
                      'name':'Height',
                      'yaxis':'y2'
                   },
                   {
                      'x':list(dates),
                      'y':list(weights.bmi),
                      'type':'scatter',
                      'mode':'lines+markers',
                     'name':'BMI'
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
                    'yaxis3':{
                        **default_axis_style,
                        'title':{
                            'text':'Weight (kg)'
                        },
                       'domain':[0.6,1]
                    },
                    'yaxis2':{
                        **default_axis_style,
                        'title':{
                            'text':'Height (in)'
                        },
                       'domain':[0.32,0.56]
                    },
                    'yaxis':{
                        **default_axis_style,
                        'title':{
                            'text':'BMI (kg/m<sup>2</sup>)'
                        },
                       'domain':[0,0.28]
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
