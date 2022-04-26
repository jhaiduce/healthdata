from pyramid.view import view_config

from ..models import Symptom,SymptomType,Note
from ..models.people import Person

from .symptom import get_symptomtype_by_name

from .header import view_with_header

class ContractionsViews(object):

    def __init__(self,request):
        self.request=request

    @view_with_header
    @view_config(route_name='contractions_plot',renderer='../templates/generic_plot.jinja2')
    def contractions_plot(self):
        
        import plotly

        import numpy as np

        import pandas as pd

        import json

        dbsession=self.request.dbsession

        contraction_symptomtype=get_symptomtype_by_name(dbsession,'Contraction')

        session_person=dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).first()
        query=dbsession.query(Symptom).filter(
            Symptom.person==session_person,
            Symptom.start_time!=None,
            Symptom.symptomtype==contraction_symptomtype
        ).order_by(Symptom.start_time)
        symptoms=pd.read_sql(query.statement,dbsession.bind)
        start_times=symptoms.start_time
        start_times=pd.to_datetime(start_times, format='%Y-%m-%d %H:%M:%S')
        end_times=symptoms.end_time
        end_times=pd.to_datetime(end_times, format='%Y-%m-%d %H:%M:%S')

        time_between=(start_times-end_times.fillna(start_times).shift()).dt.total_seconds()/60

        duration=(end_times - start_times).dt.total_seconds()/60

        from .plotly_defaults import default_axis_style

        graphs=[
            {
                'data':[{
                    'x':start_times,
                    'y':time_between,
                    'type':'scatter',
                    'mode':'lines+markers',
                    'name':'Time between'
                },{
                    'x':start_times,
                    'y':duration,
                    'type':'scatter',
                    'mode':'lines+markers',
                    'name':'Duration'
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
                            'text':'Time (minutes)'
                        }
                    },
                    'plot_bgcolor': '#E5ECF6',
                    'xaxis': default_axis_style,
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
