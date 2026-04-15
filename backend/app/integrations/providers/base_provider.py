from abc import ABC, abstractmethod
import backoff
import requests

class BaseProvider(ABC):
    @abstractmethod
    def get_balance(self, address: str):
        pass

    @abstractmethod
    def get_transactions(self, address: str, limit: int = 10):
        pass

    @abstractmethod
    def get_token_balances(self, address: str):
        pass

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def _make_rpc_call(self, url: str, method: str, params: list):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
