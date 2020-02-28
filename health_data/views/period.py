from pyramid.view import view_config
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from datetime import date,datetime,timedelta

from ..models.records import Period, period_intensity_choices, cervical_fluid_choices, Temperature

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


def appstruct_to_period(dbsession,appstruct,existing_record=None):
    if existing_record:
        period=existing_record
    else:
        period=Period()
        period.temperature=Temperature()

    period.period_intensity=appstruct['period_intensity']
    period.date=appstruct['date']
    period.cervical_fluid_character=appstruct['cervical_fluid']
    period.temperature.temperature=appstruct['temperature']
    if appstruct['temperature_time'] is not None:
        period.temperature.time=datetime.combine(period.date,appstruct['temperature_time'])

    return period

class PeriodViews(object):
    def __init__(self,request):
        self.request=request

    @property
    def period_form(self):
        schema=PeriodForm().bind(
            request=self.request
        )

        return deform.Form(schema,buttons=['submit'])

    @view_config(route_name='period_add',renderer='../templates/period_addedit.jinja2')
    def period_add(self):
        form=self.period_form.render()

        dbsession=self.request.dbsession

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.period_form.validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            period=appstruct_to_period(dbsession,appstruct)
            dbsession.add(period)
            url = self.request.route_url('period_plot')
            return HTTPFound(url)

        return dict(form=form)

    @view_config(route_name='period_plot',renderer='../templates/period_plot.jinja2')
    def period_plot(self):

        from bokeh.layouts import gridplot,layout
        from bokeh.plotting import figure
        from bokeh.embed import components
        from bokeh.models.widgets import Button

        import numpy as np

        import pandas as pd

        from sqlalchemy.orm import joinedload
        
        dbsession=self.request.dbsession

        query=dbsession.query(Period).options(
            joinedload(Period.temperature).load_only(Temperature.temperature)
        ).order_by(Period.date)
        periods=pd.read_sql(query.statement,dbsession.bind)

        dates=periods['date']
        
        ptemp=figure(x_axis_type='datetime',width=800,height=400)
        pcerv_period=figure(plot_width=ptemp.plot_width,x_range=ptemp.x_range,x_axis_type='datetime',height=100)

        ptemp.y_range.start=min(periods.temperature.min(),97)
        ptemp.y_range.end=max(periods.temperature.max(),99)

        ptemp.line(dates,periods.temperature),
        ptemp.scatter(dates,periods.temperature,marker='circle',size=8,fill_alpha=0)
        ptemp.yaxis.axis_label='Temperature (F)'
        pcerv_period.vbar(x=dates,width=timedelta(1),top=-periods.cervical_fluid_character)
        pcerv_period.vbar(x=dates,width=timedelta(1),top=periods.period_intensity)

        from bokeh.models.callbacks import CustomJS
        from bokeh.events import ButtonClick

        pager_args=dict(source=ptemp)
        pager_code="""
        var xr=source.x_range;
        xr.start+=step;
        xr.end+=step;
        source.change.emit();
        """
        callback_prev=CustomJS(args={**pager_args,'step':-3600*24*1000},code=pager_code)
        callback_next=CustomJS(args={**pager_args,'step':3600*24*1000},code=pager_code)
        
        button_prev=Button(label='<')
        button_prev.js_on_event(ButtonClick,callback_prev)
        button_next=Button(label='>')
        button_next.js_on_event(ButtonClick,callback_next)

        layout=gridplot([[layout([[button_prev,button_next]])],[ptemp],[pcerv_period]])
        
        bokeh_script,bokeh_div=components(layout)

        return dict(bokeh_script=bokeh_script,bokeh_div=bokeh_div)
