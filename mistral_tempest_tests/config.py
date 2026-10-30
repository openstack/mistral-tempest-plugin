# Copyright 2016 Catalyst IT Limited
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg

ServiceAvailableGroup = [cfg.BoolOpt('mistral',
                                     default=True,
                                     help="Whether or not Mistral is expected"
                                          " to be available")]

mistral_group = cfg.OptGroup(name='mistral',
                             title='Mistral test options')

MistralGroup = [
    cfg.URIOpt('http_server_url',
               schemes=('http', 'https'),
               help='Base URL of an HTTP server publishing the content of '
                    'playbooks/tempest/files/http, used by the std.http '
                    'tests. These tests are skipped when not set.'),
]
