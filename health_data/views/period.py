from pyramid.view import view_config
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from datetime import date,datetime,timedelta,time
import json

from .showtable import SqlalchemyOrmPage

from ..models.records import Period, period_intensity_choices, cervical_fluid_choices, Temperature, Note

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

        return dict(form=form)

    @view_config(route_name='period_edit',renderer='../templates/period_addedit.jinja2')
    def period_edit(self):
        dbsession=self.request.dbsession

        period_id=int(self.request.matchdict['period_id'])
        period=dbsession.query(Period).filter(Period.id==period_id).one()

        buttons=['submit','delete ride']

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.period_form(buttons=buttons).validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            period=appstruct_to_period(dbsession,appstruct,period)

            dbsession.add(period)
            url = self.request.route_url('period_list')
            return HTTPFound(url)
        elif 'delete_ride' in self.request.params:
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
            notes=period.notes.text or None
        ))

        return dict(form=form)

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

    @view_config(route_name='period_list',renderer='../templates/period_list.jinja2')
    def period_list(self):
        current_page = int(self.request.params.get("page",1))
        entries=self.request.dbsession.query(Period).order_by(Period.date.desc())
        page=SqlalchemyOrmPage(entries,page=current_page,items_per_page=30)
        return dict(
            entries=entries,page=page,
            period_intensity_choices={**period_intensity_choices,1:''},
            cervical_fluid_choices={**cervical_fluid_choices,1:''}
        )

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
        periods.period_intensity=periods.period_intensity.fillna(1)

        dates=periods['date']
        
        intensities=periods.period_intensity
        start_inds=(intensities>1)&(intensities.shift(1)==1)
        start_dates=dates[start_inds]

        ptemp=figure(x_axis_type='datetime',width=800,height=400)
        pcerv_period=figure(plot_width=ptemp.plot_width,x_range=ptemp.x_range,x_axis_type='datetime',height=100)

        ptemp.y_range.start=min(periods.temperature.min(),97) if not np.isnan(periods.temperature.min()) else 97
        ptemp.y_range.end=max(periods.temperature.max(),99) if not np.isnan(periods.temperature.max()) else 99

        ptemp.line(dates,periods.temperature),
        ptemp.scatter(dates,periods.temperature,marker='circle',size=8,fill_alpha=0)
        ptemp.yaxis.axis_label='Temperature (F)'
        pcerv_period.vbar(x=dates,width=timedelta(1),top=-(periods.cervical_fluid_character-1))
        pcerv_period.vbar(x=dates,width=timedelta(1),top=periods.period_intensity-1,color='red')

        from bokeh.models.callbacks import CustomJS
        from bokeh.events import ButtonClick

        pager_args=dict(source=ptemp,start_dates=start_dates)
        pager_code="""
        var xr=source.x_range;
        var oldStart=xr.start
        newStartIndex=start_dates.findIndex(function(date){
          return date>(oldStart-Math.abs(step));
        });
        if(oldStart>start_dates[start_dates.length-1]) newStartIndex=start_dates.length-1;
        if(step<0 && start_dates[Math.max(newStartIndex,0)]>(oldStart+step)) newStartIndex=Math.max(newStartIndex-1,0);
        if(step>=0 && start_dates[newStartIndex]<(oldStart+step)) newStartIndex+=1;
        newStartIndex=Math.max(Math.min(newStartIndex,start_dates.length-1),0);
        newStart=start_dates[newStartIndex];
        xr.start=newStart;
        xr.end=newStart+40*3600*24*1000;
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
