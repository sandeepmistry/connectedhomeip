# Arm Virtual Hardware (AVH) based tests

This folder contains end to end tests that use the [Arm Virtual Hardware (AVH)](https://www.arm.com/products/development-tools/simulation/virtual-hardware) service.

The tests require the `AVH_API_TOKEN` enviroment variable is set with the value from `AVH -> Profile -> API -> API Token`.

## Current tests

 * [`test_lighting_app.py`](test_lighting_app.py)
   * This test uses two virtual Raspberry Pi Model 4 boards running Ubuntu Server 22.04 and prebuilt `chip-tool` and `chip-lighting-app` binaries (`linux-arm64`), and tests commissioning and control over BLE and Wi-Fi via AVH's virtual Bluetooth and Wi-Fi network feature.
