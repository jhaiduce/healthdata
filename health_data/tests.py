import unittest

from pyramid import testing

import transaction

from pyramid.httpexceptions import HTTPFound

import re

import json
from datetime import date, datetime, time

from sqlalchemy.orm.exc import NoResultFound

session_secret='3e774c33267869272a585d5540402349252460606b42633964462a3440563365'

def dummy_request(dbsession):
    return testing.DummyRequest(dbsession=dbsession)


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp(settings={
            'sqlalchemy.url': 'sqlite:///:memory:',
            'session_secret': session_secret
        })
        self.config.include('.models')
        settings = self.config.get_settings()

        self.config.add_route('period_plot','/period')
        self.config.add_route('period_list','/period/list')
        self.config.add_route('period_delete','/period/{period_id}/delete')
        self.config.add_route('person_list','/person/list')
        self.config.add_route('person_delete','/person/{person_id}/delete')
        self.config.add_route('temperature_edit','/temperature/{temperature_id}/edit')
        self.config.add_route('temperature_list','/temperature/list')
        self.config.add_route('temperature_delete','/temperature/delete')

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
        from .models.security import User
        from .models.people import Person
        Base.metadata.create_all(self.engine)

        user=User(
            name='admin'
        )

        user.set_password('admin_password')
        self.session.add(user)

        person=Person(name='Alice')
        self.session.add(person)
        self.session.flush()

        self.person_id=person.id

        transaction.commit()

    def tearDown(self):
        from .models.meta import Base

        testing.tearDown()
        transaction.abort()
        Base.metadata.drop_all(self.engine)

class TestPerson(BaseTest):

    def setUp(self):
        super(TestPerson, self).setUp()
        self.init_database()

    def test_person_addedit(self):
        from.views.people import PersonViews
        from .models.people import Person

        request=testing.DummyRequest({
            'form.submitted':True,
            'submit':'submit',
            'name':'Bob'
            },dbsession=self.session)

        views=PersonViews(request)
        info=views.person_add()
        records=self.session.query(Person).filter(Person.name=='Bob')
        record_id=records.first().id

        request=testing.DummyRequest({
            'form.submitted':True,
            'submit':'submit',
            'name':'Robert'
            },dbsession=self.session)
        request.matchdict['person_id']=record_id
        views=PersonViews(request)
        info=views.person_edit()
        record=self.session.query(Person).filter(Person.id==record_id).one()
        self.assertEqual(record.name,'Robert')

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
        request=dummy_request(self.session)
        request.session['person_id']=self.person_id
        views = PeriodViews(request)
        info=views.period_plot()

    def test_period_edit(self):
        from .views.period import PeriodViews
        from .models.records import Period, Record, Temperature
        from datetime import date, datetime
        from webob.multidict import MultiDict
        request=testing.DummyRequest(MultiDict([
            ('form.submitted',True),
            ('submit','submit'),
            ('period_intensity','5'),
            ('cervical_fluid','1'),
            ('__start__','date:mapping'),
            ('date','2019-10-29'),
            ('__end__','date:mapping'),
            ('temperature','97.7'),
            ('__start__','temperature_time:mapping'),
            ('time','07:13'),
            ('__end__','temperature_time:mapping'),
            ('notes','Note')
        ]),dbsession=self.session)
        request.session['person_id']=self.person_id
        views = PeriodViews(request)
        info=views.period_add()
        records=self.session.query(Period).filter(
            Period.date==date(2019,10,29))
        record_id=records.first().id
        temperature_id=records.first().temperature_id
        record_count=records.count()
        self.assertGreater(record_count,0)

        request=testing.DummyRequest(MultiDict([
            ('form.submitted',True),
            ('submit','submit'),
            ('period_intensity','5'),
            ('cervical_fluid','1'),
            ('__start__','date:mapping'),
            ('date','2019-10-29'),
            ('__end__','date:mapping'),
            ('temperature','97.2'),
            ('__start__','temperature_time:mapping'),
            ('time','07:13'),
            ('__end__','temperature_time:mapping'),
            ('notes','Updated note')
        ]),dbsession=self.session)
        request.session['person_id']=self.person_id
        request.matchdict['period_id']=record_id
        views = PeriodViews(request)
        info=views.period_edit()
        record=self.session.query(Period).filter(Period.id==record_id).one()
        self.assertEqual(record.temperature.temperature,97.2)
        self.assertEqual(record.notes.text,'Updated note')

        request=testing.DummyRequest(MultiDict([
            ('form.submitted',True),
            ('submit','submit'),
            ('period_intensity','5'),
            ('cervical_fluid','1'),
            ('__start__','date:mapping'),
            ('date','2019-10-29'),
            ('__end__','date:mapping'),
            ('temperature','97.2'),
            ('__start__','temperature_time:mapping'),
            ('time',''),
            ('__end__','temperature_time:mapping'),
            ('notes','Updated note')
        ]),dbsession=self.session)
        request.session['person_id']=self.person_id
        request.matchdict['period_id']=record_id
        views = PeriodViews(request)
        info=views.period_edit()
        record=self.session.query(Period).filter(Period.id==record_id).one()
        self.assertEqual(record.temperature.temperature,97.2)
        self.assertEqual(record.temperature.time,datetime(2019,10,29))
        self.assertEqual(record.notes.text,'Updated note')

        request=testing.DummyRequest(MultiDict([
            ('form.submitted',True),
            ('submit','submit'),
            ('period_intensity','5'),
            ('cervical_fluid','1'),
            ('__start__','date:mapping'),
            ('date','2019-10-29'),
            ('__end__','date:mapping'),
            ('temperature','97.2'),
            ('__start__','__temperature_time:mapping'),
            ('time','07:13'),
            ('__end__','temperature_time:mapping'),
            ('notes','')
        ]),dbsession=self.session)
        request.session['person_id']=self.person_id
        request.matchdict['period_id']=record_id
        views = PeriodViews(request)
        info=views.period_edit()
        record=self.session.query(Period).filter(Period.id==record_id).one()
        self.assertEqual(record.temperature.temperature,97.2)
        self.assertIsNone(record.notes)

        # Test delete button on the edit form
        request=testing.DummyRequest(MultiDict([
            ('form.submitted',True),
            ('delete_entry','delete_entry'),
            ('period_intensity','5'),
            ('cervical_fluid','1'),
            ('__start__','date:mapping'),
            ('date','2019-10-29'),
            ('__end__','date:mapping'),
            ('temperature','97.2'),
            ('__start__','temperature_time:mapping'),
            ('time','07:13'),
            ('__end__','temperature_time:mapping'),
        ]),dbsession=self.session)
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

class TestTemperature(BaseTest):

    def setUp(self):
        super(TestTemperature, self).setUp()
        self.init_database()

        from .models.records import Temperature
        from datetime import date, datetime

        temperature = Temperature(
            temperature=97.5,
            time=datetime(2019,10,31,7,13),
            person_id=self.person_id)
        self.session.add(temperature)

    def test_temperature_plot(self):
        from .views.temperature import TemperatureViews
        request=dummy_request(self.session)
        request.session['person_id']=self.person_id
        views = TemperatureViews(request)
        info=views.temperature_plot()

    def test_temperature_edit(self):
        from .views.temperature import TemperatureViews
        from .models.records import Temperature,Record
        from datetime import date, datetime
        request=testing.DummyRequest({
            'form.submitted':True,
            'id':'',
            'date':{'date':'2019-10-29'},
            'time':{'time':'07:45'},
            'temperature':'97.7',
            'submit':'submit',
            '_charset_':'UTF-8',
        },dbsession=self.session)
        request.session['person_id']=self.person_id
        views = TemperatureViews(request)
        info=views.temperature_add()
        records=self.session.query(Temperature).filter(
            Temperature.time==datetime(2019,10,29,7,45))
        temperature_id=records.first().id
        record_count=records.count()
        self.assertGreater(record_count,0)

        request=testing.DummyRequest({
            'form.submitted':True,
            'submit':'submit',
            '__start__':'date:mapping',
            'date':'2019-10-29',
            '__end__':'date:mapping',
            '__start__':'time:mapping',
            'time':'07:13',
            '__end__':'time:mapping',
            'temperature':'97.7',
        },dbsession=self.session)
        request.session['person_id']=self.person_id
        request.matchdict['temperature_id']=temperature_id
        edit_url=request.url
        views = TemperatureViews(request)
        info=views.temperature_edit()
        record=self.session.query(Temperature).filter(Temperature.id==temperature_id).one()
        self.assertEqual(record.temperature,97.7)

        # Test delete button on the edit form
        request=testing.DummyRequest({
            'form.submitted':True,
            'delete_entry':'delete_entry',
            '__start__':'date:mapping',
            'date':'2019-10-29',
            '__end__':'date:mapping',
            '__start__':'time:mapping',
            'time':'07:13',
            '__end__':'time:mapping',
            'temperature':'97.7',
        },dbsession=self.session)
        request.matchdict['temperature_id']=temperature_id
        edit_url=request.url
        views = TemperatureViews(request)
        info=views.temperature_edit()
        self.assertTrue(isinstance(info,HTTPFound))
        delete_url=request.route_url('temperature_delete',
                                     temperature_id=temperature_id,
                                     _query=dict(referrer=request.url))
        self.assertEqual(info.location,delete_url)

        # Test cancelling delete
        request=testing.DummyRequest({
            'cancel':'cancel'
        },dbsession=self.session)
        request.matchdict['temperature_id']=temperature_id
        request.referrer=edit_url
        views=TemperatureViews(request)
        info=views.temperature_delete()
        self.assertTrue(isinstance(info,HTTPFound))
        self.assertEqual(info.location,edit_url)
        self.assertEqual(
            self.session.query(Temperature).filter(
                Temperature.id==temperature_id).count(),
            1)
        self.assertEqual(
            self.session.query(Record).filter(
                Record.id==temperature_id).count(),
            1)

        # Test deletion
        request=testing.DummyRequest({
            'delete':'delete'
        },dbsession=self.session)
        request.matchdict['temperature_id']=temperature_id
        request.referrer=edit_url
        views=TemperatureViews(request)
        info=views.temperature_delete()
        self.assertTrue(isinstance(info,HTTPFound))
        self.assertEqual(info.location,request.route_url('temperature_list'))
        self.assertEqual(
            self.session.query(Temperature).filter(
                Temperature.id==temperature_id).count(),
            0)
        self.assertEqual(
            self.session.query(Record).filter(
                Record.id==temperature_id).count(),
            0)

class AuthenticationTests(BaseTest):

    def setUp(self):
        super(AuthenticationTests, self).setUp()
        self.init_database()

        from .models import User

        user=User(
            name='jhaiduce'
        )

        user.set_password('password')
        self.session.add(user)

    def test_check_password(self):
        from .models import User

        user=self.session.query(User).filter(User.name=='jhaiduce').one()

        self.assertTrue(user.check_password('password'))
        self.assertFalse(user.check_password('pa$$word'))

    def test_otp(self):

        from .models import User
        import pyotp

        user=self.session.query(User).filter(User.name=='jhaiduce').one()

        # Generate OTP from URI
        otp = pyotp.parse_uri(user.otp_uri()).now()

        # Check wrong OTP is rejected
        self.assertFalse(user.check_otp(otp+'1'))

        # Check correct OTP is accepted
        self.assertTrue(user.check_otp(otp))

        # Check that reused OTP is rejected
        self.assertFalse(user.check_otp(otp))

class TestMenstrualFlow(BaseTest):

    def setUp(self):
        super(TestMenstrualFlow,self).setUp()
        self.init_database()

    def test_flow_rate(self):
        from .models import MenstrualCupFill, Period

        cup_with_insertion_date=MenstrualCupFill(
            insertion_time=datetime(2020,1,15,8,0),
            removal_time=datetime(2020,1,15,12,0),
            fill=10
        )
        self.session.add(cup_with_insertion_date)

        cup_without_insertion_date=MenstrualCupFill(
            insertion_time=None,
            removal_time=datetime(2020,1,15,16,0),
            fill=10
        )
        self.session.add(cup_without_insertion_date)

        cup_without_insertion_date_first_of_day=MenstrualCupFill(
            insertion_time=None,
            removal_time=datetime(2020,1,16,12,0),
            fill=10
        )
        self.session.add(cup_without_insertion_date_first_of_day)

        cup_with_blank_times=MenstrualCupFill(
            fill=5
        )
        self.session.add(cup_with_blank_times)

        self.session.flush()

        self.assertEqual(
            cup_without_insertion_date.insertion_time,
            cup_with_insertion_date.removal_time)
        self.assertEqual(
            cup_without_insertion_date.insertion_time,
            cup_with_insertion_date.removal_time)
        self.assertEqual(
            cup_without_insertion_date_first_of_day.insertion_time,
            datetime.combine(
                cup_without_insertion_date_first_of_day.removal_time.date(),
                time(8)))
        self.assertAlmostEqual(cup_with_insertion_date.flow_rate,2.5)
        self.assertAlmostEqual(self.session.query(MenstrualCupFill.flow_rate).filter(MenstrualCupFill.id==cup_with_insertion_date.id).one().flow_rate,2.5)
        self.assertAlmostEqual(cup_without_insertion_date.flow_rate,2.5)
        self.assertAlmostEqual(
            self.session.query(
                MenstrualCupFill.flow_rate
            ).filter(
                MenstrualCupFill.id==cup_without_insertion_date.id
            ).one().flow_rate,
            2.5)
        self.assertAlmostEqual(cup_without_insertion_date_first_of_day.flow_rate,2.5)
        self.assertAlmostEqual(
            self.session.query(
                MenstrualCupFill.flow_rate
            ).filter(
                MenstrualCupFill.id==cup_without_insertion_date_first_of_day.id
            ).one().flow_rate,
            2.5)

        self.assertIsNone(cup_with_blank_times.flow_rate)
        self.assertIsNone(self.session.query(
            MenstrualCupFill.flow_rate
        ).filter(
            MenstrualCupFill.id==cup_with_blank_times.id
        ).one().flow_rate)

        period=Period(date=datetime(2020,1,15))
        self.session.add(period)
        self.assertAlmostEqual(period.total_flow,20)

    def test_difference(self):

        from .models import AbsorbentGarment, AbsorbentWeights, Period

        pad=AbsorbentGarment(name='pad')
        self.session.add(pad)
        self.session.flush()

        weights_without_before=AbsorbentWeights(
            garment=pad,
            weight_after=15
        )

        self.session.add(weights_without_before)

        self.assertIsNone(weights_without_before.difference)

        weights_with_before=AbsorbentWeights(
            garment=pad,
            weight_before=13,
            weight_after=13
        )

        self.assertEqual(weights_with_before.difference,0)

        self.session.add(weights_with_before)

        self.assertEqual(weights_without_before.difference,2)

        weights_with_time_before=AbsorbentWeights(
            garment=pad,
            time_before=datetime(2015,1,17,8),
            time_after=datetime(2015,1,17,12),
            weight_before=13,
            weight_after=15,
        )

        self.session.add(weights_with_time_before)
        self.session.flush()

        self.assertEqual(weights_with_time_before.time_before_inferred,datetime(2015,1,17,8))
        self.assertAlmostEqual(weights_with_time_before.flow_rate,0.5)
        self.assertAlmostEqual(
             self.session.query(
                AbsorbentWeights.flow_rate
            ).filter(
                AbsorbentWeights.id==weights_with_time_before.id
            ).one().flow_rate,
            0.5)

        weights_without_time_before=AbsorbentWeights(
            garment=pad,
            time_after=datetime(2015,1,17,16),
            weight_before=13,
            weight_after=15,
        )
        self.session.add(weights_without_time_before)
        self.session.flush()

        self.assertEqual(weights_without_time_before.time_before_inferred,datetime(2015,1,17,12))
        self.assertAlmostEqual(
             self.session.query(
                AbsorbentWeights.flow_rate
            ).filter(
                AbsorbentWeights.id==weights_without_time_before.id
            ).one().flow_rate,
            0.5)

        period=Period(date=datetime(2015,1,17))
        self.session.add(period)
        self.assertAlmostEqual(period.total_flow,4)

        weights_with_blank_times=AbsorbentWeights(
            garment=pad,
            weight_before=13,
            weight_after=15,
        )
        self.session.add(weights_with_blank_times)
        self.session.flush()

        self.assertIsNone(weights_with_blank_times.time_before_inferred)
        self.assertIsNone(weights_with_blank_times.flow_rate)
        self.assertIsNone(
             self.session.query(
                AbsorbentWeights.flow_rate
            ).filter(
                AbsorbentWeights.id==weights_with_blank_times.id
            ).one().flow_rate)

import webtest

class FunctionalTests(unittest.TestCase):
    admin_login = dict(login='admin', password='admin')

    def setUp(self):
        """
        Add some dummy data to the database.
        Note that this is a session fixture that commits data to the database.
        Think about it similarly to running the ``initialize_db`` script at the
        start of the test suite.
        This data should not conflict with any other data added throughout the
        test suite or there will be issues - so be careful with this pattern!
        """

        from . import main

        from .models import (
            get_engine,
            get_session_factory,
            get_tm_session,
            )

        import pyotp

        self.config={
            'admin_password':self.admin_login['password'],
            'sqlalchemy.url':'sqlite://',
            'auth.secret':'secret',
            'session_secret':session_secret,
            'admin_otp_secret':pyotp.random_base32()
            }

        self.app = main({}, **self.config)
        self.init_database()

        from http.cookiejar import CookieJar
        cookiejar=CookieJar()
        self.testapp=webtest.TestApp(self.app,cookiejar=cookiejar)

    def get_session(self):
        from .models import get_session_factory,get_tm_session
        session_factory = self.app.registry['dbsession_factory']
        session=get_tm_session(session_factory,transaction.manager)
        return session

    def init_database(self):

        session=self.get_session()

        from . import models

        models.Base.metadata.create_all(session.bind)

        user=models.User(
            name='admin'
        )

        user.set_password(self.config['admin_password'])
        user.otp_secret_=self.config['admin_otp_secret']
        session.add(user)

        person=models.Person(name='Alice')
        session.add(person)

        self.person_id=person.id

        transaction.commit()

    def login(self):
        import pyotp
        res=self.testapp.post('http://localhost/login',{
            **self.admin_login,
            'otp':pyotp.TOTP(self.config['admin_otp_secret']).now(),
            'form.submitted':'true'})

        # Verify that we got redirected to the default page
        self.assertEqual(res.status_code,302)
        self.assertEqual(res.location,'http://localhost/period')

    def test_successful_login(self):
        import pyotp
        res=self.testapp.post('http://localhost/login',{
            **self.admin_login,
            'otp':pyotp.TOTP(self.config['admin_otp_secret']).now(),
            'form.submitted':'true'})

        # Verify that we got redirected to the default page
        self.assertEqual(res.status_code,302)
        self.assertEqual(res.location,'http://localhost/period')

        # Verify that we can load a page
        res=self.testapp.get('http://localhost/period')
        self.assertEqual(res.status_code,200)

    def test_failed_login(self):

        import pyotp

        # Try to login with wrong password (but correct OTP)
        res=self.testapp.post('http://localhost/login',{
            **self.admin_login,
            'otp':pyotp.TOTP(self.config['admin_otp_secret']).now()+'1',
            'form.submitted':'true'})

        # Verify that we stay at the login page with a "Failsed login" message
        self.assertEqual(res.status_code,200)
        self.assertTrue(isinstance(re.search('Failed login',res.text),re.Match))

        # Verify that attempts to access restricted content are
        # redirected to the login page with the request URL passed
        # in the GET data
        res=self.testapp.get('http://localhost/period')
        self.assertEqual(res.status_code,302)
        self.assertEqual(res.location,'http://localhost/login?next=http%3A%2F%2Flocalhost%2Fperiod')

        # Try to login with correct password but wrong OTP
        res=self.testapp.post('http://localhost/login',{
            'login':'admin',
            'password':'password',
            'otp':pyotp.TOTP(self.config['admin_otp_secret']).now(),
            'form.submitted':'true'})

        # Verify that we stay at the login page with a "Failsed login" message
        self.assertEqual(res.status_code,200)
        self.assertTrue(isinstance(re.search('Failed login',res.text),re.Match))

        # Verify that attempts to access restricted content are
        # redirected to the login page with the request URL passed
        # in the GET data
        res=self.testapp.get('http://localhost/period')
        self.assertEqual(res.status_code,302)
        self.assertEqual(res.location,'http://localhost/login?next=http%3A%2F%2Flocalhost%2Fperiod')

    def test_period_addedit(self):
        self.login()
        from .models import Period
        add_url='http://localhost/period/add'
        edit_url='http://localhost/period/{}/edit'
        session=self.get_session()

        resp=self.testapp.post(
            add_url,
            params=[
                ('__start__','date:mapping'),
                ('date','2020-03-14'),
                ('__end__','date:mapping'),
                ('__start__','temperature_time:mapping'),
                ('time','07:30'),
                ('__end__','temperature_time:mapping'),
                ('temperature','97.9'),
                ('period_intensity','1'),
                ('cervical_fluid','1'),
                ('submit','submit')
            ]
        )
        self.assertEqual(resp.status_code,302)
        period_id=json.loads(resp.text)['period_id']
        period=session.query(Period).filter(Period.id==period_id).one()
        self.assertEqual(period.period_intensity,1)
        self.assertEqual(period.cervical_fluid_character,1)
        self.assertEqual(period.date,date(2020,3,14))
        self.assertEqual(period.temperature.time,datetime(2020,3,14,7,30))
        self.assertEqual(period.temperature.temperature,97.9)
        self.assertEqual(period.notes,None)

        resp=self.testapp.post(
            edit_url.format(period_id),
            params=[
                ('__start__','date:mapping'),
                ('date','2020-03-14'),
                ('__end__','date:mapping'),
                ('__start__','temperature_time:mapping'),
                ('time','07:30'),
                ('__end__','temperature_time:mapping'),
                ('temperature','98.1'),
                ('period_intensity','2'),
                ('cervical_fluid','1'),
                ('notes','A brief note'),
                ('submit','submit')
            ]
        )
        self.assertEqual(resp.status_code,302)
        session.flush()
        transaction.commit()
        period=session.query(Period).filter(Period.id==period_id).one()
        self.assertEqual(period.period_intensity,2)
        self.assertEqual(period.cervical_fluid_character,1)
        self.assertEqual(period.date,date(2020,3,14))
        self.assertEqual(period.temperature.time,datetime(2020,3,14,7,30))
        self.assertEqual(period.temperature.temperature,98.1)
        self.assertEqual(period.notes.text,'A brief note')
        self.assertEqual(period.notes.date,datetime(2020,3,14,7,30))

    def test_weight_addedit(self):
        self.login()
        from .models import Weight
        add_url='http://localhost/weight/new'
        edit_url='http://localhost/weight/{}/edit'
        delete_confirm_url='http://localhost/weight/{}/delete_confirm'
        session=self.get_session()

        resp=self.testapp.post(
            add_url,
            params=[
                ('__start__','time:mapping'),
                ('date','2020-03-14'),
                ('time','07:30'),
                ('__end__','time:mapping'),
                ('weight','72.4'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        weight_id=json.loads(resp.text)['id']
        weight=session.query(Weight).filter(Weight.id==weight_id).one()
        self.assertEqual(weight.time,datetime(2020,3,14,7,30))
        self.assertEqual(weight.weight,72.4)

        resp=self.testapp.post(
            edit_url.format(weight_id),
            params=[
                ('__start__','time:mapping'),
                ('date','2020-03-15'),
                ('time','07:45'),
                ('__end__','time:mapping'),
                ('weight','72.5'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        session.flush()
        transaction.commit()
        weight=session.query(Weight).filter(Weight.id==weight_id).one()
        self.assertEqual(weight.time,datetime(2020,3,15,7,45))
        self.assertEqual(weight.weight,72.5)

        resp=self.testapp.post(
            edit_url.format(weight_id),
            params=[
                ('__start__','time:mapping'),
                ('date','2020-03-15'),
                ('time','07:45'),
                ('__end__','time:mapping'),
                ('weight','72.5'),
                ('delete','delete')
            ])

        self.assertEqual(resp.status_code,302)

        from urllib.parse import quote
        delete_confirm_url=delete_confirm_url.format(weight_id)+'?referrer='+quote(edit_url.format(weight_id),'')
        self.assertEqual(resp.location,delete_confirm_url)

        resp=self.testapp.post(
            delete_confirm_url.format(weight_id),
            params=[
                ('delete','delete')
        ])

        session.flush()
        transaction.commit()

        with self.assertRaises(NoResultFound):
            weight=session.query(Weight).filter(Weight.id==weight_id).one()

    def test_blood_pressure_addedit(self):
        self.login()
        from .models import BloodPressure
        add_url='http://localhost/blood_pressure/new'
        edit_url='http://localhost/blood_pressure/{}/edit'
        delete_confirm_url='http://localhost/blood_pressure/{}/delete_confirm'
        session=self.get_session()

        resp=self.testapp.post(
            add_url,
            params=[
                ('__start__','time:mapping'),
                ('date','2020-03-14'),
                ('time','07:30'),
                ('__end__','time:mapping'),
                ('systolic','120'),
                ('diastolic','80'),
                ('heart_rate','64'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        blood_pressure_id=json.loads(resp.text)['id']
        blood_pressure=session.query(BloodPressure).filter(BloodPressure.id==blood_pressure_id).one()
        self.assertEqual(blood_pressure.time,datetime(2020,3,14,7,30))
        self.assertEqual(blood_pressure.systolic,120)
        self.assertEqual(blood_pressure.diastolic,80)
        self.assertEqual(blood_pressure.heart_rate.rate,64)
        self.assertEqual(blood_pressure.heart_rate.time,
                         datetime(2020,3,14,7,30))

        resp=self.testapp.post(
            edit_url.format(blood_pressure_id),
            params=[
                ('__start__','time:mapping'),
                ('date','2020-03-15'),
                ('time','07:45'),
                ('__end__','time:mapping'),
                ('systolic','124'),
                ('diastolic','82'),
                ('heart_rate','72'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        session.flush()
        transaction.commit()
        blood_pressure=session.query(BloodPressure).filter(BloodPressure.id==blood_pressure_id).one()
        self.assertEqual(blood_pressure.time,datetime(2020,3,15,7,45))
        self.assertEqual(blood_pressure.systolic,124)
        self.assertEqual(blood_pressure.diastolic,82)
        self.assertEqual(blood_pressure.heart_rate.rate,72)
        self.assertEqual(blood_pressure.heart_rate.time,
                         datetime(2020,3,15,7,45))

        resp=self.testapp.post(
            edit_url.format(blood_pressure_id),
            params=[
                ('__start__','time:mapping'),
                ('date','2020-03-15'),
                ('time','07:45'),
                ('__end__','time:mapping'),
                ('systolic','124'),
                ('diastolic','82'),
                ('heart_rate','72'),
                ('delete','delete')
            ])

        self.assertEqual(resp.status_code,302)

        from urllib.parse import quote
        delete_confirm_url=delete_confirm_url.format(blood_pressure_id)+'?referrer='+quote(edit_url.format(blood_pressure_id),'')
        self.assertEqual(resp.location,delete_confirm_url)

        resp=self.testapp.post(
            delete_confirm_url.format(blood_pressure_id),
            params=[
                ('delete','delete')
        ])

        session.flush()
        transaction.commit()

        with self.assertRaises(NoResultFound):
            blood_pressure=session.query(BloodPressure).filter(BloodPressure.id==blood_pressure_id).one()

    def test_symptom_addedit(self):
        self.login()
        from .models import Symptom
        add_url='http://localhost/symptom/new'
        edit_url='http://localhost/symptom/{}/edit'
        delete_confirm_url='http://localhost/symptom/{}/delete_confirm'
        session=self.get_session()

        resp=self.testapp.post(
            add_url,
            params=[
                ('symptomtype','Fever'),
                ('__start__','start_time:mapping'),
                ('date','2020-03-14'),
                ('time','07:30'),
                ('__end__','start_time:mapping'),
                ('__start__','end_time:mapping'),
                ('date','2020-03-14'),
                ('time','09:30'),
                ('__end__','end_time:mapping'),
                ('notes','Note'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        symptom_id=json.loads(resp.text)['id']
        symptom=session.query(Symptom).filter(Symptom.id==symptom_id).one()
        self.assertEqual(symptom.start_time,datetime(2020,3,14,7,30))
        self.assertEqual(symptom.notes.text,'Note')
        self.assertEqual(symptom.symptomtype.name,'Fever')

        resp=self.testapp.post(
            edit_url.format(symptom_id),
            params=[
                ('symptomtype',''),
                ('__start__','start_time:mapping'),
                ('date','2020-03-14'),
                ('time','07:30'),
                ('__end__','start_time:mapping'),
                ('__start__','end_time:mapping'),
                ('date','2020-03-14'),
                ('time','09:30'),
                ('__end__','end_time:mapping'),
                ('notes',''),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        session.flush()
        transaction.commit()
        symptom=session.query(Symptom).filter(Symptom.id==symptom_id).one()
        self.assertIsNone(symptom.notes)
        self.assertIsNone(symptom.symptomtype)

        resp=self.testapp.post(
            edit_url.format(symptom_id),
            params=[
                ('delete','delete')
            ])

        self.assertEqual(resp.status_code,302)

        from urllib.parse import quote
        delete_confirm_url=delete_confirm_url.format(symptom_id)+'?referrer='+quote(edit_url.format(symptom_id),'')
        self.assertEqual(resp.location,delete_confirm_url)
        symptom=session.query(Symptom).filter(Symptom.id==symptom_id).one()

        resp=self.testapp.post(
            delete_confirm_url.format(symptom_id),
            params=[
                ('delete','delete')
        ])

        session.flush()
        transaction.commit()

        with self.assertRaises(NoResultFound):
            weight=session.query(Symptom).filter(Symptom.id==symptom_id).one()

    def test_menstrual_cup_addedit(self):
        self.login()
        from .models import MenstrualCupFill
        add_url='http://localhost/period/menstrual_cup_fill/new'
        edit_url='http://localhost/period/menstrual_cup_fill/{}/edit'
        delete_confirm_url='http://localhost/period/menstrual_cup_fill/{}/delete_confirm'
        session=self.get_session()

        resp=self.testapp.post(
            add_url,
            params=[
                ('__start__','insertion_time_:mapping'),
                ('date','2020-03-14'),
                ('time','06:30'),
                ('__end__','insertion_time_:mapping'),
                ('__start__','removal_time:mapping'),
                ('date','2020-03-14'),
                ('time','07:30'),
                ('__end__','removal_time:mapping'),
                ('fill','10'),
                ('notes','Note'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        record_id=json.loads(resp.text)['id']
        record=session.query(MenstrualCupFill).filter(MenstrualCupFill.id==record_id).one()
        self.assertEqual(record.insertion_time,datetime(2020,3,14,6,30))
        self.assertEqual(record.removal_time,datetime(2020,3,14,7,30))
        self.assertEqual(record.notes.text,'Note')
        self.assertEqual(record.fill,10)

        resp=self.testapp.post(
            edit_url.format(record_id),
            params=[
                ('__start__','insertion_time_:mapping'),
                ('date','2020-03-14'),
                ('time','05:30'),
                ('__end__','insertion_time_:mapping'),
                ('__start__','removal_time:mapping'),
                ('date','2020-03-14'),
                ('time','06:30'),
                ('__end__','removal_time:mapping'),
                ('fill','12'),
                ('notes','Note1'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        session.flush()
        transaction.commit()
        record=session.query(MenstrualCupFill).filter(MenstrualCupFill.id==record_id).one()
        self.assertEqual(record.insertion_time,datetime(2020,3,14,5,30))
        self.assertEqual(record.removal_time,datetime(2020,3,14,6,30))
        self.assertEqual(record.notes.text,'Note1')
        self.assertEqual(record.fill,12)

        resp=self.testapp.post(
            edit_url.format(record_id),
            params=[
                ('delete','delete')
            ])

        self.assertEqual(resp.status_code,302)

        from urllib.parse import quote
        delete_confirm_url=delete_confirm_url.format(record_id)+'?referrer='+quote(edit_url.format(record_id),'')
        self.assertEqual(resp.location,delete_confirm_url)
        record=session.query(MenstrualCupFill).filter(MenstrualCupFill.id==record_id).one()

        resp=self.testapp.post(
            delete_confirm_url.format(record_id),
            params=[
                ('delete','delete')
        ])

        session.flush()
        transaction.commit()

        with self.assertRaises(NoResultFound):
            weight=session.query(MenstrualCupFill).filter(MenstrualCupFill.id==record_id).one()

    def test_absorbent_weight_addedit(self):
        self.login()
        from .models import AbsorbentGarment, AbsorbentWeights
        add_garments_url='http://localhost/period/absorbent_garments/new'
        edit_garments_url='http://localhost/period/absorbent_garments/{}/edit'
        delete_garments_confirm_url='http://localhost/period/absorbent_garments/{}/delete_confirm'
        add_weights_url='http://localhost/period/absorbent_weights/new'
        edit_weights_url='http://localhost/period/absorbent_weights/{}/edit'
        delete_weights_confirm_url='http://localhost/period/absorbent_weights/{}/delete_confirm'
        session=self.get_session()

        resp=self.testapp.post(
            add_garments_url,
            params=[
                ('name','pad'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        pad_id=json.loads(resp.text)['id']
        pad=session.query(AbsorbentGarment).filter(AbsorbentGarment.id==pad_id).one()
        self.assertEqual(pad.name,'pad')

        resp=self.testapp.post(
            add_garments_url,
            params=[
                ('name','panty liner'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        pantyliner_id=json.loads(resp.text)['id']
        pantyliner=session.query(AbsorbentGarment).filter(AbsorbentGarment.id==pantyliner_id).one()
        self.assertEqual(pantyliner.name,'panty liner')

        resp=self.testapp.post(
            add_weights_url,
            params=[
                ('garment',str(pad_id)),
                ('__start__','time_before:mapping'),
                ('date','2020-12-27'),
                ('time','07:30'),
                ('__end__','time_before:mapping'),
                ('__start__','time_after:mapping'),
                ('date','2020-12-27'),
                ('time','17:30'),
                ('__end__','time_after:mapping'),
                ('weight_before','116'),
                ('weight_after','120'),
                ('blood_observed_s','True'),
                ('notes','Note'),
                ('save','save')
            ]
        )
        self.assertEqual(resp.status_code,302)
        record_id=json.loads(resp.text)['id']
        record=session.query(AbsorbentWeights).filter(AbsorbentWeights.id==record_id).one()
        self.assertEqual(record.garment_id,pad_id)
        self.assertEqual(record.garment,pad)
        self.assertEqual(record.time_before,datetime(2020,12,27,7,30))
        self.assertEqual(record.time_after,datetime(2020,12,27,17,30))
        self.assertAlmostEqual(record.weight_before,116)
        self.assertAlmostEqual(record.weight_after,120)
        self.assertEqual(record.blood_observed,True)
        self.assertEqual(record.notes.text,'Note')

        resp=self.testapp.post(
            edit_weights_url.format(record_id),
            params=[
                ('garment',str(pantyliner_id)),
                ('__start__','time_before:mapping'),
                ('date','2020-12-28'),
                ('time','07:45'),
                ('__end__','time_before:mapping'),
                ('__start__','time_after:mapping'),
                ('date','2020-12-28'),
                ('time','16:32'),
                ('__end__','time_after:mapping'),
                ('weight_before','115'),
                ('weight_after','121'),
                ('blood_observed_s','False'),
                ('notes','Note1'),
                ('save','save')
            ]
        )
        record_id=json.loads(resp.text)['id']
        session=self.get_session()
        record=session.query(AbsorbentWeights).filter(AbsorbentWeights.id==record_id).one()
        self.assertEqual(record.garment_id,pantyliner_id)
        self.assertEqual(record.time_before,datetime(2020,12,28,7,45))
        self.assertEqual(record.time_after,datetime(2020,12,28,16,32))
        self.assertAlmostEqual(record.weight_before,115)
        self.assertAlmostEqual(record.weight_after,121)
        self.assertEqual(record.blood_observed,False)
        self.assertEqual(record.notes.text,'Note1')

        resp=self.testapp.post(
            edit_weights_url.format(record_id),
            params=[
                ('garment',str(pantyliner_id)),
                ('blood_observed_s','False'),
                ('delete','delete')
            ])

        self.assertEqual(resp.status_code,302)

        from urllib.parse import quote
        delete_confirm_url=delete_weights_confirm_url.format(record_id)+'?referrer='+quote(edit_weights_url.format(record_id),'')
        self.assertEqual(resp.location,delete_confirm_url)
        record=session.query(AbsorbentWeights).filter(AbsorbentWeights.id==record_id).one()

        resp=self.testapp.post(
            delete_weights_confirm_url.format(record_id),
            params=[
                ('delete','delete')
        ])

        session.flush()
        transaction.commit()

        with self.assertRaises(NoResultFound):
            weight=session.query(AbsorbentWeights).filter(AbsorbentWeights.id==record_id).one()
