from pyramid.events import subscriber
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent
from pyramid.view import view_config
from ..models import Symptom,SymptomType,Note
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
import colander
import deform

def get_symptomtype_by_name(dbsession,name):

    from sqlalchemy.orm.exc import NoResultFound

    try:
        symptomtype=dbsession.query(SymptomType).filter(
            SymptomType.name==name).one()
    except NoResultFound:
        symptomtype=SymptomType(name=name)
        dbsession.add(symptomtype)
    return symptomtype

@subscriber(ViewDbInsertEvent,ViewDbUpdateEvent)
def finalize_symptom_fields(event):

    if isinstance(event.obj,Symptom):

        if event.appstruct['symptomtype'] is not None and len(event.appstruct['symptomtype'])>0:
            event.obj.symptomtype=get_symptomtype_by_name(event.request.dbsession,event.appstruct['symptomtype'])
        else:
            event.obj.symptomtype=None

        if event.appstruct['notes'] is not None:
            if event.obj.notes is None:
                event.obj.notes=Note()
            event.obj.notes.date=event.obj.start_time
            event.obj.notes.text=event.appstruct['notes']
        else:
            event.obj.notes=None

@view_config(route_name='symptomtype_autocomplete', renderer='json')
def symptomtype_autocomplete(request):
    term=request.GET['term']

    # Subquery to get the most recent instance of each symptom type
    last_id = request.dbsession.query(Symptom.id).filter(
        Symptom.symptomtype_id==SymptomType.id
    ).order_by(Symptom.end_time.desc()).limit(1
    ).correlate(SymptomType)

    # Query symptom types matching the term variable,
    # most recently used first
    symptomtypes=request.dbsession.query(SymptomType).filter(
            SymptomType.name.startswith(term)
        ).outerjoin(Symptom, Symptom.id == last_id
        ).order_by(Symptom.end_time.desc()
        ).order_by(SymptomType.id.desc()).limit(8)

    return [symptomtype.name for symptomtype in symptomtypes]

@colander.deferred
def get_symptomtype_widget(node,kw):
    return deform.widget.AutocompleteInputWidget(
        min_length=1,
        values=kw['request'].route_path(
            'symptomtype_autocomplete'
            )
    )

symptomtype_schema = colander.SchemaNode(colander.String(),
                                         name='symptomtype',
                                         title='Symptom',
                                         widget=get_symptomtype_widget)

notes_schema = colander.SchemaNode(colander.String(),
                                   name='notes',
                                   widget=deform.widget.TextAreaWidget(),
                                   missing=None)

def notes(obj):
    return obj.notes.text

class SymptomViews(IndividualRecordCRUDView,CRUDView):
    model=Symptom
    schema=SQLAlchemySchemaNode(
        Symptom,
        includes=[symptomtype_schema,'start_time','end_time',notes_schema],
        overrides={
            'start_time':{
                'title':'First noted',
            },
            'end_time':{
                'title':'Last noted',
            },
        }
    )
    url_path = '/symptom'
    list_display=('symptomtype','start_time','end_time',notes)

    def dictify(self,obj):

        appstruct=super(SymptomViews,self).dictify(obj)

        if obj.notes is not None:
            appstruct['notes']=obj.notes.text

        return appstruct
