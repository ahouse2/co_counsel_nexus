import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

# External libraries for blockchain interaction
try:
    from web3 import Web3
    from web3.exceptions import TransactionNotFound
except ImportError:
    Web3 = None
    TransactionNotFound = None

try:
    import bitcoinlib
    from bitcoinlib.keys import Address as BitcoinAddress
    from bitcoinlib.services.services import Service as BitcoinService
except ImportError:
    bitcoinlib = None
    BitcoinAddress = None
    BitcoinService = None

import requests
from neo4j import GraphDatabase

from backend.app.config import get_settings

from backend.app.forensics.models import WalletAddress, Transaction, CryptoTracingResult

class CryptoTracer:
    """
    Identifies, extracts, and traces cryptocurrency wallet addresses and transactions.
    Integrates with real blockchain APIs and Neo4j for data storage and graph generation.
    """
    def __init__(self):
        settings = get_settings()
        self.neo4j_driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.ethereum_api_key = settings.blockchain_api_key_ethereum
        self.ethereum_api_base = settings.blockchain_api_base_ethereum or "https://mainnet.infura.io/v3/"
        self.bitcoin_api_key = settings.blockchain_api_key_bitcoin
        self.bitcoin_api_base = settings.blockchain_api_base_bitcoin # Not directly used by bitcoinlib, but good to have

        if Web3 and self.ethereum_api_key:
            self.w3 = Web3(Web3.HTTPProvider(f"{self.ethereum_api_base}{self.ethereum_api_key}"))
            if not self.w3.is_connected():
                print("Warning: Could not connect to Ethereum network via web3.py.")
                self.w3 = None
        else:
            self.w3 = None
            if self.ethereum_api_key:
                print("Warning: web3.py not installed, cannot connect to Ethereum.")

        if bitcoinlib:
            # bitcoinlib typically uses its own service providers,
            # but we can configure it if needed or use direct API calls.
            pass
        else:
            print("Warning: bitcoinlib not installed, cannot process Bitcoin addresses robustly.")

    def __del__(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()

    def trace_document_for_crypto(self, document_content: str, document_id: str) -> CryptoTracingResult:
        """
        Scans document content for crypto wallet addresses, performs on-chain analysis,
        stores data in Neo4j, and generates a Mermaid graph.
        """
        wallets = self._extract_wallet_addresses(document_content)
        transactions = []
        
        if wallets:
            transactions = self._perform_on_chain_analysis(wallets)
            self._store_crypto_data_in_neo4j(document_id, wallets, transactions)
        
        mermaid_graph = self._generate_graph_data(document_id)

        details = f"Found {len(wallets)} potential wallet addresses."
        if transactions:
            details += f" Traced {len(transactions)} transactions."
        if not wallets and not transactions:
            details = "No cryptocurrency activity detected."

        return CryptoTracingResult(
            wallets_found=wallets,
            transactions_traced=transactions,
            visual_graph_mermaid=mermaid_graph,
            details=details,
        )

    def _extract_wallet_addresses(self, text: str) -> List[WalletAddress]:
        found_wallets: List[WalletAddress] = []

        # Ethereum address pattern
        eth_pattern = r'\b0x[a-fA-F0-9]{40}\b'
        for match in re.finditer(eth_pattern, text):
            address = match.group(0)
            is_valid = self.w3.is_address(address) if self.w3 else False
            found_wallets.append(WalletAddress(address=address, blockchain="Ethereum", currency="ETH", is_valid=is_valid))

        # Bitcoin address patterns (P2PKH, P2SH, Bech32)
        # Simplified regex for common Bitcoin addresses, more robust validation with bitcoinlib
        btc_pattern = r'\b([13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[ac-hj-np-z02-9]{11,71})\b'
        for match in re.finditer(btc_pattern, text):
            address = match.group(0)
            is_valid = False
            if BitcoinAddress:
                try:
                    # Attempt to parse and validate with bitcoinlib
                    btc_address = BitcoinAddress.parse(address)
                    is_valid = btc_address.is_valid()
                except Exception:
                    pass # Not a valid bitcoinlib address
            found_wallets.append(WalletAddress(address=address, blockchain="Bitcoin", currency="BTC", is_valid=is_valid))

        return found_wallets

    def _perform_on_chain_analysis(self, wallets: List[WalletAddress]) -> List[Transaction]:
        traced_transactions: List[Transaction] = []
        for wallet in wallets:
            if not wallet.is_valid:
                continue # Skip invalid addresses

            if wallet.blockchain == "Ethereum" and self.w3:
                # Use Etherscan API for transaction history (more efficient than iterating blocks)
                # Requires Etherscan API key, which can be obtained from Etherscan website
                if self.ethereum_api_key:
                    etherscan_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet.address}&startblock=0&endblock=99999999&sort=asc&apikey={self.ethereum_api_key}"
                    try:
                        response = requests.get(etherscan_url)
                        response.raise_for_status()
                        data = response.json()
                        if data["status"] == "1" and data["result"]:
                            for tx_data in data["result"]:
                                traced_transactions.append(Transaction(
                                    tx_id=tx_data["hash"],
                                    sender=tx_data["from"],
                                    receiver=tx_data["to"],
                                    amount=float(self.w3.from_wei(int(tx_data["value"]), 'ether')),
                                    currency="ETH",
                                    timestamp=datetime.fromtimestamp(int(tx_data["timeStamp"])).isoformat(),
                                    blockchain="Ethereum",
                                ))
                    except requests.exceptions.RequestException as e:
                        print(f"Error fetching Ethereum transactions from Etherscan for {wallet.address}: {e}")
                else:
                    print(f"Warning: Etherscan API key not configured for Ethereum. Skipping on-chain analysis for {wallet.address}.")

            elif wallet.blockchain == "Bitcoin" and bitcoinlib:
                # Use Blockchair API for Bitcoin transactions
                # Blockchair API is generally public for basic queries, but rate limits apply
                blockchair_url = f"https://api.blockchair.com/bitcoin/dashboards/address/{wallet.address}"
                try:
                    response = requests.get(blockchair_url)
                    response.raise_for_status()
                    data = response.json()
                    if data["data"] and wallet.address in data["data"]:
                        address_data = data["data"][wallet.address]
                        if "transactions" in address_data:
                            for tx_id in address_data["transactions"]:
                                # Fetch individual transaction details if needed, or use summary
                                # For simplicity, we'll just add a placeholder transaction for now
                                # A full implementation would fetch details for each tx_id
                                traced_transactions.append(Transaction(
                                    tx_id=tx_id,
                                    sender="unknown", # Requires fetching full tx details
                                    receiver="unknown", # Requires fetching full tx details
                                    amount=0.0, # Requires fetching full tx details
                                    currency="BTC",
                                    timestamp=datetime.now().isoformat(), # Placeholder
                                    blockchain="Bitcoin",
                                ))
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching Bitcoin transactions from Blockchair for {wallet.address}: {e}")
            else:
                print(f"Warning: Skipping on-chain analysis for {wallet.address} due to missing library or invalid blockchain.")

        return traced_transactions

    def _store_crypto_data_in_neo4j(self, document_id: str, wallets: List[WalletAddress], transactions: List[Transaction]):
        with self.neo4j_driver.session() as session:
            # Create Document node if it doesn't exist
            session.run("""
                MERGE (d:Document {documentId: $document_id})
                RETURN d
            """, document_id=document_id)

            for wallet in wallets:
                # Create Wallet node
                session.run("""
                    MERGE (w:Wallet {address: $address})
                    ON CREATE SET w.blockchain = $blockchain, w.currency = $currency, w.isValid = $is_valid
                    ON MATCH SET w.blockchain = $blockchain, w.currency = $currency, w.isValid = $is_valid
                    RETURN w
                """, address=wallet.address, blockchain=wallet.blockchain, currency=wallet.currency, is_valid=wallet.is_valid)
                
                # Link Wallet to Document
                session.run("""
                    MATCH (d:Document {documentId: $document_id})
                    MATCH (w:Wallet {address: $address})
                    MERGE (d)-[:MENTIONS_WALLET]->(w)
                """, document_id=document_id, address=wallet.address)

            for tx in transactions:
                # Create Transaction node
                session.run("""
                    MERGE (t:Transaction {txId: $tx_id})
                    ON CREATE SET t.amount = $amount, t.currency = $currency, t.timestamp = $timestamp, t.blockchain = $blockchain
                    ON MATCH SET t.amount = $amount, t.currency = $currency, t.timestamp = $timestamp, t.blockchain = $blockchain
                    RETURN t
                """, tx_id=tx.tx_id, amount=tx.amount, currency=tx.currency, timestamp=tx.timestamp, blockchain=tx.blockchain)

                # Link Sender Wallet to Transaction
                session.run("""
                    MATCH (w:Wallet {address: $sender_address})
                    MATCH (t:Transaction {txId: $tx_id})
                    MERGE (w)-[:SENT]->(t)
                """, sender_address=tx.sender, tx_id=tx.tx_id)

                # Link Transaction to Receiver Wallet
                session.run("""
                    MATCH (t:Transaction {txId: $tx_id})
                    MATCH (w:Wallet {address: $receiver_address})
                    MERGE (t)-[:RECEIVED]->(w)
                """, tx_id=tx.tx_id, receiver_address=tx.receiver)

    def _generate_graph_data(self, document_id: str) -> Optional[str]:
        """
        Generates a Mermaid graph definition string from Neo4j data related to a document.
        """
        query = """
            MATCH (d:Document {documentId: $document_id})-[:MENTIONS_WALLET]->(w:Wallet)
            OPTIONAL MATCH (w)-[s:SENT]->(t:Transaction)
            OPTIONAL MATCH (t)-[r:RECEIVED]->(w2:Wallet)
            RETURN d, w, s, t, r, w2
        """
        with self.neo4j_driver.session() as session:
            result = session.run(query, document_id=document_id)
            
            nodes = {}
            edges = set()

            for record in result:
                doc_node = record["d"]
                wallet_node = record["w"]
                tx_node = record["t"]
                wallet2_node = record["w2"]

                # Add Document node
                nodes[doc_node["documentId"]] = f'Document_{doc_node["documentId"]}[Document: {doc_node["documentId"]}]'

                # Add Wallet nodes
                nodes[wallet_node["address"]] = f'Wallet_{wallet_node["address"]}[Wallet: {wallet_node["address"]}\n({wallet_node["blockchain"]})]' 
                edges.add(f'Document_{doc_node["documentId"]} --> Wallet_{wallet_node["address"]}')

                if tx_node:
                    # Add Transaction node
                    nodes[tx_node["txId"]] = f'Transaction_{tx_node["txId"]}[Transaction: {tx_node["txId"]}\n({tx_node["amount"]} {tx_node["currency"]})]' 
                    
                    # Add edges for SENT and RECEIVED
                    if record["s"]:
                        sender_address = record["s"].start_node["address"]
                        edges.add(f'Wallet_{sender_address} --> Transaction_{tx_node["txId"]}')
                    
                    if record["r"]:
                        receiver_address = record["r"].end_node["address"]
                        edges.add(f'Transaction_{tx_node["txId"]} --> Wallet_{receiver_address}')
            
            if not nodes:
                return None

            mermaid_definition = "graph TD\n"
            for node_id, node_def in nodes.items():
                mermaid_definition += f"  {node_def}\n"
            for edge in edges:
                mermaid_definition += f"  {edge}\n"
            
            return mermaid_definition

def get_crypto_tracer() -> CryptoTracer:
    """
    Dependency function to provide a CryptoTracer instance.
    """
    return CryptoTracer()