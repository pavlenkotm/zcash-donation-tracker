"""Tests for Zcash RPC client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from zdt.rpc_client import ZcashRPCClient, ZcashRPCError
from zdt.config import ZcashConfig


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
def rpc_client(mock_config):
    """Create RPC client with mock configuration."""
    return ZcashRPCClient(mock_config)


def test_client_initialization(rpc_client, mock_config):
    """Test RPC client initialization."""
    assert rpc_client.config == mock_config
    assert rpc_client.session.auth.username == "testuser"
    assert rpc_client.session.auth.password == "testpass"


@patch("requests.Session.post")
def test_call_success(mock_post, rpc_client):
    """Test successful RPC call."""
    mock_response = Mock()
    mock_response.json.return_value = {"result": {"test": "data"}, "error": None}
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = rpc_client._call("getinfo")

    assert result == {"test": "data"}
    mock_post.assert_called_once()


@patch("requests.Session.post")
def test_call_connection_error(mock_post, rpc_client):
    """Test RPC call with connection error."""
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

    with pytest.raises(ZcashRPCError) as exc_info:
        rpc_client._call("getinfo")

    assert "Failed to connect" in str(exc_info.value)


@patch("requests.Session.post")
def test_call_timeout_error(mock_post, rpc_client):
    """Test RPC call with timeout error."""
    mock_post.side_effect = requests.exceptions.Timeout()

    with pytest.raises(ZcashRPCError) as exc_info:
        rpc_client._call("getinfo")

    assert "timed out" in str(exc_info.value)


@patch("requests.Session.post")
def test_call_rpc_error(mock_post, rpc_client):
    """Test RPC call with RPC error response."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "result": None,
        "error": {"code": -5, "message": "Invalid address"}
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    with pytest.raises(ZcashRPCError) as exc_info:
        rpc_client._call("z_getbalance", ["invalid"])

    assert "Invalid address" in str(exc_info.value)


@patch("requests.Session.post")
def test_test_connection(mock_post, rpc_client):
    """Test connection test method."""
    mock_response = Mock()
    mock_response.json.return_value = {"result": {"version": 1000000}, "error": None}
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = rpc_client.test_connection()

    assert result is True


@patch("requests.Session.post")
def test_test_connection_failure(mock_post, rpc_client):
    """Test connection test failure."""
    mock_post.side_effect = requests.exceptions.ConnectionError()

    result = rpc_client.test_connection()

    assert result is False


@patch("requests.Session.post")
def test_import_viewing_key(mock_post, rpc_client):
    """Test importing viewing key."""
    mock_response = Mock()
    mock_response.json.return_value = {"result": None, "error": None}
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    rpc_client.import_viewing_key("zviewtest123", "no")

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    assert payload["method"] == "z_importviewingkey"
    assert payload["params"] == ["zviewtest123", "no"]


@patch("requests.Session.post")
def test_scan_donations(mock_post, rpc_client):
    """Test scanning for donations."""
    # Mock responses for different RPC calls
    def mock_response_factory(*args, **kwargs):
        payload = kwargs.get("json", {})
        method = payload.get("method")

        response = Mock()
        response.raise_for_status = Mock()

        if method == "z_importviewingkey":
            response.json.return_value = {"result": None, "error": None}
        elif method == "z_listaddresses":
            response.json.return_value = {"result": ["ztestsapling123"], "error": None}
        elif method == "z_listreceivedbyaddress":
            response.json.return_value = {
                "result": [
                    {
                        "txid": "abc123",
                        "amount": 1.5,
                        "confirmations": 10,
                        "blocktime": 1234567890,
                        "memo": None
                    },
                    {
                        "txid": "def456",
                        "amount": 2.5,
                        "confirmations": 5,
                        "blocktime": 1234567900,
                        "memo": None
                    }
                ],
                "error": None
            }
        else:
            response.json.return_value = {"result": {}, "error": None}

        return response

    mock_post.side_effect = mock_response_factory

    summary = rpc_client.scan_donations()

    assert summary.total_donations == 4.0
    assert summary.tx_count == 2
    assert len(summary.transactions) == 2


@patch("requests.Session.post")
def test_scan_donations_no_transactions(mock_post, rpc_client):
    """Test scanning with no transactions."""
    def mock_response_factory(*args, **kwargs):
        payload = kwargs.get("json", {})
        method = payload.get("method")

        response = Mock()
        response.raise_for_status = Mock()

        if method == "z_importviewingkey":
            response.json.return_value = {"result": None, "error": None}
        elif method == "z_listaddresses":
            response.json.return_value = {"result": ["ztestsapling123"], "error": None}
        elif method == "z_listreceivedbyaddress":
            response.json.return_value = {"result": [], "error": None}
        else:
            response.json.return_value = {"result": {}, "error": None}

        return response

    mock_post.side_effect = mock_response_factory

    summary = rpc_client.scan_donations()

    assert summary.total_donations == 0.0
    assert summary.tx_count == 0
    assert len(summary.transactions) == 0


@patch("requests.Session.post")
def test_get_blockchain_info(mock_post, rpc_client):
    """Test getting blockchain info."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "result": {
            "chain": "test",
            "blocks": 100000,
            "headers": 100000
        },
        "error": None
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    info = rpc_client.get_blockchain_info()

    assert info["chain"] == "test"
    assert info["blocks"] == 100000
