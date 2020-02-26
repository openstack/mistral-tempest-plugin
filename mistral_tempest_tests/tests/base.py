# Copyright 2016 NEC Corporation. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os

import mock
from tempest import config
from tempest import test as test

from mistral_tempest_tests.services import base as service_base
from mistral_tempest_tests.services.v2 import mistral_client

CONF = config.CONF


class TestCase(test.BaseTestCase):
    credentials = ['admin', 'primary', 'alt']

    @classmethod
    def skip_checks(cls):
        super(TestCase, cls).skip_checks()

        if not CONF.service_available.mistral:
            raise cls.skipException("Mistral support is required.")

    def setUp(self):
        """Client authentication.

        This method allows to initialize authentication before
        each test case and define parameters of Mistral API Service.
        """
        super(TestCase, self).setUp()

        if 'WITHOUT_AUTH' in os.environ:
            self.mgr = mock.MagicMock()
            self.mgr.auth_provider = service_base.AuthProv()
            self.admin_mgr = self.alt_mgr = self.mgr
        else:
            self.admin_mgr = self.os_admin
            self.mgr = self.os_primary
            self.alt_mgr = self.os_alt

        if self._service == 'workflowv2':
            self.admin_client = mistral_client.MistralClientV2(
                self.admin_mgr.auth_provider, self._service)
            self.client = mistral_client.MistralClientV2(
                self.mgr.auth_provider, self._service)
            self.alt_client = mistral_client.MistralClientV2(
                self.alt_mgr.auth_provider, self._service)

    def assertPartIn(self, needle, haystack, message=''):
        self.assertTrue(any(needle in s for s in haystack), message)

    def tearDown(self):
        super(TestCase, self).tearDown()

        for wb in self.client.workbooks:
            self.client.delete_obj('workbooks', wb)

        self.client.workbooks = []


class TestCaseAdvanced(TestCase):

    def setUp(self):
        super(TestCaseAdvanced, self).setUp()

        self.image_ref = CONF.compute.image_ref
        self.flavor_ref = CONF.compute.flavor_ref

    def tearDown(self):
        for wb in self.client.workbooks:
            self.client.delete_obj('workbooks', wb)

        self.client.workbooks = []

        for ex in self.client.executions:
            self.client.delete_obj('executions', ex, force=True)

        self.client.executions = []

        super(TestCaseAdvanced, self).tearDown()
