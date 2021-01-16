from pyramid.events import subscriber
from pyramid.view import view_config
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent
from ..models import MenstrualCupFill, AbsorbentGarment, AbsorbentWeights, Note
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
import deform
import colander

# Notes is a foreign key reference to the symptomtype table. Since we
# only want to expose one field of notes, we declare a custom SchemaNode
# for it
notes_schema = colander.SchemaNode(colander.String(),
                                   name='notes',
                                   widget=deform.widget.TextAreaWidget(),
                                   missing=None)

def yesno(value):
    if value is None:
        return '-'
    elif value:
        return 'y'
    else:
        return 'n'

def notes(obj):
    """
    Return the text of a notes object (for display in the SymptomViews table)
    """

    return obj.notes.text if obj.notes else '-'

def garment(obj):
   return obj.garment.name if obj.garment else None

def blood_observed(obj):
   return yesno(obj.blood_observed)

class MenstrualCupFillCrudViews(IndividualRecordCRUDView,CRUDView):
    model=MenstrualCupFill
    schema=SQLAlchemySchemaNode(
       MenstrualCupFill,
       includes=['time','fill',notes_schema],
       overrides={
           'notes':{
               'widget':deform.widget.TextAreaWidget()
           },
       }
    )
    title='menstrual cup fill'
    url_path = '/period/menstrual_cup_fill'
    list_display=('time','fill',notes)

    def get_list_query(self):
       query=super(MenstrualCupFillCrudViews,self).get_list_query()

       return query.order_by(MenstrualCupFill.time.desc())

    def dictify(self,obj):
        """
        Serialize a MenstrualCupFill object to a dict for CRUD view
        """

        appstruct=super(MenstrualCupFillCrudViews,self).dictify(obj)

        if obj.notes is not None:
           appstruct['notes']=obj.notes.text

        return appstruct

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def finalize_menstrualcupfill_fields(event):

    """
    Post-process an automatically deserialized MenstrualCupFill object
    """

    if isinstance(event.obj,MenstrualCupFill):
        if event.appstruct['notes']:
            if event.obj.notes is None:
               event.obj.notes=Note()
               event.obj.notes.text=event.appstruct['notes']
               event.obj.notes.date=event.obj.time

        else:

            event.obj.notes=None

        event.request.dbsession.flush()

class AbsorbentGarmentViews(CRUDView):
    model=AbsorbentGarment
    schema=SQLAlchemySchemaNode(
       AbsorbentGarment,
       includes=['name'],
    )
    title='absorbent garment'
    url_path = '/period/absorbent_garments'
    list_display=('name',)

@colander.deferred
def get_garment_select_widget(node,kw):
    dbsession=kw['request'].dbsession
    garments=dbsession.query(AbsorbentGarment)
    choices=[('','')]+[(garment.id, garment.name) for garment in garments]
    return deform.widget.SelectWidget(values=choices)

class AbsorbentWeightCrudViews(IndividualRecordCRUDView,CRUDView):
    model=AbsorbentWeights
    schema=SQLAlchemySchemaNode(
       AbsorbentWeights,
       includes=[
          colander.SchemaNode(
             colander.Integer(),
             name='garment',
             title='Garment',
             widget=get_garment_select_widget,
          ),
          'time_before',
          'time_after',
          'weight_before',
          'weight_after',
          colander.SchemaNode(
             colander.String(),
             name='blood_observed_s',
             title='Blood Observed',
             widget=deform.widget.SelectWidget(
                values=[
                   ('None',''),
                   ('False','No'),
                   ('True','Yes')
                ]
             )
          ),
          notes_schema
       ],
       overrides={
           'notes':{
               'widget':deform.widget.TextAreaWidget()
           },
       }
    )
    title='absorbent weights'
    url_path = '/period/absorbent_weights'
    list_display=(garment,'time_before','time_after','weight_before','weight_after','difference',blood_observed,notes)

    def get_list_query(self):
       query=super(AbsorbentWeightCrudViews,self).get_list_query()

       return query.order_by(AbsorbentWeights.time_after.desc())

    def dictify(self,obj):
        """
        Serialize an AbsorbentWeights object to a dict for CRUD view
        """

        appstruct=super(AbsorbentWeightCrudViews,self).dictify(obj)

        appstruct['garment']=obj.garment_id

        appstruct['blood_observed_s']=str(obj.blood_observed)

        if obj.notes is not None:
           appstruct['notes']=obj.notes.text

        return appstruct

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def finalize_absorbentweights_fields(event):

    """
    Post-process an automatically deserialized MenstrualCupFill object
    """

    if isinstance(event.obj,AbsorbentWeights):
        if event.appstruct['notes']:
            if event.obj.notes is None:
               event.obj.notes=Note()
               event.obj.notes.text=event.appstruct['notes']
               event.obj.notes.date=event.obj.time_before

        else:

            event.obj.notes=None

        event.obj.garment_id=event.appstruct['garment']

        if event.appstruct.get('blood_observed_s','None')=='None':
           event.obj.blood_observed=None
        elif event.appstruct['blood_observed_s']=='False':
           event.obj.blood_observed=False
        elif event.appstruct['blood_observed_s']=='True':
           event.obj.blood_observed=True
        else:
           raise ValueError('Invalid value {} provided for blood_observed'.format(str(event.appstruct['blood_observed'])))

        event.request.dbsession.flush()
