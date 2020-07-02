from .crud import CRUDView
from ..models import Weight
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
