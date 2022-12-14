import subprocess

def connect(config_file_path):
    return subprocess.Popen(['sudo', 'openvpn', '--config', config_file_path])
