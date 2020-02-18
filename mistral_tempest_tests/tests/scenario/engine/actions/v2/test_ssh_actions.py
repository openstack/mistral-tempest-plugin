# Copyright 2015 - Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os
from os import path
import testtools
import time

from oslo_log import log as logging
from oslo_serialization import jsonutils
from paramiko import ssh_exception
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions

from mistral_tempest_tests.tests import base
from mistral_tempest_tests.tests import ssh_utils
from mistral_tempest_tests.tests import utils


LOG = logging.getLogger(__name__)
CONF = config.CONF
SSH_KEYS_DIRECTORY = path.expanduser("~/.ssh/")


class SSHActionsTestsV2(base.TestCaseAdvanced):

    _service = 'workflowv2'

    def _create_security_group_rule_ssh(self):
        sec_groups = (
            self.mgr.compute_security_groups_client.
            list_security_groups()
        )
        sec_groups = sec_groups['security_groups']

        default_group = next(
            g for g in sec_groups if g['name'] == 'default'
        )

        rule = (
            self.mgr.compute_security_group_rules_client
            .create_security_group_rule(
                parent_group_id=default_group['id'],
                ip_protocol="tcp",
                from_port=22,
                to_port=22,
                cidr="0.0.0.0/0"
            )
        )

        self.ssh_rule_id = rule['security_group_rule']['id']

    def _create_server(self, server_name, **kwargs):
        return self.mgr.servers_client.create_server(
            name=server_name,
            imageRef=CONF.compute.image_ref,
            flavorRef=CONF.compute.flavor_ref,
            **kwargs
        ).get('server')

    def _associate_floating_ip_to_server(self, server_id):
        fl_ip_client = self.mgr.compute_floating_ips_client

        all_ips = fl_ip_client.list_floating_ips().get(
            'floating_ips'
        )
        free_ips = list(
            [fl_ip for fl_ip in all_ips if fl_ip['instance_id'] is None]
        )

        if free_ips:
            ip = free_ips[0]['ip']
        else:
            # Allocate new floating ip.
            ip = fl_ip_client.create_floating_ip()['floating_ip']['ip']

        # Associate IP.
        fl_ip_client.associate_floating_ip_to_server(
            floating_ip=ip,
            server_id=server_id
        )

        return ip

    @staticmethod
    def _wait_until_server_up(server_ip, timeout=120, delay=2):
        seconds_remain = timeout

        LOG.info("Waiting server SSH [IP=%s]...", server_ip)

        while seconds_remain > 0:
            try:
                ssh_utils.execute_command('cd', server_ip, None)
            except ssh_exception.SSHException:
                LOG.info("Server %s: SSH service is ready.")
                return
            except Exception as e:
                LOG.info(str(e))
                seconds_remain -= delay
                time.sleep(delay)
            else:
                return

        raise Exception(
            "Failed waiting until server's '%s' SSH is up." % server_ip
        )

    def _wait_until_server_active(self, server_id, timeout=60, delay=2):
        seconds_remain = timeout

        LOG.info("Waiting server [id=%s]...", server_id)

        while seconds_remain > 0:
            server_info = self.mgr.servers_client.show_server(server_id)
            if server_info['server']['status'] == 'ACTIVE':
                return

            seconds_remain -= delay
            time.sleep(delay)

        raise Exception(
            "Failed waiting until server %s is active." % server_id
        )

    def _wait_until_server_delete(self, server_id, timeout=60, delay=2):
        seconds_remain = timeout

        LOG.info("Deleting server [id=%s]...", server_id)

        while seconds_remain > 0:
            try:
                self.mgr.servers_client.show_server(server_id)
                seconds_remain -= delay
                time.sleep(delay)
            except exceptions.NotFound:
                return

        raise RuntimeError("Server delete timeout!")

    def setUp(self):
        super(SSHActionsTestsV2, self).setUp()

        # Modify security group for accessing VM via SSH.
        self._create_security_group_rule_ssh()

        # Create keypair (public and private keys).
        self.private_key, self.public_key = utils.generate_key_pair()
        self.key_name = 'mistral-functional-tests-key'

        self.key_dir = SSH_KEYS_DIRECTORY

        self.key_path = self.key_dir + self.key_name

        utils.save_text_to(
            self.private_key,
            self.key_path,
            overwrite=True
        )

        LOG.info("Private key saved to %s", self.key_path)

        # Create keypair in nova.
        self.mgr.keypairs_client.create_keypair(
            name=self.key_name,
            public_key=self.public_key
        )

        # Start servers and provide key_name.
        # Note: start public vm only after starting the guest one,
        # so we can track public vm launching using ssh, but can't
        # do the same with guest VM.
        self.guest_vm = self._create_server(
            'mistral-guest-vm',
            key_name=self.key_name
        )
        self.public_vm = self._create_server(
            'mistral-public-vm',
            key_name=self.key_name
        )

        self._wait_until_server_active(self.public_vm['id'])

        self.public_vm_ip = self._associate_floating_ip_to_server(
            self.public_vm['id']
        )

        # Wait until server is up.
        self._wait_until_server_up(self.public_vm_ip)

        # Update servers info.
        self.public_vm = self.mgr.servers_client.show_server(
            self.public_vm['id']
        ).get('server')

        self.guest_vm = self.mgr.servers_client.show_server(
            self.guest_vm['id']
        ).get('server')

    def tearDown(self):
        mgr = self.mgr

        fl_ip_client = mgr.compute_floating_ips_client
        fl_ip_client.disassociate_floating_ip_from_server(
            self.public_vm_ip,
            self.public_vm['id']
        )

        mgr.servers_client.delete_server(self.public_vm['id'])
        mgr.servers_client.delete_server(self.guest_vm['id'])

        self._wait_until_server_delete(self.public_vm['id'])
        self._wait_until_server_delete(self.guest_vm['id'])

        mgr.keypairs_client.delete_keypair(self.key_name)

        mgr.compute_security_group_rules_client.delete_security_group_rule(
            self.ssh_rule_id
        )
        os.remove(self.key_path)

        super(SSHActionsTestsV2, self).tearDown()

    @decorators.attr(type='sanity')
    @testtools.skip('https://bugs.launchpad.net/mistral/+bug/1822969')
    @decorators.idempotent_id('3e12a2ad-5b10-46b0-ae1f-ed34d3cc6ae2')
    def test_run_ssh_action(self):
        input_data = {
            'cmd': 'hostname',
            'host': self.public_vm_ip,
            'username': CONF.validation.image_ssh_user,
            'private_key_filename': self.key_path
        }

        resp, body = self.client.create_action_execution(
            {
                'name': 'std.ssh',
                'input': jsonutils.dump_as_bytes(input_data)
            }
        )

        self.assertEqual(201, resp.status)

        output = jsonutils.loads(body['output'])

        self.assertIn(self.public_vm['name'], output['result'])

    @decorators.attr(type='sanity')
    @testtools.skip('https://bugs.launchpad.net/mistral/+bug/1822969')
    @decorators.idempotent_id('6c09fb04-70b4-43a6-b5f8-a53ca92e66e0')
    def test_run_ssh_proxied_action(self):
        guest_vm_ip = self.guest_vm['addresses'].popitem()[1][0]['addr']

        input_data = {
            'cmd': 'hostname',
            'host': guest_vm_ip,
            'username': CONF.validation.image_ssh_user,
            'private_key_filename': self.key_path,
            'gateway_host': self.public_vm_ip,
            'gateway_username': CONF.validation.image_ssh_user
        }

        resp, body = self.client.create_action_execution(
            {
                'name': 'std.ssh_proxied',
                'input': jsonutils.dump_as_bytes(input_data)
            }
        )

        self.assertEqual(201, resp.status)

        output = jsonutils.loads(body['output'])

        self.assertIn(self.guest_vm['name'], output['result'])
