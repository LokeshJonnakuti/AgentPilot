import requests


class Browser:
    def __init__(self, computer):
        self.computer = computer

    def search(self, query):
        """
        Searches the web for the specified query and returns the results.
        """
        response = requests.get(
            f'{self.computer.api_base.strip("/")}/browser/search',
            params={"query": query},
        timeout=60)
        return response.json()["result"]
