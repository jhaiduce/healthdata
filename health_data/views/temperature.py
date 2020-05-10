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

    date=colander.SchemaNode(colander.Date(),missing=date.today())
    time=colander.SchemaNode(colander.Time(),missing=datetime.now().time())
    temperature=colander.SchemaNode(
        colander.Float(),missing=None)

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
                return dict(form=e.render())

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
            temperature=temperature.temperature
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

        from bokeh.layouts import gridplot,layout
        from bokeh.plotting import figure
        from bokeh.embed import components
        from bokeh.models.widgets import Button

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
        
        ptemp=figure(x_axis_type='datetime',width=800,height=400)

        ptemp.y_range.start=min(temperatures.temperature.min(),97) if not np.isnan(temperatures.temperature.min()) else 97
        ptemp.y_range.end=max(temperatures.temperature.max(),99) if not np.isnan(temperatures.temperature.max()) else 99

        ptemp.line(dates,temperatures.temperature),
        ptemp.scatter(dates,temperatures.temperature,marker='circle',size=8,fill_alpha=0)
        ptemp.yaxis.axis_label='Temperature (F)'

        from bokeh.models.callbacks import CustomJS
        from bokeh.events import ButtonClick

        pager_args=dict(source=ptemp)
        pager_code="""
        var xr=source.x_range;
        var oldStart=xr.start
        var oldEnd=xr.end
        var oldRange=oldEnd-oldStart

        var newStart=oldStart+oldRange*step;
        var newEnd=oldEnd+oldRange*step

        xr.start=newStart;
        xr.end=newEnd;
        source.change.emit();
        """
        callback_prev=CustomJS(args={**pager_args,'step':-1},code=pager_code)
        callback_next=CustomJS(args={**pager_args,'step':1},code=pager_code)
        
        button_prev=Button(label='<')
        button_prev.js_on_event(ButtonClick,callback_prev)
        button_next=Button(label='>')
        button_next.js_on_event(ButtonClick,callback_next)

        layout=gridplot([[layout([[button_prev,button_next]])],[ptemp]])
        
        bokeh_script,bokeh_div=components(layout)

        return dict(bokeh_script=bokeh_script,bokeh_div=bokeh_div)
