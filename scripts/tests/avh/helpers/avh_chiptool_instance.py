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

from .avh_instance import AvhInstance

APPLICATION_BINARY = "chip-tool"


class AvhChiptoolInstance(AvhInstance):
    def __init__(self, avh_client, name, application_binary_path):
        super().__init__(avh_client, name)

        self.application_binary_path = application_binary_path

    def upload_application_binary(self):
        ssh_client = super().ssh_client()

        stfp_client = ssh_client.open_sftp()
        stfp_client.put(self.application_binary_path, APPLICATION_BINARY)
        stfp_client.close()

        ssh_client.exec_command(f"chmod +x {APPLICATION_BINARY}")

    def pairing_ble_wifi(self, node_id, ssid, password, pin_code, discriminator):
        ssh_client = super().ssh_client()

        _, stdout, _ = ssh_client.exec_command(
            f"./{APPLICATION_BINARY} pairing ble-wifi {node_id} {ssid} {password} {pin_code} {discriminator}"
        )

        return stdout.read()

    def on(self, node_id):
        ssh_client = super().ssh_client()

        _, stdout, _ = ssh_client.exec_command(
            f"./{APPLICATION_BINARY} onoff on {node_id} 1"
        )

        return stdout.read()

    def off(self, node_id):
        ssh_client = super().ssh_client()

        _, stdout, _ = ssh_client.exec_command(
            f"./{APPLICATION_BINARY} onoff off {node_id} 1"
        )

        return stdout.read()