import os
import signal
import time

import unittest

from .helpers.avh_client import AvhClient
from .helpers.avh_instance import AvhInstance
from .helpers import openvpn

AVH_VPN_CONFIG_PATH = '/tmp/avh.ovpn'

INSTANCE_NAME_PREFIX = 'nightly-test-'

INSTANCE_FLAVOR = 'rpi4b'
INSTANCE_OS = 'Ubuntu Server'
INSTANCE_OS_VERSION = '22.04.1'

SSH_USERNAME = 'pi'
SSH_PASSWORD = 'raspberry'

class TestLightingApp(unittest.TestCase):
    def setUp(self):
        self.avh_client = AvhClient(os.environ['AVH_API_TOKEN'])

        # TODO: delete instances (if applicable)

        self.chip_tool_instance = AvhInstance(
            self.avh_client,
            username=SSH_USERNAME,
            password=SSH_PASSWORD
        )

        self.lighting_app_instance = AvhInstance(
            self.avh_client,
            username=SSH_USERNAME,
            password=SSH_PASSWORD
        )

        print('creating instances ...', end='')
        self.chip_tool_instance.create(
            name=INSTANCE_NAME_PREFIX + 'chip-tool',
            flavor=INSTANCE_FLAVOR,
            os=INSTANCE_OS,
            os_version=INSTANCE_OS_VERSION,
        )

        self.lighting_app_instance.create(
            name=INSTANCE_NAME_PREFIX + 'lighting-app',
            flavor=INSTANCE_FLAVOR,
            os=INSTANCE_OS,
            os_version=INSTANCE_OS_VERSION,
        )

        self.chip_tool_instance.wait_for_state_on()
        self.lighting_app_instance.wait_for_state_on()
        print(' instances created.')

        print('saving vpn config')
        self.avh_client.save_vpn_config(AVH_VPN_CONFIG_PATH)

        print('connect vpn')
        # mkdir -p /dev/net
        # mknod /dev/net/tun c 10 200
        self.vpn_subprocess = openvpn.connect(AVH_VPN_CONFIG_PATH)

        print('wait for OS boot ...', end='')
        self.chip_tool_instance.wait_for_console_output('ubuntu login: ')
        self.lighting_app_instance.wait_for_console_output('ubuntu login: ')
        print(' OS booted.')

        print('ssh ...', end='')
        self.chip_tool_ssh_client = self.chip_tool_instance.ssh()
        self.lighting_app_ssh_client = self.lighting_app_instance.ssh()
        print(' connected')

        print('uploading application binaries ...')
        chip_tool_stfp_client = self.chip_tool_ssh_client.open_sftp()
        chip_tool_stfp_client.put('out/linux-arm64-chip-tool-ipv6only-mbedtls-clang/chip-tool', 'chip-tool')
        chip_tool_stfp_client.close()

        lighting_app_stfp_client = self.lighting_app_ssh_client.open_sftp()
        lighting_app_stfp_client.put('out/linux-arm64-light-ipv6only-mbedtls-clang/chip-lighting-app', 'chip-lighting-app')
        lighting_app_stfp_client.close()

        self.chip_tool_ssh_client.exec_command('chmod +x chip-tool')
        self.lighting_app_ssh_client.exec_command('chmod +x chip-lighting-app')

        print('configuring network manager and WPA supplicant ...')
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
        print('starting chip-lighting-app ...')

        lighting_app_shell_channel = self.lighting_app_ssh_client.invoke_shell()
        lighting_app_shell_channel.send('./chip-lighting-app --wifi\n')
        time.sleep(2.0)
        lighting_app_start_output = lighting_app_shell_channel.recv(999999)

        with open('/tmp/avh_lighting_app.start.output.txt', 'wb') as out:
            out.write(lighting_app_start_output)

        self.assertIn(b'Server Listening...', lighting_app_start_output)

        print('commissioning with chip-tool ...')
        _, stdout, _ = self.chip_tool_ssh_client.exec_command('./chip-tool pairing ble-wifi 17 Arm password 20202021 3840')
        chip_tool_commissioning_output = stdout.read()

        with open('/tmp/avh_chiptool.commissioning.output.txt', 'wb') as out:
            out.write(chip_tool_commissioning_output)

        self.assertIn(b'Device commissioning completed with success', chip_tool_commissioning_output)

        time.sleep(1.0)
        lighting_app_commissioning_output = lighting_app_shell_channel.recv(999999)

        with open('/tmp/avh_lighting_app.commissioning.output.txt', 'wb') as out:
            out.write(lighting_app_commissioning_output)

        self.assertIn(b'Commissioning completed successfully', lighting_app_commissioning_output)

        print('turning light on with chip-tool ...')

        _, stdout, _ = self.chip_tool_ssh_client.exec_command('./chip-tool onoff on 17 1')
        chip_tool_on_output = stdout.read()

        with open('/tmp/avh_chiptool.on.output.txt', 'wb') as out:
            out.write(chip_tool_on_output)

        time.sleep(1.0)
        lighting_app_on_output = lighting_app_shell_channel.recv(999999)

        with open('/tmp/avh_lighting_app.on.output.txt', 'wb') as out:
            out.write(lighting_app_on_output)

        self.assertIn(b'Toggle on/off from 0 to 1', lighting_app_on_output)


        print('turning light off with chip-tool ...')

        _, stdout, _ = self.chip_tool_ssh_client.exec_command('./chip-tool onoff off 17 1')
        chip_tool_off_output = stdout.read()

        with open('/tmp/avh_chiptool.off.output.txt', 'wb') as out:
            out.write(chip_tool_off_output)

        time.sleep(1.0)
        lighting_app_off_output = lighting_app_shell_channel.recv(999999)

        with open('/tmp/avh_lighting_app.off.output.txt', 'wb') as out:
            out.write(lighting_app_off_output)

        self.assertIn(b'Toggle on/off from 1 to 0', lighting_app_off_output)

        lighting_app_shell_channel.close()

    def tearDown(self):
        print('tear down')

        print('disconnect vpn')
        try:
            self.vpn_subprocess.send_signal(signal.SIGINT)
            self.vpn_subprocess.wait(timeout=0.25)
        except:
            pass

        print('deleting instances ...', end='')
        self.chip_tool_instance.delete()
        self.lighting_app_instance.delete()

        self.chip_tool_instance.wait_for_state_deleted()
        self.lighting_app_instance.wait_for_state_deleted()
        print(' instances deleted.')

if __name__ == '__main__':
    unittest.main()
