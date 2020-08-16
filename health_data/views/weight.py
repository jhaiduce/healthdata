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

    def get_list_query(self):
        query=super(WeightView,self).get_list_query()

        return query.order_by(Weight.time.desc())
