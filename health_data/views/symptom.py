from pyramid.events import subscriber
from .crud import CRUDView, ViewDbInsertEvent,ViewDbUpdateEvent
from pyramid.view import view_config
from ..models import Symptom,SymptomType,Note
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView
import colander
import deform

def get_symptomtype_by_name(dbsession,name):
    """
    Get the most recently used symptom type whose name starts with `name`, or a new symptomtype object if no match is found.

    Arguments:
    - dbsession: A SQLAlchemy database session object
    - name: Name string to search for
    """

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
    """
    Post-process an automatically deserialized Symptom object
    """

    if isinstance(event.obj,Symptom):

        # Store the symptomtype field
        if event.appstruct['symptomtype'] is not None:

            event.obj.symptomtype=get_symptomtype_by_name(
                event.request.dbsession,event.appstruct['symptomtype'])

        else:

            event.obj.symptomtype=None

        # Store the notes field
        if event.appstruct['notes'] is not None:

            if event.obj.notes is None:
                # Create a new notes object
                event.obj.notes=Note()

            # Set/update the notes properties
            event.obj.notes.date=event.obj.start_time
            event.obj.notes.text=event.appstruct['notes']

        else:

            event.obj.notes=None

@view_config(route_name='symptomtype_autocomplete', renderer='json')
def symptomtype_autocomplete(request):
    """
    Autocomplete suggestions view for symptom types

    Arguments:
    - request: A Pyramid request object

    Returns: A list of symptomtype names
    """

    # String to search for matching symptom types
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
    """
    Return an autocomplete widget for symptom types
    """

    return deform.widget.AutocompleteInputWidget(
        min_length=1,
        values=kw['request'].route_path(
            'symptomtype_autocomplete'
            )
    )

# Symptomtype is a foreign key reference to the symptomtype table. Since we
# only want to expose one field of symptomtype, we declare a custom SchemaNode
# for it
symptomtype_schema = colander.SchemaNode(colander.String(),
                                         name='symptomtype',
                                         title='Symptom',
                                         widget=get_symptomtype_widget,
                                         missing=None)

# Notes is a foreign key reference to the symptomtype table. Since we
# only want to expose one field of notes, we declare a custom SchemaNode
# for it
notes_schema = colander.SchemaNode(colander.String(),
                                   name='notes',
                                   widget=deform.widget.TextAreaWidget(),
                                   missing=None)

def notes(obj):
    """
    Return the text of a notes object (for display in the SymptomViews table)
    """

    return obj.notes.text if obj.notes else None

def symptom(obj):
    """
    Return the name of a symptomtype object (for display in the SymptomViews
    table)
    """

    return obj.symptomtype.name if obj.symptomtype else None

class SymptomViews(IndividualRecordCRUDView,CRUDView):
    """
    CRUD views for Symptom entries
    """

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
    list_display=(symptom,'start_time','end_time',notes)

    def dictify(self,obj):
        """
        Serialize a SymptomViews object to a dict
        """

        # Default serialization for built-in fields
        appstruct=super(SymptomViews,self).dictify(obj)

        if obj.notes is not None:
            appstruct['notes']=obj.notes.text

        if obj.symptomtype is not None:
            appstruct['symptomtype']=obj.symptomtype.name

        return appstruct
