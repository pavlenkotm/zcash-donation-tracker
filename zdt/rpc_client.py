"""Zcash RPC client for interacting with zcashd."""

import requests
from typing import Any, Optional
from requests.auth import HTTPBasicAuth

from .config import ZcashConfig
from .models import Transaction, DonationSummary
from datetime import datetime


class ZcashRPCError(Exception):
    """Exception raised for Zcash RPC errors."""

    pass


class ZcashRPCClient:
    """Client for interacting with Zcash daemon via JSON-RPC."""

    def __init__(self, config: ZcashConfig):
        """Initialize RPC client with configuration."""
        self.config = config
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(config.rpc_user, config.rpc_password)
        self.session.headers.update({"content-type": "application/json"})

    def _call(self, method: str, params: Optional[list] = None) -> Any:
        """
        Make a JSON-RPC call to zcashd.

        Args:
            method: RPC method name
            params: List of parameters

        Returns:
            Result from RPC call

        Raises:
            ZcashRPCError: If RPC call fails
        """
        payload = {
            "jsonrpc": "2.0",
            "id": "zdt",
            "method": method,
            "params": params or []
        }

        try:
            response = self.session.post(
                self.config.rpc_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise ZcashRPCError(f"Failed to connect to Zcash RPC at {self.config.rpc_url}: {e}")
        except requests.exceptions.Timeout:
            raise ZcashRPCError(f"Zcash RPC request timed out")
        except requests.exceptions.RequestException as e:
            raise ZcashRPCError(f"Zcash RPC request failed: {e}")

        data = response.json()

        if "error" in data and data["error"]:
            error = data["error"]
            raise ZcashRPCError(f"RPC error: {error.get('message', str(error))}")

        return data.get("result")

    def test_connection(self) -> bool:
        """
        Test connection to zcashd.

        Returns:
            True if connection is successful
        """
        try:
            self._call("getinfo")
            return True
        except ZcashRPCError:
            return False

    def get_blockchain_info(self) -> dict:
        """Get blockchain information."""
        return self._call("getblockchaininfo")

    def import_viewing_key(self, viewing_key: str, rescan: str = "no") -> None:
        """
        Import a viewing key to track transactions.

        Args:
            viewing_key: The viewing key to import
            rescan: Rescan mode ("yes", "no", or "whenkeyisnew")
        """
        try:
            self._call("z_importviewingkey", [viewing_key, rescan])
        except ZcashRPCError as e:
            if "already have" in str(e).lower():
                # Key already imported, continue
                pass
            else:
                raise

    def list_received_by_address(self, address: Optional[str] = None, min_conf: int = 1) -> list[dict]:
        """
        List amounts received by z-address.

        Args:
            address: Specific z-address to query (optional)
            min_conf: Minimum confirmations

        Returns:
            List of received transaction data
        """
        params = [min_conf]
        if address:
            params.append(False)  # includeWatchonly
            params.append(address)

        return self._call("z_listreceivedbyaddress", params)

    def get_transaction(self, txid: str) -> dict:
        """Get transaction details by transaction ID."""
        return self._call("gettransaction", [txid])

    def get_address_from_viewing_key(self) -> Optional[str]:
        """
        Get z-address associated with the viewing key.

        Returns:
            Z-address or None if not found
        """
        try:
            addresses = self._call("z_listaddresses")
            if addresses:
                return addresses[0]
            return None
        except ZcashRPCError:
            return None

    def scan_donations(self) -> DonationSummary:
        """
        Scan for all donations received via the viewing key.

        Returns:
            DonationSummary with all donation data

        Raises:
            ZcashRPCError: If scanning fails
        """
        # First, ensure the viewing key is imported
        try:
            self.import_viewing_key(self.config.viewing_key, rescan="whenkeyisnew")
        except ZcashRPCError as e:
            raise ZcashRPCError(f"Failed to import viewing key: {e}")

        # Get the z-address associated with the viewing key
        z_address = self.get_address_from_viewing_key()
        if not z_address:
            raise ZcashRPCError("No z-address found for viewing key")

        # List all received transactions
        try:
            received = self._call("z_listreceivedbyaddress", [z_address, 0])
        except ZcashRPCError as e:
            if "invalid parameter" in str(e).lower():
                # Try alternative method
                received = self.list_received_by_address(z_address, 0)
            else:
                raise

        if not received:
            return DonationSummary(
                total_donations=0.0,
                tx_count=0,
                last_updated=datetime.now(),
                transactions=[]
            )

        # Parse transactions
        transactions = []
        total = 0.0

        for item in received:
            amount = item.get("amount", 0.0)
            txid = item.get("txid", "")
            confirmations = item.get("confirmations", 0)
            block_time = item.get("blocktime")
            memo = item.get("memo")

            # Decode memo if present
            if memo:
                try:
                    # Memo is typically hex-encoded
                    memo_bytes = bytes.fromhex(memo)
                    memo = memo_bytes.decode("utf-8", errors="ignore").strip("\x00")
                except Exception:
                    pass

            if amount > 0:
                total += amount
                tx = Transaction(
                    txid=txid,
                    amount=amount,
                    confirmations=confirmations,
                    block_time=block_time,
                    memo=memo
                )
                transactions.append(tx)

        return DonationSummary(
            total_donations=total,
            tx_count=len(transactions),
            last_updated=datetime.now(),
            transactions=transactions
        )
