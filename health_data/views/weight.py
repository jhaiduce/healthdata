from .crud import CRUDView
from ..models import Weight
from ..models.people import Person
from pyramid.events import NewRequest
from pyramid.events import subscriber
from colanderalchemy import SQLAlchemySchemaNode
from .individual_record import IndividualRecordCRUDView

class WeightView(IndividualRecordCRUDView,CRUDView):
    model=Weight
    schema=SQLAlchemySchemaNode(
        Weight,
        includes=['time','weight']
    )
    url_path = '/weight'
    list_display=('time','weight',)
