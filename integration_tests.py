import unittest
from unittest.mock import patch
import requests
import configparser
import json
import re
from bs4 import BeautifulSoup

class BaseTest(unittest.TestCase):

    def setUp(self):
        self.session=requests.Session()

        self.config=configparser.ConfigParser()
        self.config.read('/run/secrets/production.ini')

        self.admin_password=self.config['app:main']['admin_password']

        while True:
            try:
                resp=self.session.post('http://healthdata_web/login',data={
                    'login':'admin',
                    'password':self.admin_password,
                    'form.submitted':'Log+In'
                })
                break
            except requests.exceptions.ConnectionError:
                print('Connection failed. Sleeping before retry.')
                import time
                time.sleep(2)

        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://healthdata_web/period')

    def tearDown(self):
        resp=self.session.post('http://healthdata_web/logout')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://healthdata_web/period')

        resp=self.session.get('http://healthdata_web/period')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://healthdata_web/login?next=http%3A%2F%2Fhealthdata_web%2Fperiod')

    def test_period_list(self):
        resp=self.session.get('http://healthdata_web/period/list')
        self.assertGreater(resp.text.find('entries'),0)

    def test_period_plot(self):
        resp=self.session.get('http://healthdata_web/period')
        self.assertGreater(resp.text.find('<div class="bk-root"'),0)

    def test_period_add(self):
        resp=self.session.get('http://healthdata_web/period/list')
        entry_count=int(re.search(r'(\d+) entries',resp.text).group(1))

        resp=self.session.post(
            'http://healthdata_web/period/add',
            data=[
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

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        # Get the id of the new entry
        submission_metadata=json.loads(resp.history[0].text)
        period_id=submission_metadata['period_id']

        # Load the period listing page
        resp=self.session.get('http://healthdata_web/period/list')

        # Check that the entry count was incremented
        new_entry_count=int(re.search(r'(\d+) entries',resp.text).group(1))
        self.assertEqual(new_entry_count,entry_count+1)

        # Check that the new entry is listed
        self.assertGreater(resp.text.find('a href="/period/{}/edit"'.format(period_id)),0)

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

        cervical_fluid_value=soup.find('select',{'name':'cervical_fluid'}
        ).find('option',{'selected':'selected'})['value']

        self.assertEqual(cervical_fluid_value,'1')
