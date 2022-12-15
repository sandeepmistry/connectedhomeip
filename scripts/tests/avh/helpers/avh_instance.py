import socket
import time

import avh_api
import paramiko

class AvhInstance:
    def __init__(self, avh_client, username=None, password=None):
        self.avh_client = avh_client
        self.username = username
        self.password = password
        self.instance_id = None

    def create(self, name, flavor, os, os_version):
        self.instance_id = self.avh_client.create_instance(
            name=name,
            flavor= flavor,
            os=os_version,
            osbuild=os
        )

    def wait_for_state_on(self):
        # TODO: timeout
        while True:
            instance_state = self.avh_client.instance_state(self.instance_id)

            if instance_state == 'on':
                break
            elif instance_state == 'error':
                raise Exception('VM entered error state')

            print('.', end='')
            time.sleep(1.0)

    def wait_for_console_output(self, suffix):
        # TODO: timeout
        while True:
            if self.console_log().endswith(suffix):
                break

            print('.', end='')
            time.sleep(1.0)

    def console_log(self):
        return self.avh_client.instance_console_log(self.instance_id)

    def ssh(self):
        instance_ip = self.avh_client.instance_ip(self.instance_id)

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        while True:
            try:
                self.ssh_client.connect(
                    hostname=instance_ip,
                    username=self.username,
                    password=self.password,
                    timeout=1.0
                )

                break
            except:
                print('.', end='')
                time.sleep(1.0)

        return self.ssh_client

    def delete(self):
        if self.ssh_client is not None:
            self.ssh_client.close()

        self.avh_client.delete_instance(self.instance_id)

    def wait_for_state_deleted(self):
        # TODO: timeout
        while True:
            try:
                instance_state = self.avh_client.instance_state(self.instance_id)
            except avh_api.exceptions.NotFoundException:
                print('')
                break

            print('.', end='')
            time.sleep(1.0)
