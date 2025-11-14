# Zcash Donation Tracker

A CLI tool and web service for tracking donations to Zcash z-addresses via viewing keys. This tool enables organizations and projects to provide transparent donation reporting while preserving donor privacy.

## Features

- **Private Donations**: Donors remain completely anonymous through Zcash's shielded addresses
- **Transparent Reporting**: Organizations can publicly display total donations and transaction counts
- **CLI Interface**: Easy-to-use command-line tools for initialization, scanning, and reporting
- **Web API**: RESTful API built with FastAPI for programmatic access
- **Web UI**: Simple, beautiful web interface for displaying donation statistics
- **Viewing Key Support**: Read-only access to incoming transactions without spending capability

## Technology Stack

- **Language**: Python 3.10+
- **API Framework**: FastAPI
- **CLI Framework**: Click with Rich for beautiful terminal output
- **Zcash Integration**: JSON-RPC communication with zcashd
- **Storage**: In-memory caching with optional persistence

## Installation

### Prerequisites

1. **Python 3.10 or higher**
   ```bash
   python --version
   ```

2. **Zcash node (zcashd) running and synced**
   - For installation instructions, see the [official Zcash documentation](https://zcash.readthedocs.io/en/latest/rtd_pages/install_binary_tarball.html)
   - Ensure your node is fully synced before using this tool

### Install from source

1. Clone the repository:
   ```bash
   git clone https://github.com/pavlenkotm/zcash-donation-tracker.git
   cd zcash-donation-tracker
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

## Quick Start

### 1. Configure zcashd

Ensure your `zcash.conf` file has RPC enabled:

```conf
# Enable RPC
server=1
rpcuser=your_username
rpcpassword=your_secure_password

# Testnet (remove for mainnet)
testnet=1
```

For more details, see the [Zcash RPC documentation](https://zcash.readthedocs.io/en/latest/rtd_pages/payment_api.html).

### 2. Create a z-address and viewing key

Connect to your Zcash node and create a new shielded address:

```bash
zcash-cli z_getnewaddress
# Returns: ztestsapling1234567890abcdef...
```

Export the viewing key for this address:

```bash
zcash-cli z_exportviewingkey ztestsapling1234567890abcdef...
# Returns: zviewtestsapling0987654321fedcba...
```

**Important**:
- Share the **z-address** with donors
- Keep the **viewing key** private (it allows read-only access)
- Never share your **spending key**

### 3. Initialize the tracker

Run the initialization command and follow the prompts:

```bash
zdt init
```

You'll be asked to provide:
- Zcash RPC URL (e.g., `http://localhost:18232` for testnet)
- RPC username and password
- Viewing key
- Network (testnet or mainnet)

Configuration is saved to `~/.zdt/config.toml`.

### 4. Scan for donations

Scan the blockchain for incoming donations:

```bash
zdt scan
```

This will:
- Import the viewing key into zcashd (if not already imported)
- Scan for all incoming transactions
- Display the total donation amount and transaction count

### 5. View detailed report

Display a detailed report with recent transactions:

```bash
zdt report
```

You can limit the number of transactions shown:

```bash
zdt report --limit 20
```

## Web Interface

### Start the web server

```bash
uvicorn zdt.webapp:app --reload
```

Or with custom host and port:

```bash
uvicorn zdt.webapp:app --host 0.0.0.0 --port 8000
```

### Available endpoints

- **`GET /`** - API information
- **`GET /ui`** - Web interface for viewing donation statistics
- **`GET /health`** - Health check endpoint
- **`GET /summary`** - Get donation summary (total, count, last updated)
- **`GET /last-transactions?limit=N`** - Get last N transactions
- **`GET /docs`** - Interactive API documentation (Swagger UI)

### Example API usage

Get donation summary:
```bash
curl http://localhost:8000/summary
```

Response:
```json
{
  "total_donations": 15.75000000,
  "tx_count": 8,
  "last_updated": "2024-01-15T10:30:00"
}
```

Get last 5 transactions:
```bash
curl http://localhost:8000/last-transactions?limit=5
```

Response:
```json
{
  "count": 5,
  "transactions": [
    {
      "date": "2024-01-15T09:20:00",
      "amount": 2.5,
      "confirmations": 10,
      "txid_short": "abc12345...xyz98765",
      "memo": "For the project"
    }
  ]
}
```

## CLI Commands Reference

### `zdt init`
Initialize configuration with interactive prompts.

### `zdt scan`
Scan for donations and display summary.

### `zdt report [--limit N]`
Display detailed donation report with recent transactions.
- `--limit, -n`: Number of recent transactions to display (default: 10)

### `zdt config`
Display current configuration.

## Configuration

### Configuration file location

Configuration is stored in `~/.zdt/config.toml`:

```toml
[zcash]
rpc_url = "http://localhost:18232"
rpc_user = "your_username"
rpc_password = "your_password"
viewing_key = "zviewtestsapling..."
network = "testnet"
```

### Environment variables

You can also configure using environment variables (see `.env.example`):

```bash
export ZCASH_RPC_URL="http://localhost:18232"
export ZCASH_RPC_USER="your_username"
export ZCASH_RPC_PASSWORD="your_password"
export ZCASH_VIEWING_KEY="zviewtestsapling..."
export ZCASH_NETWORK="testnet"
```

## Development

### Install development dependencies

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=zdt --cov-report=html
```

### Code structure

```
zcash-donation-tracker/
├── zdt/                    # Main package
│   ├── __init__.py        # Package initialization
│   ├── cli.py             # CLI commands
│   ├── config.py          # Configuration management
│   ├── models.py          # Data models
│   ├── rpc_client.py      # Zcash RPC client
│   └── webapp.py          # FastAPI web application
├── tests/                  # Test suite
│   ├── test_cli.py        # CLI tests
│   └── test_rpc_client.py # RPC client tests
├── requirements.txt        # Dependencies
├── pyproject.toml         # Package configuration
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Security Considerations

### Viewing Keys
- **Viewing keys provide READ-ONLY access** to incoming transactions
- They **cannot be used to spend funds**
- Keep viewing keys private - they reveal transaction amounts and memos
- Never share your spending keys or private keys

### RPC Security
- Use strong RPC credentials
- Consider running zcashd on localhost only
- Use firewall rules to restrict RPC access
- Enable SSL/TLS for production deployments

### API Security
For production deployments:
- Enable HTTPS/TLS
- Add authentication to sensitive endpoints
- Use rate limiting
- Run behind a reverse proxy (nginx, caddy)
- Consider implementing API keys

## Use Cases

- **Nonprofit Organizations**: Accept private donations while providing public transparency
- **Open Source Projects**: Track project funding without exposing donors
- **Fundraising Campaigns**: Display real-time donation progress
- **Grant Programs**: Monitor incoming contributions
- **Research Projects**: Study Zcash transaction patterns (with consent)

## Troubleshooting

### Connection errors

If you get "Failed to connect to Zcash RPC":
1. Verify zcashd is running: `zcash-cli getinfo`
2. Check RPC credentials in zcash.conf
3. Verify the RPC URL and port (18232 for testnet, 8232 for mainnet)
4. Check firewall settings

### Empty results

If you get zero transactions:
1. Ensure the viewing key is correct
2. Verify you're using the right network (testnet/mainnet)
3. Wait for blockchain sync to complete
4. Send a test donation to the z-address

### Invalid viewing key

If you get "invalid viewing key" errors:
1. Verify the viewing key format
2. Ensure it matches the network (testnet vs mainnet)
3. Re-export the viewing key from zcashd

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Resources

- [Zcash Documentation](https://zcash.readthedocs.io/)
- [Zcash RPC API](https://zcash.readthedocs.io/en/latest/rtd_pages/payment_api.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Zcash Community](https://z.cash/community/)

## Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/pavlenkotm/zcash-donation-tracker/issues)
- Join the Zcash community forum
- Check the official Zcash documentation

## Disclaimer

This software is provided as-is for educational and practical purposes. Always ensure you understand the privacy implications of using viewing keys and follow best security practices when handling cryptocurrency.
