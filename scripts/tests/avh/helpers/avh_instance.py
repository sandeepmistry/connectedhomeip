import time

import avh_api
import paramiko

class AvhInstance:
    def __init__(self, avh_client, instance_id=None):
        self.avh_client = avh_client
        self.instance_id = instance_id
        self.ssh_client = None

    def create(self, name, flavor, os, os_version):
        self.instance_id = self.avh_client.create_instance(
            name=name,
            flavor= flavor,
            os=os_version,
            osbuild=os
        )

        # TODO: timeout
        while True:
            instance_state = self.avh_client.instance_state(self.instance_id)

            if instance_state == 'on':
                break
            elif instance_state == 'error':
                raise Exception('VM entered error state')

            time.sleep(0.1)

    def ssh(self, username, password):
        instance_ip = self.avh_client.instance_ip(self.instance_id)

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.ssh_client.connect(
            hostname=instance_ip,
            username=username,
            password=password
        )

        return self.ssh_client

    def delete(self):
        self.avh_client.delete_instance(self.instance_id)

        # TODO: timeout
        while True:
            try:
                instance_state = self.avh_client.instance_state(self.instance_id)
            except avh_api.exceptions.NotFoundException:
                break

            time.sleep(0.1)

        if self.ssh_client is not None:
            self.ssh_client.close()
