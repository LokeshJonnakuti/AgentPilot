import json
import os
from src.utils import sql


class APIManager:
    def __init__(self):
        self.apis = {}

    def load(self):
        self.apis = {}
        apis = sql.get_results("""
            SELECT
                name,
                client_key,
                priv_key AS api_key,
                config
            FROM apis""")
        for api_name, client_key, api_key, api_config in apis:
            if api_key.startswith('$'):
                api_key = os.environ.get(api_key[1:], '')
            if client_key.startswith('$'):
                client_key = os.environ.get(client_key[1:], '')

            self.apis[api_name] = {
                'client_key': client_key,
                'api_key': api_key,
                'config': json.loads(api_config)
            }

    def to_dict(self):
        return self.apis
