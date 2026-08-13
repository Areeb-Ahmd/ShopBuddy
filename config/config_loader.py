import os
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")

def load_config(config_path: str = None):
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    elif not os.path.isabs(config_path) and not os.path.exists(config_path):
        config_path = os.path.join(BASE_DIR, config_path)

    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config