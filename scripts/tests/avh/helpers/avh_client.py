from avh_api import Configuration as AvhApiConfiguration
from avh_api import ApiClient as AvhApiClient
from avh_api.api.arm_api import ArmApi as AvhApi


class AvhClient:
    def __init__(self, api_token):
        avh_api_config = AvhApiConfiguration()
        self.avh_api_client = AvhApiClient(avh_api_config)

        self.avh_api = AvhApi(self.avh_api_client)

        avh_api_config.access_token = self.avh_api.v1_auth_login(
            {"api_token": api_token}
        ).token

        self.default_project_id = self.avh_api.v1_get_projects()[0]["id"]

    def create_instance(self, name, flavor, os, osbuild):
        instance_id = self.avh_api.v1_create_instance(
            {
                "name": name,
                "project": self.default_project_id,
                "flavor": flavor,
                "os": os,
                "osbuild": osbuild,
            }
        )["id"]

        return instance_id

    def instance_state(self, instance_id):
        return str(self.avh_api.v1_get_instance_state(instance_id))

    def instance_console_log(self, instance_id):
        return str(self.avh_api.v1_get_instance_console_log(instance_id))

    def instance_ip(self, instance_id):
        return self.avh_api.v1_get_instance(instance_id)["wifi_ip"]

    def delete_instance(self, instance_id):
        self.avh_api.v1_delete_instance(instance_id)

    def save_vpn_config(self, path):
        vpn_config = self.avh_api.v1_get_project_vpn_config(self.default_project_id)

        with open(path, "w") as out:
            out.write(vpn_config)
