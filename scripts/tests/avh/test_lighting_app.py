import os
import subprocess
import time

import unittest

from .helpers.avh_client import AvhClient
from .helpers.avh_instance import AvhInstance

AVH_VPN_CONFIG_PATH = '/tmp/avh.ovpn'

class TestLightingApp(unittest.TestCase):
    def setUp(self):
        print('set up')
        self.avh_client = AvhClient(os.environ['AVH_API_TOKEN'])

        self.chip_tool_instance = AvhInstance(self.avh_client)

        print('creating instance ...')
        self.chip_tool_instance.create(
            name='chip-tool',
            flavor='rpi4b',
            os='lite',
            os_version='11.2.0',
        )
        print('instance created.')

        print('saving vpn config')
        self.avh_client.save_vpn_config(AVH_VPN_CONFIG_PATH)

        print('connect vpn')
        # mkdir -p /dev/net
        # mknod /dev/net/tun c 10 200
        self.vpn_subprocess = subprocess.Popen(['openvpn', '--config', AVH_VPN_CONFIG_PATH])

        time.sleep(15)

        print('ssh')
        chip_tool_ssh_client = self.chip_tool_instance.ssh('pi', 'raspberry')

        _, stdout, stderr = chip_tool_ssh_client.exec_command('ls -l /')
        print(stdout.read().decode())
        print(stderr.read().decode())

        # sudo sysctl -w net.ipv6.conf.eth0.disable_ipv6=1


    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

    def tearDown(self):
        print('tear down')

        print('disconnect vpn')
        self.vpn_subprocess.kill()

        print('deleting instance ...')
        self.chip_tool_instance.delete()
        print('instance deleted.')

if __name__ == '__main__':
    unittest.main()
