from .crud import CRUDView
from ..models import Weight
from pyramid.events import NewRequest
from pyramid.events import subscriber
from colanderalchemy import SQLAlchemySchemaNode

class WeightView(CRUDView):
    model=Weight
    schema=SQLAlchemySchemaNode(
        Weight,
        includes=['time','weight']
    )
    url_path = '/weight'
    list_display=('time','weight',)
