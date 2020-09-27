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

class PeriodForm(colander.MappingSchema):
    id=colander.SchemaNode(
        colander.Integer(),
        widget=deform.widget.HiddenWidget(),missing=None)

    date=colander.SchemaNode(colander.Date(),missing=date.today())
    temperature_time=colander.SchemaNode(colander.Time(),missing=None)
    temperature=colander.SchemaNode(
        colander.Float(),missing=None)

    period_intensity=colander.SchemaNode(
        colander.Integer(),
        widget=deform.widget.SelectWidget(
            values=[(key,value) for (key,value) in period_intensity_choices.items()]
            ),
        missing=None)
    cervical_fluid=colander.SchemaNode(
        colander.Integer(),
        widget=deform.widget.SelectWidget(
            values=[(key,value) for (key,value) in cervical_fluid_choices.items()]),
        missing=None)

    notes=colander.SchemaNode(
        colander.String(),
        widget=deform.widget.TextAreaWidget(),
        missing=None)

class DeleteForm(colander.MappingSchema):
    id=colander.SchemaNode(
        colander.Integer(),
        widget=deform.widget.HiddenWidget(),missing=None)

def appstruct_to_period(dbsession,appstruct,existing_record=None):
    if existing_record:
        period=existing_record
        if period.temperature is None:
            period.temperature=Temperature()
    else:
        period=Period()
        period.temperature=Temperature()

    period.period_intensity=appstruct['period_intensity']
    period.date=appstruct['date']
    period.cervical_fluid_character=appstruct['cervical_fluid']
    period.temperature.temperature=appstruct['temperature']
    if appstruct['temperature_time'] is not None:
        period.temperature.time=datetime.combine(period.date,appstruct['temperature_time'])

    if appstruct['notes'] is not None:
        if period.notes is None:
            period.notes=Note()
        period.notes.date=datetime.combine(appstruct['date'],appstruct['temperature_time'])
        period.notes.text=appstruct['notes']
    else:
        period.notes=None

    return period

class PeriodViews(object):
    def __init__(self,request):
        self.request=request

    def delete_form(self,buttons=['delete','cancel']):
        schema=DeleteForm().bind(
            request=self.request
        )

        return deform.Form(schema,buttons=buttons)

    def period_form(self,buttons=['submit']):
        schema=PeriodForm().bind(
            request=self.request
        )

        return deform.Form(schema,buttons=buttons)

    @view_config(route_name='period_add',renderer='../templates/period_addedit.jinja2')
    def period_add(self):
        form=self.period_form().render()

        dbsession=self.request.dbsession

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.period_form().validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            period=appstruct_to_period(dbsession,appstruct)

            session_person=self.request.dbsession.query(Person).filter(
                Person.id==self.request.session['person_id']).one()

            period.person=session_person
            period.temperature.person=session_person

            dbsession.add(period)

            # Flush dbsession so we can get an id assignment
            dbsession.flush()

            url = self.request.route_url('period_plot')
            return HTTPFound(
                url,
                content_type='application/json',
                charset='',
                text=json.dumps(
                    {'period_id':period.id}
                )
            )

        return dict(form=form,period=None,modified_date=None)

    @view_config(route_name='period_edit',renderer='../templates/period_addedit.jinja2')
    def period_edit(self):
        dbsession=self.request.dbsession

        period_id=int(self.request.matchdict['period_id'])
        period=dbsession.query(Period).filter(Period.id==period_id).one()

        buttons=['submit','delete entry']

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.period_form(buttons=buttons).validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            period=appstruct_to_period(dbsession,appstruct,period)

            session_person=self.request.dbsession.query(Person).filter(
                Person.id==self.request.session['person_id']).one()

            period.person=session_person
            period.temperature.person=session_person

            dbsession.add(period)
            url = self.request.route_url('period_list')
            return HTTPFound(url)
        elif 'delete_entry' in self.request.params:
            url=self.request.route_url('period_delete',
                                       period_id=period.id,
                                       _query=dict(referrer=self.request.url))
            return HTTPFound(url)

        form=self.period_form(
            buttons=buttons
        ).render(dict(
            id=period.id,
            date=period.date,
            temperature_time=period.temperature.time,
            temperature=period.temperature.temperature,
            period_intensity=period.period_intensity,
            cervical_fluid=period.cervical_fluid_character,
            notes=period.notes.text if period.notes else ''
        ))

        modified_dates=[
            period.modified_date,
            period.temperature.modified_date,
            period.notes.modified_date
            if period.notes else None]

        modified_dates=[d for d in modified_dates if d is not None]

        modified_date=max(modified_dates) if len(modified_dates)>0 else None

        return dict(form=form,period=period,modified_date=modified_date)

    @view_config(route_name='period_delete',renderer='../templates/period_delete_confirm.jinja2')
    def period_delete(self):
        dbsession=self.request.dbsession

        period_id=int(self.request.matchdict['period_id'])
        period=dbsession.query(Period).filter(Period.id==period_id).one()

        if 'delete' in self.request.params:
            dbsession.delete(period)
            url=self.request.route_url('period_list')
            return(HTTPFound(url))
        elif 'cancel' in self.request.params:
            referrer=self.request.params.get('referrer',self.request.referrer)
            url=referrer if referrer else self.request.route_url('period_list')
            return HTTPFound(url)

        form=self.delete_form().render(dict(id=period.id))

        return dict(form=form)

    @view_with_header
    @view_config(route_name='period_list',renderer='../templates/period_list.jinja2')
    def period_list(self):
        current_page = int(self.request.params.get("page",1))
        session_person=self.request.dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).one()
        entries=self.request.dbsession.query(Period).filter(
            Period.person==session_person
        ).order_by(Period.date.desc())
        page=SqlalchemyOrmPage(entries,page=current_page,items_per_page=30)
        return dict(
            entries=entries,page=page,
            period_intensity_choices={**period_intensity_choices,1:''},
            cervical_fluid_choices={**cervical_fluid_choices,1:''}
        )

    @view_with_header
    @view_config(route_name='period_plot',renderer='../templates/period_plot.jinja2')
    def period_plot(self):

        import plotly

        import numpy as np

        import pandas as pd

        from sqlalchemy.orm import joinedload
        
        dbsession=self.request.dbsession

        session_person=dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).first()
        query=dbsession.query(Period).filter(
            Period.person==session_person
        ).options(
            joinedload(Period.temperature).load_only(Temperature.temperature)
        ).order_by(Period.date)

        periods=pd.read_sql(query.statement,dbsession.bind)
        periods.period_intensity=periods.period_intensity.fillna(1)

        dates=periods['date']
        
        intensities=periods.period_intensity
        start_inds=(intensities>1)&(intensities.shift(1)==1)
        start_dates=dates[start_inds]

        from .plotly_defaults import default_axis_style

        graphs=[
            {
                'data':[{
                    'x':dates,
                    'y':periods.temperature,
                    'type':'scatter',
                    'mode':'lines+markers',
                    'name':'Temperature',
                    'yaxis':'y2'
                },
                {
                    'x':dates,
                    'y':periods.period_intensity-1,
                    'type':'bar',
                    'marker':{'color':'red'},
                    'name':'Period intensity',
                    'yaxis':'y1'
                },
                {
                    'x':dates,
                    'y':-(periods.cervical_fluid_character-1),
                    'type':'bar',
                    'marker':{'color':'blue'},
                    'name':'Cervical fluid',
                    'yaxis':'y1'
                }],
                'layout':{
                    'plot_bgcolor':'white',
                    'margin':{
                        'l':55,
                        'r':25,
                        'b':50,
                        't':45,
                        'pad':2,
                    },
                    'yaxis':{
                        **default_axis_style,
                        'domain':[0,0.2],
                        'range':[-6,6],
                        'fixedrange':True,
                        **default_axis_style
                    },
                    'yaxis2':{
                        'title':{
                            'text':'Temperature (F)'
                        },
                        'range':[
                            min(periods.temperature.min(),97) if not np.isnan(periods.temperature.min()) else 97,
                            max(periods.temperature.max(),99) if not np.isnan(periods.temperature.max()) else 99
                        ],
                        'domain':[0.2,1],
                        **default_axis_style
                    },
                    'barmode':'overlay',
                    'legend':{
                        'traceorder':'normal',
                        'x':1,
                        'y':1,
                        'xanchor':'right'
                    },
                    'plot_bgcolor': '#E5ECF6',
                    "xaxis": default_axis_style,
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
