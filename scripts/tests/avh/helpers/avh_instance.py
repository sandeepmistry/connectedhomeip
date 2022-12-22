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

import io
import socket
import time

import avh_api
import paramiko

DEFAULT_INSTANCE_FLAVOR = "rpi4b"
DEFAULT_INSTANCE_OS = "Ubuntu Server"
DEFAULT_INSTANCE_OS_VERSION = "22.04.1"

DEFAULT_OS_BOOTED_OUTPUT = "-----END SSH HOST KEY KEYS-----"

DEFAULT_SSH_USERNAME = "pi"
DEFAULT_SSH_PASSWORD = "raspberry"


class AvhInstance:
    def __init__(
        self,
        avh_client,
        name,
        flavor=DEFAULT_INSTANCE_FLAVOR,
        os=DEFAULT_INSTANCE_OS,
        os_version=DEFAULT_INSTANCE_OS_VERSION,
        username=DEFAULT_SSH_USERNAME,
        password=DEFAULT_SSH_PASSWORD,
    ):
        self.avh_client = avh_client
        self.name = name
        self.flavor = flavor
        self.os = os
        self.os_version = os_version
        self.username = username
        self.password = password
        self.instance_id = None
        self.ssh_proxy_client = None
        self.ssh_client = None
        self.ssh_pkey = None
        self.ssh_key_id = None

    def create(self):
        self.instance_id = self.avh_client.create_instance(
            name=self.name, flavor=self.flavor, os=self.os_version, osbuild=self.os
        )

    def wait_for_state_on(self, timeout=180):
        start_time = time.monotonic()

        while True:
            instance_state = self.avh_client.instance_state(self.instance_id)

            if instance_state == "on":
                break
            elif instance_state == "error":
                raise Exception("VM entered error state")
            elif (time.monotonic() - start_time) > timeout:
                raise Exception(
                    f"Timedout waiting for state 'on' for instance id {self.instance_id}"
                )

            time.sleep(1.0)

    def wait_for_os_boot(self, booted_output=DEFAULT_OS_BOOTED_OUTPUT, timeout=240):
        start_time = time.monotonic()

        while True:
            console_log = self.avh_client.instance_console_log(self.instance_id)

            if booted_output in console_log:
                break
            elif (time.monotonic() - start_time) > timeout:
                raise Exception(
                    f"Timedout waiting for OS to boot for instance id {self.instance_id}",
                    f"Did not find {booted_output} in {console_log}",
                )

            time.sleep(1.0)

    def ssh_client(self, timeout=60):
        if self.ssh_client is not None:
            return self.ssh_client

        if self.ssh_pkey is None:
            self.ssh_pkey = paramiko.ecdsakey.ECDSAKey.generate()

            self.ssh_key_id = self.avh_client.create_ssh_project_key(
                self.name, f"{self.ssh_pkey.get_name()} {self.ssh_pkey.get_base64()}"
            )

        instance_quick_connect_command = self.avh_client.instance_quick_connect_command(
            self.instance_id
        )

        split_instance_quick_connect_command = instance_quick_connect_command.split()
        proxy_username = split_instance_quick_connect_command[-2].split("@")[-2]
        proxy_hostname = split_instance_quick_connect_command[-2].split("@")[-1]
        instance_ip = split_instance_quick_connect_command[-1].split("@")[-1]

        self.ssh_proxy_client = paramiko.SSHClient()
        self.ssh_proxy_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.ssh_proxy_client.connect(
            hostname=proxy_hostname,
            username=proxy_username,
            pkey=self.ssh_pkey,
            look_for_keys=False,
        )

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        start_time = time.monotonic()

        while True:
            try:
                proxy_sock = self.ssh_proxy_client.get_transport().open_channel(
                    "direct-tcpip", (instance_ip, 22), ("", 0)
                )

                self.ssh_client.connect(
                    hostname=instance_ip,
                    username=self.username,
                    password=self.password,
                    sock=proxy_sock,
                    timeout=1.0,
                    look_for_keys=False,
                )

                break
            except:
                time.sleep(1.0)

            if (time.monotonic() - start_time) > timeout:
                raise Exception(
                    f"Timedout waiting for SSH connection for instance id {self.instance_id} with IP {instance_ip}"
                )

        return self.ssh_client

    def delete(self):
        if self.ssh_client is not None:
            self.ssh_client.close()

            self.ssh_client = None

        if self.ssh_proxy_client is not None:
            self.ssh_proxy_client.close()

            self.ssh_proxy_client = None

        if self.ssh_key_id is not None:
            self.avh_client.delete_ssh_project_key(self.ssh_key_id)

            self.ssh_key_id = None

        if self.instance_id is not None:
            self.avh_client.delete_instance(self.instance_id)

    def wait_for_state_deleted(self, timeout=60):
        if self.instance_id is None:
            return

        start_time = time.monotonic()

        while True:
            try:
                instance_state = self.avh_client.instance_state(self.instance_id)
            except avh_api.exceptions.NotFoundException:
                break

            if (time.monotonic() - start_time) > timeout:
                raise Exception(
                    f"Timedout waiting for instance id {self.instance_id} to be deleted"
                )

            time.sleep(1.0)

        self.instance_id = None
