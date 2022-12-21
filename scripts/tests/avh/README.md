# Arm Virtual Hardware (AVH) based tests

This folder contains end to end tests that use the [Arm Virtual Hardware (AVH)](https://www.arm.com/products/development-tools/simulation/virtual-hardware) service.

The tests require the `AVH_API_TOKEN` environment variable is set with the value from `AVH -> Profile -> API -> API Token` and the `AVH_SSH_KEY` environment variable is set with an [authorized private key](https://intercom.help/arm-avh/en/articles/6347261-quick-connect#h_38318e6a2f) from `AVH -> Profile -> Admin -> Settings`.

## Current tests

 * [`test_lighting_app.py`](test_lighting_app.py)
   * This test uses two virtual Raspberry Pi Model 4 boards running Ubuntu Server 22.04 and pre-built `chip-tool` and `chip-lighting-app` binaries (`linux-arm64`), and tests commissioning and control over BLE and Wi-Fi using the virtual Bluetooth and Wi-Fi network features of AVH.
