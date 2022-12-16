import os
import signal
import time

import unittest

from .helpers.avh_client import AvhClient
from .helpers.avh_instance import AvhInstance
from .helpers import openvpn

AVH_VPN_CONFIG_PATH = '/tmp/avh.ovpn'

class TestLightingApp(unittest.TestCase):
    def setUp(self):
        print('set up')
        self.avh_client = AvhClient(os.environ['AVH_API_TOKEN'])

        # TODO: delete instances (if applicable)

        self.chip_tool_instance = AvhInstance(
            self.avh_client,
            username='pi',
            password='raspberry'
        )

        self.lighting_app_instance = AvhInstance(
            self.avh_client,
            username='pi',
            password='raspberry'
        )

        print('creating instances', end=' ')
        self.chip_tool_instance.create(
            name='nightly-test-chip-tool',
            flavor='rpi4b',
            os='Ubuntu Server',
            os_version='22.04.1',
        )

        self.lighting_app_instance.create(
            name='nightly-test-lighting-app',
            flavor='rpi4b',
            os='Ubuntu Server',
            os_version='22.04.1',
        )

        self.chip_tool_instance.wait_for_state_on()
        self.lighting_app_instance.wait_for_state_on()
        print('instances created.')

        print('saving vpn config')
        self.avh_client.save_vpn_config(AVH_VPN_CONFIG_PATH)

        print('connect vpn')
        # mkdir -p /dev/net
        # mknod /dev/net/tun c 10 200
        self.vpn_subprocess = openvpn.connect(AVH_VPN_CONFIG_PATH)

        print('wait for OS boot', end=' ')
        self.chip_tool_instance.wait_for_console_output('ubuntu login: ')
        self.lighting_app_instance.wait_for_console_output('ubuntu login: ')
        print('OS booted.')

        print('ssh')
        self.chip_tool_ssh_client = self.chip_tool_instance.ssh()
        self.lighting_app_ssh_client = self.lighting_app_instance.ssh()

        chip_tool_stfp_client = self.chip_tool_ssh_client.open_sftp()
        chip_tool_stfp_client.put('out/linux-arm64-chip-tool-ipv6only-mbedtls-clang/chip-tool', 'chip-tool')
        chip_tool_stfp_client.close()

        lighting_app_stfp_client = self.lighting_app_ssh_client.open_sftp()
        lighting_app_stfp_client.put('out/linux-arm64-light-ipv6only-mbedtls-clang/chip-lighting-app', 'chip-lighting-app')
        lighting_app_stfp_client.close()

        self.chip_tool_ssh_client.exec_command('chmod +x chip-tool')
        self.lighting_app_ssh_client.exec_command('chmod +x chip-lighting-app')

        # remove the Wi-Fi configuration and disable network manager on the Wi-Fi interface
        # disable IPv6 on the Ethernet interface
        # patch and restart wpa_supplication DBus
        self.lighting_app_ssh_client.exec_command('sudo nmcli connection delete Arm')
        self.lighting_app_ssh_client.exec_command('sudo nmcli dev set wlan0 managed no')
        # self.lighting_app_ssh_client.exec_command('sudo sysctl -w net.ipv6.conf.eth0.disable_ipv6=1')
        self.lighting_app_ssh_client.exec_command('sudo sed -i "s/wpa_supplicant -u -s -O/wpa_supplicant -u -s -i wlan0 -O/i" /etc/systemd/system/dbus-fi.w1.wpa_supplicant1.service')
        self.lighting_app_ssh_client.exec_command('sudo systemctl restart wpa_supplicant.service')
        self.lighting_app_ssh_client.exec_command('sudo systemctl daemon-reload')

    def test_commissioning_and_control(self):
        lighting_app_shell_channel = self.lighting_app_ssh_client.invoke_shell()
        lighting_app_shell_channel.send('./chip-lighting-app --wifi\n')
        time.sleep(2.0)
        lighting_app_start_output = lighting_app_shell_channel.recv(999999)

        self.assertIn(b'Server Listening...', lighting_app_start_output)

        _, stdout, _ = self.chip_tool_ssh_client.exec_command('./chip-tool pairing ble-wifi 17 Arm password 20202021 3840')
        chip_tool_pairing_ouput = stdout.read()

        self.assertIn(b'Device commissioning completed with success', chip_tool_pairing_ouput)

        time.sleep(1.0)
        lighting_app_commissioning_output = lighting_app_shell_channel.recv(999999)
        self.assertIn(b'Commissioning completed successfully', lighting_app_commissioning_output)

        _, _, _ = self.chip_tool_ssh_client.exec_command('./chip-tool onoff on 17 1')

        time.sleep(1.0)
        lighting_app_on_output = lighting_app_shell_channel.recv(999999)
        self.assertIn(b'Toggle on/off from 0 to 1', lighting_app_on_output)

        _, _, _ = self.chip_tool_ssh_client.exec_command('./chip-tool onoff off 17 1')

        time.sleep(1.0)
        lighting_app_off_output = lighting_app_shell_channel.recv(999999)
        self.assertIn(b'Toggle on/off from 1 to 0', lighting_app_off_output)

        lighting_app_shell_channel.close()

    def tearDown(self):
        print('tear down')

        # print('disconnect vpn')
        # self.vpn_subprocess.send_signal(signal.SIGINT)
        # self.vpn_subprocess.wait(timeout=0.25)

        print('deleting instances ...')
        self.chip_tool_instance.delete()
        self.lighting_app_instance.delete()

        self.chip_tool_instance.wait_for_state_deleted()
        self.lighting_app_instance.wait_for_state_deleted()
        print('instances deleted.')

if __name__ == '__main__':
    unittest.main()
