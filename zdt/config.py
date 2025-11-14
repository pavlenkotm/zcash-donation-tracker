"""Configuration management for Zcash Donation Tracker."""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import toml


@dataclass
class ZcashConfig:
    """Zcash configuration parameters."""

    rpc_url: str
    rpc_user: str
    rpc_password: str
    viewing_key: str
    network: str = "testnet"  # testnet or mainnet

    @classmethod
    def from_env(cls) -> "ZcashConfig":
        """Load configuration from environment variables."""
        return cls(
            rpc_url=os.getenv("ZCASH_RPC_URL", "http://localhost:18232"),
            rpc_user=os.getenv("ZCASH_RPC_USER", ""),
            rpc_password=os.getenv("ZCASH_RPC_PASSWORD", ""),
            viewing_key=os.getenv("ZCASH_VIEWING_KEY", ""),
            network=os.getenv("ZCASH_NETWORK", "testnet")
        )

    @classmethod
    def from_toml(cls, config_path: Path) -> "ZcashConfig":
        """Load configuration from TOML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        config_data = toml.load(config_path)
        zcash_config = config_data.get("zcash", {})

        return cls(
            rpc_url=zcash_config.get("rpc_url", "http://localhost:18232"),
            rpc_user=zcash_config.get("rpc_user", ""),
            rpc_password=zcash_config.get("rpc_password", ""),
            viewing_key=zcash_config.get("viewing_key", ""),
            network=zcash_config.get("network", "testnet")
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.rpc_url:
            errors.append("RPC URL is required")

        if not self.rpc_user:
            errors.append("RPC user is required")

        if not self.rpc_password:
            errors.append("RPC password is required")

        if not self.viewing_key:
            errors.append("Viewing key is required")

        if self.network not in ["testnet", "mainnet"]:
            errors.append(f"Invalid network: {self.network}. Must be 'testnet' or 'mainnet'")

        return errors

    def to_toml(self) -> dict:
        """Convert configuration to TOML-compatible dictionary."""
        return {
            "zcash": {
                "rpc_url": self.rpc_url,
                "rpc_user": self.rpc_user,
                "rpc_password": self.rpc_password,
                "viewing_key": self.viewing_key,
                "network": self.network
            }
        }


def get_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".zdt" / "config.toml"


def ensure_config_dir() -> Path:
    """Ensure configuration directory exists and return its path."""
    config_dir = Path.home() / ".zdt"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def load_config() -> ZcashConfig:
    """Load configuration from file or environment."""
    config_path = get_config_path()

    if config_path.exists():
        return ZcashConfig.from_toml(config_path)

    # Fall back to environment variables
    return ZcashConfig.from_env()


def save_config(config: ZcashConfig) -> None:
    """Save configuration to file."""
    ensure_config_dir()
    config_path = get_config_path()

    with open(config_path, "w") as f:
        toml.dump(config.to_toml(), f)
