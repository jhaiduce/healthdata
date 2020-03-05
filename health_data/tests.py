import unittest

from pyramid import testing

import transaction

from pyramid.httpexceptions import HTTPFound

def dummy_request(dbsession):
    return testing.DummyRequest(dbsession=dbsession)


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp(settings={
            'sqlalchemy.url': 'sqlite:///:memory:'
        })
        self.config.include('.models')
        settings = self.config.get_settings()

        self.config.add_route('period_plot','/period')
        self.config.add_route('period_list','/period/list')
        self.config.add_route('period_delete','/period/{period_id}/delete')

        from .models import (
            get_engine,
            get_session_factory,
            get_tm_session,
            )

        self.engine = get_engine(settings)
        session_factory = get_session_factory(self.engine)

        self.session = get_tm_session(session_factory, transaction.manager)

    def init_database(self):
        from .models.meta import Base
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        from .models.meta import Base

        testing.tearDown()
        transaction.abort()
        Base.metadata.drop_all(self.engine)


class TestPeriod(BaseTest):

    def setUp(self):
        super(TestPeriod, self).setUp()
        self.init_database()

        from .models.records import Period, period_intensity_choices, cervical_fluid_choices, Temperature
        from datetime import date, datetime

        period = Period(period_intensity=3,date=date(2019,10,31),
                        cervical_fluid_character=1,
                        temperature=Temperature(
                            temperature=97.5,
                            time=datetime(2019,10,31,7,13)))
        self.session.add(period)

    def test_period_plot(self):
        from .views.period import PeriodViews
        views = PeriodViews(dummy_request(self.session))
        info=views.period_plot()

    def test_period_edit(self):
        from .views.period import PeriodViews
        from .models.records import Period, Record, Temperature
        from datetime import date, datetime
        request=testing.DummyRequest({
            'form.submitted':True,
            'submit':'submit',
            'period_intensity':'5',
            'cervical_fluid':'1',
            '__start__':'date:mapping',
            'date':'2019-10-29',
            '__end__':'date:mapping',
            'temperature':'97.7',
            'time':'07:13',
        },dbsession=self.session)
        views = PeriodViews(request)
        info=views.period_add()
        records=self.session.query(Period).filter(
            Period.date==date(2019,10,29))
        record_id=records.first().id
        temperature_id=records.first().temperature_id
        record_count=records.count()
        self.assertGreater(record_count,0)

        request=testing.DummyRequest({
            'form.submitted':True,
            'submit':'submit',
            'period_intensity':'5',
            'cervical_fluid':'1',
            '__start__':'date:mapping',
            'date':'2019-10-29',
            '__end__':'date:mapping',
            'temperature':'97.2',
            'time':'07:13',
        },dbsession=self.session)
        request.matchdict['period_id']=record_id
        views = PeriodViews(request)
        info=views.period_edit()
        record=self.session.query(Period).filter(Period.id==record_id).one()
        self.assertEqual(record.temperature.temperature,97.2)

        # Test delete button on the edit form
        request=testing.DummyRequest({
            'form.submitted':True,
            'delete_ride':'delete_ride',
            'period_intensity':'5',
            'cervical_fluid':'1',
            '__start__':'date:mapping',
            'date':'2019-10-29',
            '__end__':'date:mapping',
            'temperature':'97.2',
            'time':'07:13',
        },dbsession=self.session)
        request.matchdict['period_id']=record_id
        edit_url=request.url
        views = PeriodViews(request)
        info=views.period_edit()
        self.assertTrue(isinstance(info,HTTPFound))
        delete_url=request.route_url('period_delete',
                                          period_id=record_id,
                                          _query=dict(referrer=request.url))
        self.assertEqual(info.location,delete_url)

        # Test cancelling delete
        request=testing.DummyRequest({
            'cancel':'cancel'
        },dbsession=self.session)
        request.matchdict['period_id']=record_id
        request.referrer=edit_url
        views=PeriodViews(request)
        info=views.period_delete()
        self.assertTrue(isinstance(info,HTTPFound))
        self.assertEqual(info.location,edit_url)

        # Test deletion
        request=testing.DummyRequest({
            'delete':'delete'
        },dbsession=self.session)
        request.matchdict['period_id']=record_id
        request.referrer=edit_url
        views=PeriodViews(request)
        info=views.period_delete()
        self.assertTrue(isinstance(info,HTTPFound))
        self.assertEqual(info.location,request.route_url('period_list'))
        self.assertEqual(
            self.session.query(Period).filter(Period.id==record_id).count(),
            0)
        self.assertEqual(
            self.session.query(Record).filter(Record.id==record_id).count(),
            0)
        self.assertEqual(
            self.session.query(Temperature).filter(Temperature.id==temperature_id).count(),
            0)
