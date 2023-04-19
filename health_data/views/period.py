from pyramid.view import view_config
from pyramid.events import subscriber
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound
from datetime import date,datetime,timedelta,time
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
import json

from ..models.records import Period, period_intensity_choices, cervical_fluid_choices, lh_surge_choices, Temperature, Note, MenstrualCupFill, AbsorbentWeights
from ..models.people import Person

from .header import view_with_header

from sqlalchemy.sql import func

# Notes is a foreign key reference to the notes table. Since we
# only want to expose one field of notes, we declare a custom SchemaNode
# for it
notes_schema = colander.SchemaNode(colander.String(),
                                   name='notes',
                                   widget=deform.widget.TextAreaWidget(),
                                   missing=None)

# Temperature is a foreign key reference to the temperature table. Since we
# only want to expose one field of notes, we declare a custom SchemaNode
# for it
temperature_schema = colander.SchemaNode(colander.Float(),
                                   name='temperature',
                                   missing=None)

# Temperature time is a foreign key reference to the temperature table. Since we
# only want to expose one field of notes, we declare a custom SchemaNode
# for it
temperature_time_schema = colander.SchemaNode(colander.Time(),
                                   name='temperature_time',
                                   missing=None)

def notes(obj):
    """
    Return the text of a notes object (for display in the SymptomViews table)
    """

    return obj.notes.text if obj.notes else '-'

def temperature(obj):
    """
    Return the text of a notes object (for display in the SymptomViews table)
    """

    return obj.temperature.temperature if obj.temperature else ''

def period_intensity(obj):
    if obj.period_intensity==1: return ''
    return period_intensity_choices.get(obj.period_intensity,'')

def cervical_fluid(obj):
    if obj.cervical_fluid_character==1: return ''
    return cervical_fluid_choices.get(obj.cervical_fluid_character,'')

def period_flow(obj):
    return obj.total_flow

def lh_surge(obj):
    return {2:'Negative',3:'Positive'}.get(obj.lh_surge,'')

def get_period_data(dbsession,session_person):
    from sqlalchemy.orm import joinedload
    import pandas as pd

    query=dbsession.query(Period).filter(
        Period.person==session_person
    ).options(
        joinedload(Period.temperature).load_only(Temperature.temperature)
    ).order_by(func.coalesce(
        Period.date,
        Period.modified_date
    ))

    periods=pd.read_sql(query.statement,dbsession.bind)
    periods.period_intensity=periods.period_intensity.fillna(1)

    return periods

def periods_postprocess(periods):

    import pandas as pd

    dates=pd.to_datetime(periods['date'])
    periods['dates']=dates

    if len(dates)>0:
        all_dates=pd.date_range(dates[0],dates[len(dates)-1])
        periods=periods.dropna(subset=['dates'])
        periods=periods.set_index(periods.dates)
        periods=periods[~periods.index.duplicated()]
        periods=periods.reindex(all_dates)
        periods.dates=periods.index
        periods=periods.reset_index()
        periods=periods.dropna(subset=['dates'])
    periods.period_intensity=periods.period_intensity.fillna(value=1)

    return periods

def get_period_starts(periods):

    import pandas as pd

    previous_periods=periods.period_intensity.rolling(3)
    intensities=pd.Series(periods.period_intensity)
    cervical_fluid=pd.Series(periods.cervical_fluid_character.fillna(1)).rolling(3)
    start_inds=(intensities>1)&(intensities.shift(1)==1)&((intensities>2)|(intensities.shift(-1)>2)|(intensities.shift(-2)>2))&(previous_periods.median()==1)&(cervical_fluid.max().shift(-1)==1)
    start_dates=periods.dates[start_inds]

    return start_inds, start_dates

def get_temperature_rise(periods):
    smoothtemp=periods.temperature.rolling(10).median()
    hightemp=periods.temperature.rolling(10).quantile(0.75)
    temperature_rise_inds=(periods.temperature-hightemp >= 0.2) & (periods.temperature - periods.temperature.shift(1) > 0)
    temperature_rise_dates = periods.dates[temperature_rise_inds]

    return temperature_rise_inds, temperature_rise_dates

def get_ovulations(periods):

    import pandas as pd

    cervical_fluid=pd.Series(periods.cervical_fluid_character)
    ovulation_inds=(cervical_fluid>1)&(cervical_fluid.shift(-1)==1)
    ovulation_dates=periods.dates[ovulation_inds]

    return ovulation_inds, ovulation_dates

def get_ovulations_with_temperature_rise(periods,ovulation_inds,temperature_rise_inds,inverse=False):

    temperature_rise_following=(temperature_rise_inds|temperature_rise_inds.shift(-1)|temperature_rise_inds.shift(-2))
    if inverse:
        ovulation_inds=ovulation_inds&(~temperature_rise_following)
    else:
        ovulation_inds=ovulation_inds&temperature_rise_following
    ovulation_dates=periods.dates[ovulation_inds]

    return ovulation_inds, ovulation_dates,

def sea_var_data(var,epoch_inds,window=45):

    import numpy as np

    sea_data=np.empty([len(epoch_inds),window*2])

    for i,epoch_ind in enumerate(epoch_inds):

        sea_data[i,:]=var[epoch_ind-window:epoch_ind+window]

    return sea_data

def sum_hats(df,times_left='time_before',times_right='time_after',sum_field='flow_rate',offset=timedelta(seconds=1)):

    import pandas as pd

    times=pd.concat([df[times_left],df[times_right],df[times_right]+offset]).drop_duplicates().sort_values()

    total=pd.DataFrame({
        sum_field:pd.Series([0.0]*len(times),index=times.values)
    })

    for idx,row in df.iterrows():
        hat_times=pd.Series([
            times.min()-offset,
            row[times_left],
            row[times_right],
            row[times_right]+offset,
            times.max()])

        hat=pd.DataFrame({
            sum_field:pd.Series([0.0,row[sum_field],row[sum_field],0.0,0.0],
                                 index=hat_times)
        })
        hat=hat.loc[~hat.index.duplicated(),:]
        hat=hat.reindex(times).fillna(method='ffill').fillna(0)
        total=total+hat

    return total

def insert_gaps(df,gap_size=timedelta(days=1),offset=timedelta(seconds=1),fill_value=0,append_at_end=True,fill_field='flow_rate'):
    """
    Insert values in a dataframe at the beginning of each interval longer than gap_size without data
    """

    import pandas as pd
    import numpy as np

    times=df.index.to_series()
    is_gap=(times.diff(periods=-1)<-gap_size),
    gap_times=times.loc[is_gap]
    insert_times=gap_times.dropna()+offset
    if len(insert_times)>0:
        df=df.append(pd.DataFrame(
            {
                fill_field:pd.Series([fill_value]*len(insert_times),
                                      index=insert_times.values)
            }
        ))
    if len(times)>0 and append_at_end:
        df=df.append(pd.DataFrame(
            {
                fill_field:pd.Series([fill_value],
                                     index=[times.values.max()+np.timedelta64(offset)])
            }
        ))

    return df

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def finalize_period_fields(event):
    """
    Post-process an automatically deserialized Temperature object
    """

    if isinstance(event.obj,Period):

        # Store the notes field
        if event.appstruct['notes'] is not None:

            if event.obj.notes is None:
                # Create a new notes object
                event.obj.notes=Note()

            # Set/update the notes properties
            if event.appstruct['temperature_time'] is not None:
                event.obj.notes.date=datetime.combine(
                    event.obj.date,event.appstruct['temperature_time'])
            else:
                event.obj.notes.date=datetime.combine(event.obj.date,time())

            event.obj.notes.text=event.appstruct['notes']

        else:

            event.obj.notes=None

        if event.obj.temperature is None:
            event.obj.temperature=Temperature()

        event.obj.temperature.temperature=event.appstruct['temperature']
        if event.appstruct['temperature_time'] is not None:
            event.obj.temperature.time=datetime.combine(
                event.obj.date,event.appstruct['temperature_time'])
        else:
            event.obj.temperature.time=datetime.combine(
                event.obj.date,time())

class PeriodCrudViews(IndividualRecordCRUDView,CRUDView):

    model=Period

    schema=SQLAlchemySchemaNode(
        Period,
        includes=['date',temperature_time_schema,temperature_schema,'period_intensity','cervical_fluid_character','lh_surge',notes_schema],
        overrides={
            'period_intensity':{
                'widget':deform.widget.SelectWidget(
                    values=[
                        (key,value)
                        for (key,value) in period_intensity_choices.items()]
                )
            },
            'cervical_fluid_character':{
                'widget':deform.widget.SelectWidget(
                    values=[
                        (key,value)
                        for (key,value) in cervical_fluid_choices.items()
                    ])
            },
            'notes':{
                'widget':deform.widget.TextAreaWidget()
            },
        }
    )
    title='period'
    url_path='/period'
    list_display=['date',temperature,period_intensity,period_flow,cervical_fluid,lh_surge,notes]

    def dictify(self,obj):
        """
        Serialize a Period object to a dict for CRUD view
        """

        appstruct=super(PeriodCrudViews,self).dictify(obj)

        if obj.notes is not None:
           appstruct['notes']=obj.notes.text

        if obj.temperature is not None:
           appstruct['temperature']=obj.temperature.temperature
           appstruct['temperature_time']=obj.temperature.time

        return appstruct

    def get_list_query(self):
       query=super(PeriodCrudViews,self).get_list_query()

       return query.order_by(Period.date.desc())

class PeriodViews(object):
    def __init__(self,request):
        self.request=request

    @view_with_header
    @view_config(route_name='period_plot',renderer='../templates/period_plot.jinja2')
    def period_plot(self):

        import plotly

        import numpy as np

        import pandas as pd

        dbsession=self.request.dbsession

        session_person=dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).first()

        periods=get_period_data(dbsession,session_person)
        periods=periods_postprocess(periods)

        dates=periods.dates

        intensities=periods.period_intensity

        start_inds, start_dates=get_period_starts(periods)

        cervical_fluid=pd.Series(periods.cervical_fluid_character)

        ovulation_inds, ovulation_dates = get_ovulations(periods)
        temperature_rise_inds, temperature_rise_dates=get_temperature_rise(periods)
        ovulation_with_temp_inds, ovulation_with_temp_dates = get_ovulations_with_temperature_rise(periods,ovulation_inds,temperature_rise_inds)

        menstrual_cup_query=dbsession.query(MenstrualCupFill).with_entities(
            MenstrualCupFill.insertion_time,
            MenstrualCupFill.removal_time,
            MenstrualCupFill.flow_rate
        ).filter(
            MenstrualCupFill.person==session_person
        ).order_by(MenstrualCupFill.removal_time)

        menstrual_cup_flow=pd.read_sql(
            menstrual_cup_query.statement,dbsession.bind)

        menstrual_cup_flow.insertion_time=pd.to_datetime(menstrual_cup_flow.insertion_time)

        # Separate dataframe for insertion
        menstrual_cup_insertion=menstrual_cup_flow[['insertion_time','flow_rate']]
        menstrual_cup_insertion=menstrual_cup_insertion.rename(
            columns={'insertion_time':'time'})

        # Separate dataframe for removal
        menstrual_cup_removal=menstrual_cup_flow[['removal_time','flow_rate']]
        menstrual_cup_removal=menstrual_cup_removal.rename(
            columns={'removal_time':'time'})
        menstrual_cup_removal.time-=timedelta(seconds=1)

        # Interleave insertion and removal
        menstrual_cup_flow=pd.concat(
            [menstrual_cup_insertion,menstrual_cup_removal]
        ).dropna(subset=['time']).set_index('time').sort_index()

        absorbent_query=dbsession.query(AbsorbentWeights).with_entities(
            AbsorbentWeights.time_before_inferred,
            AbsorbentWeights.time_after,
            AbsorbentWeights.flow_rate
        ).filter(
            AbsorbentWeights.person==session_person
        ).order_by(AbsorbentWeights.time_after)

        absorbent_flow=pd.read_sql(
            absorbent_query.statement,dbsession.bind)

        absorbent_flow.time_before_inferred=pd.to_datetime(absorbent_flow.time_before_inferred)

        absorbent_flow=absorbent_flow.dropna(subset=['time_before_inferred'])

        absorbent_flow=sum_hats(absorbent_flow,times_left='time_before_inferred')

        absorbent_flow=insert_gaps(absorbent_flow).sort_index()
        menstrual_cup_flow=insert_gaps(menstrual_cup_flow).sort_index()

        flow_times=pd.concat([
            absorbent_flow.index.to_series(),menstrual_cup_flow.index.to_series(),dates
        ]).drop_duplicates().sort_values().reset_index(drop=True)

        absorbent_flow=absorbent_flow.groupby(absorbent_flow.index).last().reindex(flow_times).fillna(method='ffill').fillna(0)
        menstrual_cup_flow=menstrual_cup_flow.groupby(menstrual_cup_flow.index).last().reindex(flow_times).fillna(method='ffill').fillna(0)

        if len(flow_times)>0:
            # Get the total flow for each point in time
            total_flow=pd.Series((absorbent_flow.flow_rate+menstrual_cup_flow.flow_rate),index=flow_times)

            # Get total flow for each day
            daily_flow=(total_flow.groupby(total_flow.index.date).sum())

            # Find dates with nonzero flow
            nonzero_flow=(daily_flow[dates]!=0).values

            # Zero out subjective intensities on days with nonzero flow
            # (cleans up chart visually)
            intensities.loc[nonzero_flow]=1

        from .plotly_defaults import default_axis_style, get_axis_range

        graphs=[
            {
                'data':[{
                    'x':dates,
                    'y':periods.temperature,
                    'type':'scatter',
                    'mode':'lines+markers',
                    'name':'Temperature',
                    'showlegend':False,
                    'yaxis':'y2'
                },
                {
                    'x':start_dates,
                    'y':[0]*len(start_dates),
                    'type':'scatter',
                    'mode':'markers',
                    'name':'Period start',
                    'showlegend':False,
                    'yaxis':'y1'
                },
                {
                    'x':ovulation_dates,
                    'y':[1]*len(ovulation_dates),
                    'type':'scatter',
                    'mode':'markers',
                    'name':'Ovulation (cervical fluid)',
                    'showlegend':False,
                    'yaxis':'y1'
                },
                {
                    'x':ovulation_with_temp_dates,
                    'y':[0]*len(ovulation_with_temp_dates),
                    'type':'scatter',
                    'mode':'markers',
                    'name':'Ovulation (combined)',
                    'showlegend':False,
                    'yaxis':'y1'
                },
                {
                    'x':temperature_rise_dates,
                    'y':[0.5]*len(temperature_rise_dates),
                    'type':'scatter',
                    'mode':'markers',
                    'name':'Temperature rise',
                    'showlegend':False,
                    'yaxis':'y1'
                },
                {
                    'x':dates,
                    'y':intensities-1,
                    'type':'bar',
                    'marker':{'color':'red'},
                    'name':'Period intensity',
                },
                {
                    'x':dates,
                    'y':-(periods.cervical_fluid_character-1),
                    'type':'bar',
                    'marker':{'color':'blue'},
                    'name':'Cervical fluid',
                },
                {
                    'x':absorbent_flow.index,
                    'y':absorbent_flow.flow_rate,
                    'stackgroup':'flow_rate',
                    'fillcolor':'brown',
                    'name':'Abs. garment',
                    'line':{'shape':'hv'},
                    'mode':'none'
                },
                {
                    'x':menstrual_cup_flow.index,
                    'y':menstrual_cup_flow.flow_rate,
                    'stackgroup':'flow_rate',
                    'fillcolor':'red',
                    'name':'Menstrual cup',
                    'line':{'shape':'hv'},
                    'mode':'none'
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
                        'title':{
                            'text':'Flow rate (mL/h)'
                        },
                        'domain':[0,0.3],
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
                        'domain':[0.36,1],
                        **default_axis_style
                    },
                    'yaxis3':{
                        'range':[0,1],
                        'domain':[0.36,1]
                    },
                    'barmode':'overlay',
                    'legend':{
                        'traceorder':'normal',
                        'x':1,
                        'y':1,
                        'xanchor':'right'
                    },
                    'plot_bgcolor': '#E5ECF6',
                    "xaxis": {
                        'range': get_axis_range(dates,start_idx=-120),
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

    @view_with_header
    @view_config(route_name='period_sea',renderer='../templates/period_plot.jinja2')
    def period_sea(self):

        import plotly

        import numpy as np

        import pandas as pd

        from .plotly_defaults import default_axis_style

        dbsession=self.request.dbsession

        session_person=dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).first()

        periods=get_period_data(dbsession,session_person)

        periods=periods_postprocess(periods)

        intensities=periods.period_intensity

        start_inds, start_dates=get_period_starts(periods)

        ovulation_inds, ovulation_dates=get_ovulations(periods)

        temperature_rise_inds, temperature_rise_dates=get_temperature_rise(periods)
        ovulation_with_temp_inds, ovulation_with_temp_dates = get_ovulations_with_temperature_rise(periods,ovulation_inds,temperature_rise_inds)

        ovulation_without_temp_inds, ovulation_without_temp_dates = get_ovulations_with_temperature_rise(periods,ovulation_inds,temperature_rise_inds,inverse=True)

        window=int(self.request.params.get('window','45'))

        assert window>0

        epoch_type=self.request.params.get('epochs','period_start')

        if epoch_type=='period_start':
            epoch_inds=start_inds
        elif epoch_type=='cervical_fluid':
            epoch_inds=ovulation_inds
        elif epoch_type=='cervical_fluid_with_temp':
            epoch_inds=ovulation_with_temp_inds
        elif epoch_type=='cervical_fluid_without_temp':
            epoch_inds=ovulation_without_temp_inds
        elif epoch_type=='temperature_rise':
            epoch_inds=temperature_rise_inds
        else:
            raise ValueError('Invalid epoch type {}'.format(epoch_type))

        # Reject epochs without data to fill the window
        usable_epochs=epoch_inds&(epoch_inds.index>window)&(epoch_inds.index<len(periods)-window)

        # Get intervals between epochs
        intervals=epoch_inds.index[epoch_inds].to_numpy()[1:]-epoch_inds.index[epoch_inds].to_numpy()[:-1]

        # Reject epochs for which the following interval exceeds 64 days
        usable_epochs=usable_epochs&(epoch_inds[epoch_inds].iloc[:-1].iloc[intervals<64])

        # Reject the first and last epochs from the SEA (they can't meet the
        # interval criteria regardless of what interval is set)
        usable_epochs[epoch_inds.index[epoch_inds][0]]=False
        usable_epochs[epoch_inds.index[epoch_inds][-1]]=False

        # Reject epochs for which the preceding interval exceeds 64 days
        usable_epochs[1:]=usable_epochs[1:]&(epoch_inds[epoch_inds].iloc[:-2].iloc[intervals[:-1]<64])

        epoch_inds=epoch_inds.index[usable_epochs]

        period_start=sea_var_data(start_inds,epoch_inds,window)

        cervical_fluid_end=sea_var_data(ovulation_inds,epoch_inds,window)

        temperature_rise=sea_var_data(temperature_rise_inds,epoch_inds,window)

        temp=sea_var_data(periods.temperature,epoch_inds,window)

        cervical_fluid=-sea_var_data(periods.cervical_fluid_character-1,epoch_inds,window)

        period_intensity=sea_var_data(periods.period_intensity-1,epoch_inds,window)

        def sea_plot(var_data,color=None,**kwargs):

            qul=np.nanpercentile(var_data,(25,50,75),axis=0)

            if color:
                style={'line':{'color':color}}
            else:
                style={}

            x=np.concatenate([np.arange(-window,window),
                                        np.arange(window-1,-window-1,-1)])

            if len(qul.shape)==1:
                ylower=qul
                yupper=qul
                ymid=qul
            else:
                ylower=qul[0]
                yupper=qul[2][::-1]
                ymid=qul[1]

            return [
                {
                    'x':x,
                    'y':np.concatenate([ylower,yupper]),
                    'type':'scatter',
                    'fill':'toself',
                    'fillcolor':'rgba(231,107,243,0.4)',
                    'line':{'color':'transparent'},
                    'mode':'lines+markers',
                    'showlegend':False,
                    **kwargs
                },
                {
                    'x':x,
                    'y':ymid,
                    'type':'scatter',
                    'mode':'lines+markers',
                    **style,
                    **kwargs
                },
            ]

        def sea_probability(var_data,color=None,**kwargs):

            if color:
                style={'marker':{'color':color}}
            else:
                style={}

            return [{
                'x':np.arange(-window,window),
                'y':np.mean(var_data,axis=0),
                'type':'bar',
                'opacity':0.6,
                **style,
                **kwargs
            }]

        graphs=[
            {
                'data':[
                    *sea_plot(temp,yaxis='y2',name='Temperature'),
                    *sea_probability(period_start,name='Period start',yaxis='y3'),
                    *sea_probability(cervical_fluid_end,name='Ovulation (cervical fluid)',yaxis='y3'),
                    *sea_probability(temperature_rise,name='Ovulation (temperature rise)',yaxis='y3'),
                    *sea_plot(period_intensity,yaxis='y1',color='red',name='Period'),
                    *sea_plot(cervical_fluid,yaxis='y1',color='blue',name='Cervical fluid')
                ],
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
                        'title':{
                            'text':'Intensity'
                        },
                        'domain':[0.15,0.3],
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
                        'domain':[0.36,1],
                        **default_axis_style
                    },
                    'yaxis3':{
                        'range':[0,1],
                        'domain':[0,0.1],
                        'title':{
                            'text':'Probability'
                        },
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

    @view_with_header
    @view_config(route_name='period_interval_plot',renderer='../templates/period_histogram.jinja2')
    def interval_plot(self):

        import plotly

        import numpy as np

        import pandas as pd

        from .plotly_defaults import default_axis_style

        dbsession=self.request.dbsession

        session_person=dbsession.query(Person).filter(
            Person.id==self.request.session['person_id']).first()

        periods=get_period_data(dbsession,session_person)

        periods=periods_postprocess(periods)

        intensities=periods.period_intensity

        start_mask, start_dates=get_period_starts(periods)

        cervical_fluid_end_inds, cervical_fluid_end_dates=get_ovulations(periods)

        temperature_rise_inds, temperature_rise_dates=get_temperature_rise(periods)
        ovulation_with_temp_inds, ovulation_with_temp_dates = get_ovulations_with_temperature_rise(periods,cervical_fluid_end_inds,temperature_rise_inds)

        ovulation_without_temp_inds, ovulation_without_temp_dates = get_ovulations_with_temperature_rise(periods,cervical_fluid_end_inds,temperature_rise_inds,inverse=True)

        interval_type=self.request.params.get('interval_type','cycle_length')

        if interval_type=='cycle_length':
            dates=start_dates
            intervals=(dates-dates.shift(1)).dt.total_seconds()/86400+1
        elif interval_type=='luteal_phase':
            ovulation_inds=pd.Series(np.zeros([len(periods)],dtype=bool))
            start_inds=start_mask[start_mask].index.values
            for i in range(len(start_inds)-1):
                ind=start_inds[i]
                ind_next=start_inds[i+1]

                # Get ovulations in this cycle
                cycle_ovulations=ovulation_with_temp_inds[
                    (ovulation_with_temp_inds.index>ind)
                    & (ovulation_with_temp_inds.index<ind_next)
                ]

                if cycle_ovulations.sum()==0:
                    # No ovulations with corresponding temperature rise,
                    # use ovulations based on cervical fluid alone
                    cycle_ovulations=cervical_fluid_end_inds[
                        (cervical_fluid_end_inds.index>ind)
                        & (cervical_fluid_end_inds.index<ind_next)
                    ]

                if cycle_ovulations.sum()>0:

                    # Find the last ovulation of the cycle
                    ovulation_inds[
                        cycle_ovulations[cycle_ovulations].index[-1]]=True
                else:
                    start_mask[ind_next]=False

            intervals=(periods.dates[start_mask][1:].reset_index()-periods.dates[ovulation_inds[ovulation_inds].index].reset_index()).dates.dt.total_seconds()/86400+1

        else:
            raise ValueError('Invalid interval type {}'.format(epoch_type))


        graphs=[
            {
                'data':[
                    {
                        'x':periods.dates[start_mask],
                        'y':intervals,
                        'xaxis':'x1',
                        'yaxis':'y1'
                    },
                    {
                        'x':intervals,
                        'type':'histogram',
                        'yaxis':'y2',
                        'xaxis':'x2',
                        'xbins':{'size':1}
                    }
                ],
                'layout':{
                    'showlegend':False,
                    'yaxis':{
                        **default_axis_style,
                        'title':'Interval (days)',
                        'domain':[0.4,1]
                    },
                    'yaxis2':{
                        **default_axis_style,
                        'title':'Probability',
                        'domain':[0,0.3]
                    },
                    'grid':{
                        'rows':2,
                        'columns':1,
                        'pattern':'independent',
                        'roworder':'top to bottom'
                    },
                    'xaxis2':{**default_axis_style},
                    'xaxis2':{
                        **default_axis_style,
                        'title':'Interval (days)'
                    }
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
