from pyramid.view import view_config
from pyramid.events import subscriber
import colander
import deform.widget
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
import json

from ..models.records import Temperature, Note
from ..models.people import Person

from .header import view_with_header

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

    return obj.notes.text if obj.notes else '-'

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def finalize_temperature_fields(event):
    """
    Post-process an automatically deserialized Temperature object
    """

    if isinstance(event.obj,Temperature):

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

class TemperatureCrudViews(IndividualRecordCRUDView,CRUDView):

    model=Temperature

    schema=SQLAlchemySchemaNode(
        Temperature,
        includes=['date','time','temperature',notes_schema],
        overrides={
            'notes':{
                'widget':deform.widget.TextAreaWidget()
            },
        }
    )
    title='temperature'
    url_path='/temperature'
    list_display=['time','temperature',notes]

    def get_list_query(self):
       query=super(TemperatureCrudViews,self).get_list_query()

       return query.order_by(Temperature.time.desc())

    def dictify(self,obj):
        """
        Serialize a MenstrualCupFill object to a dict for CRUD view
        """

        appstruct=super(TemperatureCrudViews,self).dictify(obj)

        if obj.notes is not None:
           appstruct['notes']=obj.notes.text

        return appstruct

class TemperatureViews(object):
    def __init__(self,request):
        self.request=request

    @view_with_header
    @view_config(route_name='temperature_plot',renderer='../templates/temperature_plot.jinja2')
    def temperature_plot(self):

        import plotly

        import numpy as np

        import pandas as pd

        from sqlalchemy.orm import joinedload

        dbsession=self.request.dbsession

        session_person=dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).first()
        query=dbsession.query(Temperature).filter(
            Temperature.person==session_person
        ).order_by(Temperature.time)
        temperatures=pd.read_sql(query.statement,dbsession.bind)
        temperatures=temperatures.dropna(subset=['time'])
        dates=temperatures['time']
        dates=dates.apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))

        from .plotly_defaults import default_axis_style, get_axis_range

        graphs=[
            {
                'data':[{
                    'x':dates,
                    'y':temperatures.temperature,
                    'type':'scatter',
                    'mode':'lines+markers',
                    'name':'Temperature'
                }],
                'layout':{
                    'margin':{
                        'l':55,
                        'r':25,
                        'b':50,
                        't':45,
                        'pad':2,
                    },
                    'yaxis':{
                        **default_axis_style,
                        'title':{
                            'text':'Temperature (F)'
                        }
                    },
                    'plot_bgcolor': '#E5ECF6',
                    "xaxis": {
                        'range': get_axis_range(temperatures['time'],
                                                start_idx=-120),
                        **default_axis_style
                    },
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
