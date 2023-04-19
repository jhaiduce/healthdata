import unittest
from unittest.mock import patch
import requests
import configparser
import json
import re
from bs4 import BeautifulSoup

class BaseTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        import pyotp

        cls.session=requests.Session()

        cls.config=configparser.ConfigParser()
        cls.config.read('/run/secrets/production.ini')

        cls.admin_password=cls.config['app:main']['admin_password']
        cls.admin_otp_secret=cls.config['app:main']['admin_otp_secret']

        while True:
            try:
                resp=cls.session.post('http://healthdata_web/login',data={
                    'login':'admin',
                    'password':cls.admin_password,
                    'otp':pyotp.TOTP(cls.admin_otp_secret).now(),
                    'form.submitted':'Log+In'
                })
                break
            except requests.exceptions.ConnectionError:
                print('Connection failed. Sleeping before retry.')
                import time
                time.sleep(2)

        assert resp.history[0].status_code==302
        assert resp.history[0].headers['Location']=='http://healthdata_web/period/plot'

    @classmethod
    def tearDownClass(cls):
        resp=cls.session.post('http://healthdata_web/logout')
        assert resp.history[0].status_code==302
        assert resp.history[0].headers['Location']=='http://healthdata_web/period/plot'

        resp=cls.session.get('http://healthdata_web/period')
        assert resp.history[0].status_code==302
        assert resp.history[0].headers['Location']=='http://healthdata_web/login?next=http%3A%2F%2Fhealthdata_web%2Fperiod'

    def test_person_add(self):
        resp=self.session.post('http://healthdata_web/person/add',data={
            'form.submitted':True,
            'submit':'submit',
            'name':'Robert'
        })
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://healthdata_web/person/list')

    def test_period_list(self):
        resp=self.session.get('http://healthdata_web/period')
        self.assertGreater(resp.text.find('entries'),0)

    def test_period_plot(self):
        resp=self.session.get('http://healthdata_web/period/plot')
        self.assertGreater(resp.text.find('<div id="graph-0"'),0)

    def test_period_add(self):
        resp=self.session.get('http://healthdata_web/period')
        entry_count=int(re.search(r'(\d+) entries',resp.text).group(1))

        resp=self.session.post(
            'http://healthdata_web/period/new',
            data=[
                ('__start__','date:mapping'),
                ('date','2020-03-14'),
                ('__end__','date:mapping'),
                ('__start__','temperature_time:mapping'),
                ('time','07:30'),
                ('__end__','temperature_time:mapping'),
                ('temperature','97.9'),
                ('period_intensity','1'),
                ('cervical_fluid_character','1'),
                ('save','save')
            ]
        )

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        # Get the id of the new entry
        submission_metadata=json.loads(resp.history[0].text)
        period_id=submission_metadata['id']

        # Load the period listing page
        resp=self.session.get('http://healthdata_web/period')

        # Check that the entry count was incremented
        new_entry_count=int(re.search(r'(\d+) entries',resp.text).group(1))
        self.assertEqual(new_entry_count,entry_count+1)

        # Check that the new entry is listed
        self.assertGreater(resp.text.find('a href="http://healthdata_web/period/{}/edit"'.format(period_id)),0)

        # Check that the edit screen loads correctly
        resp=self.session.get('http://healthdata_web/period/{}/edit'.format(period_id))

        # Check form content
        soup=BeautifulSoup(resp.text,'html.parser')
        self.assertTrue(soup.find('input',{'name':'temperature',
                                               'value':'97.9'}))
        self.assertTrue(soup.find('input',{'name':'date',
                                               'value':'2020-03-14'}))
        self.assertTrue(soup.find('input',{'name':'time',
                                               'value':'07:30:00'}))
        self.assertTrue(soup.find('textarea',{'name':'notes'}).text=='')

        period_intensity_value=soup.find('select',{'name':'period_intensity'}
        ).find('option',{'selected':'selected'})['value']

        self.assertEqual(period_intensity_value,'1')

        cervical_fluid_value=soup.find('select',{'name':'cervical_fluid_character'}
        ).find('option',{'selected':'selected'})['value']

        self.assertEqual(cervical_fluid_value,'1')

    def test_heightweight_addedit(self):

        resp=self.session.post(
            'http://healthdata_web/height_weight/new',
            data=[
                ('__start__','time:mapping'),
                ('date','2020-03-14'),
                ('time','07:30'),
                ('__end__','time:mapping'),
                ('weight','72.4'),
                ('height','70'),
                ('save','save')
            ]
        )

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        # Get the id of the new entry
        submission_metadata=json.loads(resp.history[0].text)
        heightweight_id=submission_metadata['id']

        # Load the heightweight listing page
        resp=self.session.get('http://healthdata_web/height_weight')

        # Check that the new entry is listed
        self.assertGreater(resp.text.find('a href="http://healthdata_web/height_weight/{}/edit"'.format(heightweight_id)),0)

        # Load the heightweight plot page
        resp=self.session.get('http://healthdata_web/height_weight/plot_weight')
        self.assertEqual(resp.status_code,200)

        # Check that the edit page loads correctly
        resp=self.session.get('http://healthdata_web/height_weight/{}/edit'.format(heightweight_id))

        # Check form content
        soup=BeautifulSoup(resp.text,'html.parser')
        self.assertTrue(soup.find('input',{'name':'weight',
                                           'value':'72.4'}))
        self.assertTrue(soup.find('input',{'name':'height',
                                           'value':'70.0'}))
        self.assertTrue(soup.find('input',{'name':'date',
                                           'value':'2020-03-14'}))
        self.assertTrue(soup.find('input',{'name':'time',
                                               'value':'07:30:00'}))
