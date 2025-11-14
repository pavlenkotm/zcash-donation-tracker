"""Data models for Zcash Donation Tracker."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Transaction:
    """Represents a donation transaction."""

    txid: str
    amount: float
    confirmations: int
    block_time: Optional[int] = None
    memo: Optional[str] = None

    @property
    def timestamp(self) -> Optional[datetime]:
        """Convert block time to datetime."""
        if self.block_time:
            return datetime.fromtimestamp(self.block_time)
        return None

    def to_dict(self) -> dict:
        """Convert transaction to dictionary."""
        return {
            "txid": self.txid,
            "amount": self.amount,
            "confirmations": self.confirmations,
            "block_time": self.block_time,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "memo": self.memo
        }


@dataclass
class DonationSummary:
    """Summary of all donations."""

    total_donations: float
    tx_count: int
    last_updated: datetime
    transactions: list[Transaction]

    def to_dict(self) -> dict:
        """Convert summary to dictionary."""
        return {
            "total_donations": self.total_donations,
            "tx_count": self.tx_count,
            "last_updated": self.last_updated.isoformat(),
            "transactions": [tx.to_dict() for tx in self.transactions]
        }

    def get_last_transactions(self, limit: int = 10) -> list[Transaction]:
        """Get the last N transactions sorted by block time."""
        sorted_txs = sorted(
            [tx for tx in self.transactions if tx.block_time],
            key=lambda x: x.block_time,
            reverse=True
        )
        return sorted_txs[:limit]
