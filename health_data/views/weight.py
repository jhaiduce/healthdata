from pyramid.view import view_config
from .crud import CRUDView
from ..models import Weight
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
from .header import view_with_header
from ..models.people import Person

class WeightCrudViews(IndividualRecordCRUDView,CRUDView):
   model=Weight
   schema=SQLAlchemySchemaNode(
       Weight,
       includes=['time','weight']
   )
   url_path = '/weight'
   list_display=('time','weight',)

   def get_list_query(self):
       query=super(WeightCrudViews,self).get_list_query()

       return query.order_by(Weight.time.desc())

class WeightViews(object):
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
        query=dbsession.query(Weight).filter(
            Weight.person==session_person
        ).order_by(Weight.time)

        weights=pd.read_sql(query.statement,dbsession.bind)
        weights=weights.dropna(subset=['time'])
        dates=weights['time']
        dates=dates.apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))

        from .plotly_defaults import default_axis_style

        graphs=[
            {
                'data':[{
                    'x':list(dates),
                    'y':list(weights.weight),
                    'type':'scatter',
                    'mode':'lines+markers',
                    'name':'Weight'
                }],
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
                            'text':'Weight (kg)'
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
