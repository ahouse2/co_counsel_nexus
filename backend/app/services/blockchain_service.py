
from __future__ import annotations
import httpx
from typing import Any, Dict, List, Optional

from backend.app.config import get_settings

class BlockchainService:
    """
    A service for interacting with various blockchain APIs to track cryptocurrency assets.
    """

    def __init__(self):
        settings = get_settings()
        self.ethereum_api_key = settings.blockchain_api_key_ethereum
        self.ethereum_api_base = settings.blockchain_api_base_ethereum or "https://api.etherscan.io/api"
        self.bitcoin_api_key = settings.blockchain_api_key_bitcoin
        self.bitcoin_api_base = settings.blockchain_api_base_bitcoin or "https://api.blockchair.com/bitcoin"

    async def get_ethereum_transactions(self, address: str) -> List[Dict[str, Any]]:
        """
        Retrieves Ethereum transaction history for a given address.
        Uses Etherscan API.
        """
        if not self.ethereum_api_key:
            return {"error": "Ethereum API key not configured."}

        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "asc",
            "apikey": self.ethereum_api_key
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.ethereum_api_base, params=params)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "1":
                    return data.get("result", [])
                else:
                    return {"error": data.get("message", "Unknown error from Ethereum API.")}
            except httpx.HTTPStatusError as e:
                return {"error": f"Ethereum API request failed: {e.response.status_code} - {e.response.text}"}
            except httpx.RequestError as e:
                return {"error": f"Ethereum API request error: {e}"}

    async def get_bitcoin_transactions(self, address: str) -> List[Dict[str, Any]]:
        """
        Retrieves Bitcoin transaction history for a given address.
        Uses Blockchair API.
        """
        if not self.bitcoin_api_key:
            return {"error": "Bitcoin API key not configured."}
        
        url = f"{self.bitcoin_api_base}/dashboards/address/{address}"
        params = {"key": self.bitcoin_api_key}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                # Blockchair API structure is different, need to parse
                if data and data.get("data") and data["data"].get(address) and data["data"][address].get("transactions"):
                    return data["data"][address]["transactions"]
                else:
                    return {"error": "No transactions found or unexpected response from Bitcoin API."}
            except httpx.HTTPStatusError as e:
                return {"error": f"Bitcoin API request failed: {e.response.status_code} - {e.response.text}"}
            except httpx.RequestError as e:
                return {"error": f"Bitcoin API request error: {e}"}

    async def get_address_balance(self, address: str, blockchain: str = "ethereum") -> Dict[str, Any]:
        """
        Retrieves the balance for a given cryptocurrency address.
        """
        if blockchain.lower() == "ethereum":
            if not self.ethereum_api_key:
                return {"error": "Ethereum API key not configured."}
            params = {
                "module": "account",
                "action": "balance",
                "address": address,
                "tag": "latest",
                "apikey": self.ethereum_api_key
            }
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(self.ethereum_api_base, params=params)
                    response.raise_for_status()
                    data = response.json()
                    if data.get("status") == "1":
                        return {"balance": int(data.get("result", 0)) / 10**18, "unit": "ETH"} # Convert Wei to ETH
                    else:
                        return {"error": data.get("message", "Unknown error from Ethereum API.")}
                except httpx.HTTPStatusError as e:
                    return {"error": f"Ethereum API request failed: {e.response.status_code} - {e.response.text}"}
                except httpx.RequestError as e:
                    return {"error": f"Ethereum API request error: {e}"}
        elif blockchain.lower() == "bitcoin":
            if not self.bitcoin_api_key:
                return {"error": "Bitcoin API key not configured."}
            url = f"{self.bitcoin_api_base}/dashboards/address/{address}"
            params = {"key": self.bitcoin_api_key}
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    if data and data.get("data") and data["data"].get(address) and data["data"][address].get("address"):
                        balance_satoshi = data["data"][address]["address"].get("balance", 0)
                        return {"balance": balance_satoshi / 10**8, "unit": "BTC"} # Convert Satoshi to BTC
                    else:
                        return {"error": "No balance found or unexpected response from Bitcoin API."}
                except httpx.HTTPStatusError as e:
                    return {"error": f"Bitcoin API request failed: {e.response.status_code} - {e.response.text}"}
                except httpx.RequestError as e:
                    return {"error": f"Bitcoin API request error: {e}"}
        else:
            return {"error": f"Unsupported blockchain: {blockchain}"}
