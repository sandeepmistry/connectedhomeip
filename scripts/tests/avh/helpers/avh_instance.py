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

import socket
import time

import avh_api
import paramiko

DEFAULT_INSTANCE_FLAVOR = "rpi4b"
DEFAULT_INSTANCE_OS = "Ubuntu Server"
DEFAULT_INSTANCE_OS_VERSION = "22.04.1"

DEFAULT_OS_LOGIN_PROMPT = "ubuntu login: "

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
        self.ssh_client = None

    def create(self):
        self.instance_id = self.avh_client.create_instance(
            name=self.name, flavor=self.flavor, os=self.os_version, osbuild=self.os
        )

    def wait_for_state_on(self):
        # TODO: timeout
        while True:
            instance_state = self.avh_client.instance_state(self.instance_id)

            if instance_state == "on":
                break
            elif instance_state == "error":
                raise Exception("VM entered error state")

            time.sleep(1.0)

    def wait_for_os_boot(self, suffix=DEFAULT_OS_LOGIN_PROMPT):
        # TODO: timeout
        for i in range(2):
            while True:
                if self.avh_client.instance_console_log(self.instance_id).endswith(
                    suffix
                ):
                    break

                time.sleep(1.0)
            time.sleep(2.0)

            self.ssh_client = None

    def ssh_client(self):
        if self.ssh_client is not None:
            return self.ssh_client

        instance_ip = self.avh_client.instance_ip(self.instance_id)

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # TODO: timeout
        while True:
            try:
                self.ssh_client.connect(
                    hostname=instance_ip,
                    username=self.username,
                    password=self.password,
                    timeout=1.0,
                )

                break
            except:
                time.sleep(1.0)

        return self.ssh_client

    def delete(self):
        if self.ssh_client is not None:
            self.ssh_client.close()

            self.ssh_client = None

        if self.instance_id is not None:
            self.avh_client.delete_instance(self.instance_id)

    def wait_for_state_deleted(self):
        if self.instance_id is None:
            return

        # TODO: timeout
        while True:
            try:
                instance_state = self.avh_client.instance_state(self.instance_id)
            except avh_api.exceptions.NotFoundException:
                break

            time.sleep(1.0)

        self.instance_id = None
