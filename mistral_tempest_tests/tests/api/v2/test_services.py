#  Copyright 2019 - Nokia Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import testtools

from tempest import config
from tempest.lib import decorators

from mistral_tempest_tests.tests import base

CONF = config.CONF


class ServicesTestsV2(base.TestCase):

    _service = 'workflowv2'

    @decorators.attr(type='sanity')
    @decorators.idempotent_id('f4359ad2-9109-4305-a00a-77679878f7f9')
    @testtools.skipUnless(CONF.mistral_api.service_api_supported,
                          'Service api is not supported')
    def test_get_services_list(self):
        resp, body = self.client.get_list_obj('services')

        self.assertEqual(200, resp.status)
        self.assertNotEmpty(body['services'])
