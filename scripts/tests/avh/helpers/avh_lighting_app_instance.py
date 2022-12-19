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
        self.shell_channel = None

    def upload_application_binary(self):
        ssh_client = super().ssh_client()

        stfp_client = ssh_client.open_sftp()
        stfp_client.put(self.application_binary_path, APPLICATION_BINARY)
        stfp_client.close()

        ssh_client.exec_command(f"chmod +x {APPLICATION_BINARY}")

    def configure_system(self):
        ssh_client = super().ssh_client()
        # remove the Wi-Fi configuration and disable network manager on the Wi-Fi interface

        ssh_client.exec_command("sudo nmcli connection delete Arm")
        ssh_client.exec_command("sudo nmcli dev set wlan0 managed no")

        # patch and restart wpa_supplication DBus
        ssh_client.exec_command(
            'sudo sed -i "s/wpa_supplicant -u -s -O/wpa_supplicant -u -s -i wlan0 -O/i" /etc/systemd/system/dbus-fi.w1.wpa_supplicant1.service'
        )
        ssh_client.exec_command("sudo systemctl restart wpa_supplicant.service")
        ssh_client.exec_command("sudo systemctl daemon-reload")

    def start_application(self):
        ssh_client = super().ssh_client()

        self.shell_channel = ssh_client.invoke_shell()
        self.shell_channel.send(f"./{APPLICATION_BINARY} --wifi\n")

    def get_application_output(self):
        # TODO: timeout
        while not self.shell_channel.recv_ready():
            time.sleep(1.0)

        output = b""
        while self.shell_channel.recv_ready():
            data = self.shell_channel.recv(1024 * 1024)
            if len(data) == 0:
                break

            output += data
            time.sleep(0.25)

        return output
