from pyramid.view import view_config
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from datetime import date,datetime,timedelta,time
import json

from .showtable import SqlalchemyOrmPage

from ..models.records import Period, period_intensity_choices, cervical_fluid_choices, Temperature, Note
from ..models.people import Person

from .header import view_with_header

class TemperatureForm(colander.MappingSchema):
    id=colander.SchemaNode(
        colander.Integer(),
        widget=deform.widget.HiddenWidget(),missing=None)

    date=colander.SchemaNode(colander.Date())
    time=colander.SchemaNode(colander.Time())
    temperature=colander.SchemaNode(
        colander.Float(),missing=None)

    notes=colander.SchemaNode(
        colander.String(),
        widget=deform.widget.TextAreaWidget(),
        missing=None)

class DeleteForm(colander.MappingSchema):
    id=colander.SchemaNode(
        colander.Integer(),
        widget=deform.widget.HiddenWidget(),missing=None)

def appstruct_to_temperature(dbsession,appstruct,existing_record=None):
    if existing_record:
        temperature=existing_record
    else:
        temperature=Temperature()

    temperature.temperature=appstruct['temperature']
    temperature.time=datetime.combine(appstruct['date'],appstruct['time'])

    if appstruct['notes'] is not None:
        if temperature.notes is None:
            temperature.notes=Note()

        temperature.notes.date=temperature.time
        temperature.notes.text=appstruct['notes']
    else:
        temperature.notes=None

    return temperature

class TemperatureViews(object):
    def __init__(self,request):
        self.request=request

    def delete_form(self,buttons=['delete','cancel']):
        schema=DeleteForm().bind(
            request=self.request
        )

        return deform.Form(schema,buttons=buttons)

    def temperature_form(self,buttons=['submit']):
        schema=TemperatureForm().bind(
            request=self.request
        )

        return deform.Form(schema,buttons=buttons)

    @view_config(route_name='temperature_add',renderer='../templates/temperature_addedit.jinja2')
    def temperature_add(self):
        form=self.temperature_form().render()

        dbsession=self.request.dbsession

        if 'submit' in self.request.params:
            controls=self.request.POST.items()

            try:
                appstruct=self.temperature_form().validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render(),temperature=None,modified_date=None)

            temperature=appstruct_to_temperature(dbsession,appstruct)

            session_person=self.request.dbsession.query(Person).filter(
                Person.id==self.request.session['person_id']).one()

            temperature.person=session_person

            dbsession.add(temperature)

            # Flush dbsession so we can get an id assignment
            dbsession.flush()

            url = self.request.route_url('temperature_list')
            return HTTPFound(
                url,
                content_type='application/json',
                charset='',
                text=json.dumps(
                    {'temperature_id':temperature.id}
                )
            )

        return dict(form=form,temperature=None,modified_date=None)

    @view_config(route_name='temperature_edit',renderer='../templates/temperature_addedit.jinja2')
    def temperature_edit(self):
        dbsession=self.request.dbsession

        temperature_id=int(self.request.matchdict['temperature_id'])
        temperature=dbsession.query(Temperature).filter(Temperature.id==temperature_id).one()

        buttons=['submit','delete entry']

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.temperature_form(buttons=buttons).validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            temperature=appstruct_to_temperature(dbsession,appstruct,temperature)

            session_person=self.request.dbsession.query(Person).filter(
                Person.id==self.request.session['person_id']).one()

            temperature.person=session_person

            dbsession.add(temperature)
            url = self.request.route_url('temperature_list')
            return HTTPFound(url)
        elif 'delete_entry' in self.request.params:
            url=self.request.route_url('temperature_delete',
                                       temperature_id=temperature.id,
                                       _query=dict(referrer=self.request.url))
            return HTTPFound(url)

        form=self.temperature_form(
            buttons=buttons
        ).render(dict(
            id=temperature.id,
            date=temperature.time.date(),
            time=temperature.time.time(),
            temperature=temperature.temperature,
            notes=temperature.notes.text if temperature.notes else ''
        ))

        modified_date=temperature.modified_date

        return dict(form=form,temperature=temperature,modified_date=modified_date)

    @view_config(route_name='temperature_delete',renderer='../templates/temperature_delete_confirm.jinja2')
    def temperature_delete(self):
        dbsession=self.request.dbsession

        temperature_id=int(self.request.matchdict['temperature_id'])
        temperature=dbsession.query(Temperature).filter(Temperature.id==temperature_id).one()

        referrer=self.request.params.get('referrer',self.request.referrer)
        url=referrer if referrer else self.request.route_url('temperature_list')

        if 'delete' in self.request.params:
            dbsession.delete(temperature)
            return(HTTPFound(self.request.route_url('temperature_list')))
        elif 'cancel' in self.request.params:
            return HTTPFound(url)

        form=self.delete_form().render(dict(id=temperature.id))

        return dict(form=form)

    @view_with_header
    @view_config(route_name='temperature_list',renderer='../templates/temperature_list.jinja2')
    def temperature_list(self):
        current_page = int(self.request.params.get("page",1))
        session_person=self.request.dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).one()
        entries=self.request.dbsession.query(Temperature).filter(
            Temperature.person==session_person
        ).order_by(Temperature.time.desc())
        page=SqlalchemyOrmPage(entries,page=current_page,items_per_page=30)
        return dict(
            entries=entries,page=page
        )

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
