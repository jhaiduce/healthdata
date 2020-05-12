from pyramid_crud.forms import CSRFModelForm
from pyramid_crud.views import CRUDView
from ..models import Weight
from pyramid.events import NewRequest
from pyramid.events import subscriber

class WeightForm(CSRFModelForm):
    class Meta:
        model = Weight

    @subscriber(NewRequest)
    @classmethod
    def update_dbsesion(cls,event):
        cls.dbsession=event.request.dbsession

    @classmethod
    def get_dbsession(cls):
        return cls.dbsession

class WeightView(CRUDView):
    Form = WeightForm
    url_path = '/weight'
