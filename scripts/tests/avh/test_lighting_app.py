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

import logging
import os
import sys
import unittest

from helpers.avh_chiptool_instance import AvhChiptoolInstance
from helpers.avh_client import AvhClient
from helpers.avh_instance import AvhInstance
from helpers.avh_lighting_app_instance import AvhLightingAppInstance

INSTANCE_NAME_PREFIX = "matter-test-"
CHIP_TOOL_INSTANCE_NAME = INSTANCE_NAME_PREFIX + "chip-tool"
LIGHTING_APP_INSTANCE_NAME = INSTANCE_NAME_PREFIX + "lighting-app"


TEST_NODE_ID = 17
TEST_WIFI_SSID = "Arm"
TEST_WIFI_PASSWORD = "password"
TEST_PIN_CODE = 20202021
TEST_DISCRIMINATOR = 3840

if "AVH_API_TOKEN" not in os.environ:
    raise Exception("Please set AVH_API_TOKEN environment variable value")


class TestLightingApp(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        stdout_logger_handler = logging.StreamHandler(sys.stdout)
        stdout_logger_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        self.logger.addHandler(stdout_logger_handler)

        self.avh_client = AvhClient(
            api_token=os.environ["AVH_API_TOKEN"],
            api_endpoint=os.environ["AVH_API_ENDPOINT"]
            if "AVH_API_ENDPOINT" in os.environ
            else None,
        )

        self.cleanupExistingInstances(
            [CHIP_TOOL_INSTANCE_NAME, LIGHTING_APP_INSTANCE_NAME]
        )

        self.chip_tool_instance = AvhChiptoolInstance(
            self.avh_client,
            name=CHIP_TOOL_INSTANCE_NAME,
            application_binary_path="out/linux-arm64-chip-tool-ipv6only-mbedtls-clang-minmdns-verbose/chip-tool",
        )

        self.lighting_app_instance = AvhLightingAppInstance(
            self.avh_client,
            name=LIGHTING_APP_INSTANCE_NAME,
            application_binary_path="out/linux-arm64-light-ipv6only-mbedtls-clang-minmdns-verbose/chip-lighting-app",
        )

        self.logger.info("creating instances ...")
        self.addCleanup(self.cleanupInstances)

        self.chip_tool_instance.create()
        self.lighting_app_instance.create()

        self.chip_tool_instance.wait_for_state_on()
        self.lighting_app_instance.wait_for_state_on()

        self.logger.info("waiting for OS to boot ...")
        self.chip_tool_instance.wait_for_os_boot()
        self.lighting_app_instance.wait_for_os_boot()

        self.logger.info("uploading application binaries ...")
        self.chip_tool_instance.upload_application_binary()
        self.lighting_app_instance.upload_application_binary()

        self.logger.info("configuring systems ...")
        self.chip_tool_instance.configure_system()
        self.lighting_app_instance.configure_system()

    def test_commissioning_and_control(self):
        self.logger.info("starting chip-lighting-app ...")
        self.lighting_app_instance.start_application()

        lighting_app_start_output = self.lighting_app_instance.get_application_output()
        self.assertIn(b"Server Listening...", lighting_app_start_output)

        self.logger.info("commissioning with chip-tool using BLE pairing ...")
        chip_tool_commissioning_output = self.chip_tool_instance.pairing_ble_wifi(
            TEST_NODE_ID,
            TEST_WIFI_SSID,
            TEST_WIFI_PASSWORD,
            TEST_PIN_CODE,
            TEST_DISCRIMINATOR,
        )

        self.assertIn(
            b"Device commissioning completed with success",
            chip_tool_commissioning_output,
        )

        lighting_app_commissioning_output = (
            self.lighting_app_instance.get_application_output()
        )

        self.assertIn(
            b"Commissioning completed successfully", lighting_app_commissioning_output
        )

        self.logger.info("turning light on with chip-tool ...")
        chip_tool_on_output = self.chip_tool_instance.on(TEST_NODE_ID)
        self.assertIn(b"Received Command Response Status for", chip_tool_on_output)

        lighting_app_on_output = self.lighting_app_instance.get_application_output()
        self.assertIn(b"Toggle ep1 on/off from state 0 to 1", lighting_app_on_output)

        self.logger.info("turning light off with chip-tool ...")
        chip_tool_off_output = self.chip_tool_instance.off(TEST_NODE_ID)
        self.assertIn(b"Received Command Response Status for", chip_tool_off_output)

        lighting_app_off_output = self.lighting_app_instance.get_application_output()
        self.assertIn(b"Toggle ep1 on/off from state 1 to 0", lighting_app_off_output)

        self.logger.info("stopping chip-lighting-app ...")
        self.lighting_app_instance.stop_application()

    def cleanupExistingInstances(self, instance_names):
        existing_instances = []

        for instance_name in instance_names:
            existing_instances += self.avh_client.get_instances(name=instance_name)

        if len(existing_instances) == 0:
            return

        existing_avh_instances = list(
            map(
                lambda instance: AvhInstance(
                    self.avh_client, name=instance["name"], instance_id=instance["id"]
                ),
                existing_instances,
            )
        )

        self.logger.info(
            f"deleting {len(existing_avh_instances)} existing instances ..."
        )

        for avh_instance in existing_avh_instances:
            avh_instance.delete()

        for avh_instance in existing_avh_instances:
            avh_instance.wait_for_state_deleted()

    def cleanupInstances(self):
        self.logger.info("deleting instances ...")
        self.chip_tool_instance.delete()
        self.lighting_app_instance.delete()

        self.chip_tool_instance.wait_for_state_deleted()
        self.lighting_app_instance.wait_for_state_deleted()

        self.avh_client.close()


if __name__ == "__main__":
    unittest.main()