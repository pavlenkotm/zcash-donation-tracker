"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from zdt.cli import cli
from zdt.config import ZcashConfig
from zdt.models import DonationSummary, Transaction
from datetime import datetime


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return ZcashConfig(
        rpc_url="http://localhost:18232",
        rpc_user="testuser",
        rpc_password="testpass",
        viewing_key="zviewtestsapling1234567890",
        network="testnet"
    )


@pytest.fixture
def mock_summary():
    """Create mock donation summary."""
    tx1 = Transaction(
        txid="abc123",
        amount=1.5,
        confirmations=10,
        block_time=1234567890,
        memo="Test donation"
    )
    tx2 = Transaction(
        txid="def456",
        amount=2.5,
        confirmations=5,
        block_time=1234567900
    )
    return DonationSummary(
        total_donations=4.0,
        tx_count=2,
        last_updated=datetime.now(),
        transactions=[tx1, tx2]
    )


def test_cli_version(runner):
    """Test CLI version command."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


@patch("zdt.cli.load_config")
@patch("zdt.cli.ZcashRPCClient")
def test_scan_command(mock_rpc_client, mock_load_config, runner, mock_config, mock_summary):
    """Test scan command."""
    mock_load_config.return_value = mock_config

    mock_client = Mock()
    mock_client.scan_donations.return_value = mock_summary
    mock_rpc_client.return_value = mock_client

    result = runner.invoke(cli, ["scan"])

    assert result.exit_code == 0
    assert "4.00000000 ZEC" in result.output
    assert "Number of transactions: 2" in result.output


@patch("zdt.cli.load_config")
@patch("zdt.cli.ZcashRPCClient")
def test_report_command(mock_rpc_client, mock_load_config, runner, mock_config, mock_summary):
    """Test report command."""
    mock_load_config.return_value = mock_config

    mock_client = Mock()
    mock_client.scan_donations.return_value = mock_summary
    mock_rpc_client.return_value = mock_client

    result = runner.invoke(cli, ["report"])

    assert result.exit_code == 0
    assert "4.00000000 ZEC" in result.output
    assert "Total Transactions: 2" in result.output


@patch("zdt.cli.load_config")
def test_scan_no_config(mock_load_config, runner):
    """Test scan command without configuration."""
    mock_load_config.side_effect = FileNotFoundError()

    result = runner.invoke(cli, ["scan"])

    assert result.exit_code == 1
    assert "Configuration not found" in result.output


@patch("zdt.cli.load_config")
@patch("zdt.cli.ZcashRPCClient")
def test_scan_rpc_error(mock_rpc_client, mock_load_config, runner, mock_config):
    """Test scan command with RPC error."""
    mock_load_config.return_value = mock_config

    mock_client = Mock()
    mock_client.scan_donations.side_effect = Exception("Connection failed")
    mock_rpc_client.return_value = mock_client

    result = runner.invoke(cli, ["scan"])

    assert result.exit_code == 1
    assert "Error" in result.output


@patch("zdt.cli.load_config")
def test_config_command(mock_load_config, runner, mock_config):
    """Test config command."""
    mock_load_config.return_value = mock_config

    result = runner.invoke(cli, ["config"])

    assert result.exit_code == 0
    assert "http://localhost:18232" in result.output
    assert "testuser" in result.output
    assert "testnet" in result.output
