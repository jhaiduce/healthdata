import unittest
from unittest.mock import patch
import requests
import configparser
import json
import re

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
