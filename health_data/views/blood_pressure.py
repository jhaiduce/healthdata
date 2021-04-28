from pyramid.events import subscriber
from pyramid.view import view_config
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent
from ..models import BloodPressure, HeartRate
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
from .header import view_with_header
from ..models.people import Person
import colander

def heart_rate(obj):

   if obj.heart_rate is None or obj.heart_rate.rate is None:
      return '-'

   return '{:0.1f}'.format(obj.heart_rate.rate)

class BloodPressureCrudViews(IndividualRecordCRUDView,CRUDView):
    model=BloodPressure
    schema=SQLAlchemySchemaNode(
       BloodPressure,
       includes=[
          'time',
          'systolic',
          'diastolic',
          colander.SchemaNode(
             colander.Float(),
             name='heart_rate',
             title='Heart rate',
             missing=None
          )
       ]
    )

    title='blood pressure'
    url_path = '/blood_pressure'
    list_display=('time','systolic','diastolic',heart_rate)

    def get_list_query(self):
       query=super(BloodPressureCrudViews,self).get_list_query()

       return query.order_by(BloodPressure.time.desc())

    def dictify(self,obj):

       appstruct=super(BloodPressureCrudViews,self).dictify(obj)

       if obj.heart_rate is not None:
          appstruct['heart_rate'] = obj.heart_rate.rate

       return appstruct

@subscriber(ViewDbInsertEvent, ViewDbUpdateEvent)
def finalize_blood_pressure_fields(event):

    """
    Post-process an automatically deserialized BloodPressure object
    """

    if isinstance(event.obj,BloodPressure):

       if event.obj.heart_rate is None:
          event.obj.heart_rate=HeartRate()

       event.obj.heart_rate.rate = event.appstruct['heart_rate']
       event.obj.heart_rate.time = event.appstruct['time']

class BloodPressureViews(object):
    def __init__(self,request):
        self.request=request

    @view_with_header
    @view_config(route_name='blood_pressure_plot',renderer='../templates/blood_pressure_plot.jinja2')
    def plot(self):

        import json
        import plotly

        import pandas as pd
        import numpy as np

        dbsession=self.request.dbsession

        session_person=dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).first()
        query=dbsession.query(BloodPressure).filter(
            BloodPressure.person==session_person
        ).order_by(BloodPressure.time)

        blood_pressure=pd.read_sql(query.statement,dbsession.bind)
        blood_pressure=blood_pressure.dropna(subset=['time'])
        dates=blood_pressure['time']
        dates=dates.apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))

        from .plotly_defaults import default_axis_style

        graphs=[
            {
                'data':[
                   {
                    'x':list(dates),
                    'y':list(blood_pressure.systolic),
                    'type':'scatter',
                    'mode':'lines+markers',
                    'name':'Systolic'
                   },
                   {
                    'x':list(dates),
                    'y':list(blood_pressure.diastolic),
                    'type':'scatter',
                    'mode':'lines+markers',
                    'name':'Diastolic'
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
                    'legend':{
                        'traceorder':'normal',
                        'x':1,
                        'y':1,
                        'xanchor':'right'
                    },
                    'yaxis':{
                        **default_axis_style,
                        'title':{
                            'text':'Blood pressure (mm hg)'
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

