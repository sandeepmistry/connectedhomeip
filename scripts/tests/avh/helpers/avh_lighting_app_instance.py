# Copyright (c) 2022 Project CHIP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

from .avh_instance import AvhInstance

APPLICATION_BINARY = "chip-lighting-app"


class AvhLightingAppInstance(AvhInstance):
    def __init__(self, avh_client, name, application_binary_path):
        super().__init__(avh_client, name)

        self.application_binary_path = application_binary_path
        self.lighting_app_ssh_client = None
        self.lighting_app_shell_channel = None

    def upload_application_binary(self):
        super().upload_application_binary(
            self.application_binary_path, APPLICATION_BINARY
        )

    def configure_system(self):
        # remove the Wi-Fi configuration and disable network manager on the Wi-Fi interface

        self.exec_command("sudo nmcli connection delete Arm")
        self.exec_command("sudo nmcli dev set wlan0 managed no")

        # patch and restart wpa_supplication DBus
        self.exec_command(
            'sudo sed -i "s/wpa_supplicant -u -s -O/wpa_supplicant -u -s -i wlan0 -O/i" /etc/systemd/system/dbus-fi.w1.wpa_supplicant1.service'
        )
        self.exec_command("sudo systemctl restart wpa_supplicant.service")
        self.exec_command("sudo systemctl daemon-reload")

    def start_application(self):
        self.lighting_app_ssh_client = super().ssh_client()

        self.lighting_app_shell_channel = self.lighting_app_ssh_client.invoke_shell()
        self.lighting_app_shell_channel.send(f"./{APPLICATION_BINARY} --wifi\n")

    def stop_application(self):
        if self.lighting_app_shell_channel is not None:
            self.lighting_app_shell_channel.close()

            self.lighting_app_shell_channel = None

        if self.lighting_app_ssh_client is not None:
            self.lighting_app_ssh_client.close()

            self.lighting_app_ssh_client = None

    def get_application_output(self, timeout=30):
        start_time = time.monotonic()
        output = b""

        while not self.lighting_app_shell_channel.recv_ready():
            if (time.monotonic() - start_time) > timeout:
                break

            time.sleep(1.0)

        while self.lighting_app_shell_channel.recv_ready():
            data = self.lighting_app_shell_channel.recv(1024 * 1024)
            if len(data) == 0:
                break

            output += data
            time.sleep(0.25)

        return output
