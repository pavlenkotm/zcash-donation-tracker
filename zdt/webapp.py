"""FastAPI web application for Zcash Donation Tracker."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional
import logging

from .config import load_config
from .rpc_client import ZcashRPCClient, ZcashRPCError
from .models import DonationSummary

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Zcash Donation Tracker",
    description="Track donations to Zcash z-addresses via viewing keys",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache for donation summary
_cached_summary: Optional[DonationSummary] = None
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_SECONDS = 60  # Cache for 1 minute


def get_rpc_client() -> ZcashRPCClient:
    """Get configured RPC client."""
    try:
        config = load_config()
        return ZcashRPCClient(config)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Configuration not found. Please run 'zdt init' first."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load configuration: {str(e)}"
        )


def get_cached_summary(force_refresh: bool = False) -> DonationSummary:
    """Get donation summary with caching."""
    global _cached_summary, _cache_timestamp

    now = datetime.now()

    # Check if cache is valid
    if not force_refresh and _cached_summary and _cache_timestamp:
        cache_age = (now - _cache_timestamp).total_seconds()
        if cache_age < CACHE_TTL_SECONDS:
            logger.info(f"Returning cached summary (age: {cache_age:.1f}s)")
            return _cached_summary

    # Refresh cache
    logger.info("Refreshing donation summary...")
    try:
        client = get_rpc_client()
        summary = client.scan_donations()
        _cached_summary = summary
        _cache_timestamp = now
        return summary
    except ZcashRPCError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to Zcash RPC: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error scanning donations: {str(e)}"
        )


@app.get("/")
async def root():
    """Redirect to web UI."""
    return {"message": "Zcash Donation Tracker API", "docs": "/docs", "ui": "/ui"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        client = get_rpc_client()
        is_connected = client.test_connection()
        return {
            "status": "healthy" if is_connected else "degraded",
            "zcashd_connected": is_connected,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/summary")
async def get_summary(refresh: bool = Query(False, description="Force refresh cache")):
    """
    Get donation summary.

    Returns:
        - total_donations: Total amount donated in ZEC
        - tx_count: Number of donation transactions
        - last_updated: Timestamp of last update
    """
    summary = get_cached_summary(force_refresh=refresh)

    return {
        "total_donations": summary.total_donations,
        "tx_count": summary.tx_count,
        "last_updated": summary.last_updated.isoformat()
    }


@app.get("/last-transactions")
async def get_last_transactions(
    limit: int = Query(10, ge=1, le=100, description="Number of transactions to return"),
    refresh: bool = Query(False, description="Force refresh cache")
):
    """
    Get last N transactions without revealing sender information.

    Args:
        limit: Number of transactions to return (1-100)
        refresh: Force refresh cache

    Returns:
        List of recent transactions with date and amount
    """
    summary = get_cached_summary(force_refresh=refresh)
    recent_txs = summary.get_last_transactions(limit)

    return {
        "count": len(recent_txs),
        "transactions": [
            {
                "date": tx.timestamp.isoformat() if tx.timestamp else None,
                "amount": tx.amount,
                "confirmations": tx.confirmations,
                "txid_short": f"{tx.txid[:8]}...{tx.txid[-8:]}" if len(tx.txid) > 16 else tx.txid,
                "memo": tx.memo if tx.memo else None
            }
            for tx in recent_txs
        ]
    }


@app.get("/ui", response_class=HTMLResponse)
async def web_ui():
    """Simple web UI for displaying donation statistics."""
    try:
        summary = get_cached_summary()
        recent_txs = summary.get_last_transactions(10)

        # Build transaction rows
        tx_rows = ""
        for tx in recent_txs:
            date_str = tx.timestamp.strftime("%Y-%m-%d %H:%M") if tx.timestamp else "N/A"
            tx_rows += f"""
            <tr>
                <td>{date_str}</td>
                <td style="text-align: right;">{tx.amount:.8f} ZEC</td>
                <td style="text-align: center;">{tx.confirmations}</td>
            </tr>
            """

        if not tx_rows:
            tx_rows = '<tr><td colspan="3" style="text-align: center;">No transactions yet</td></tr>'

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Zcash Donation Tracker</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}

                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                }}

                .header {{
                    text-align: center;
                    color: white;
                    margin-bottom: 30px;
                }}

                .header h1 {{
                    font-size: 2.5rem;
                    margin-bottom: 10px;
                }}

                .header p {{
                    font-size: 1.1rem;
                    opacity: 0.9;
                }}

                .card {{
                    background: white;
                    border-radius: 12px;
                    padding: 30px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
                    margin-bottom: 20px;
                }}

                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}

                .stat-box {{
                    text-align: center;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 8px;
                    color: white;
                }}

                .stat-box .value {{
                    font-size: 2rem;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}

                .stat-box .label {{
                    font-size: 0.9rem;
                    opacity: 0.9;
                }}

                .transactions {{
                    margin-top: 30px;
                }}

                .transactions h2 {{
                    margin-bottom: 20px;
                    color: #333;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}

                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #eee;
                }}

                th {{
                    background-color: #f8f9fa;
                    color: #333;
                    font-weight: 600;
                }}

                tr:hover {{
                    background-color: #f8f9fa;
                }}

                .footer {{
                    text-align: center;
                    color: white;
                    margin-top: 30px;
                    opacity: 0.8;
                    font-size: 0.9rem;
                }}

                .refresh-btn {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 1rem;
                    margin-bottom: 20px;
                    text-decoration: none;
                }}

                .refresh-btn:hover {{
                    opacity: 0.9;
                }}

                .last-updated {{
                    color: #666;
                    font-size: 0.9rem;
                    text-align: center;
                    margin-top: 15px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Zcash Donation Tracker</h1>
                    <p>Private Donations, Transparent Reporting</p>
                </div>

                <div class="card">
                    <div style="text-align: center;">
                        <a href="/ui?refresh=true" class="refresh-btn">Refresh Data</a>
                    </div>

                    <div class="stats">
                        <div class="stat-box">
                            <div class="value">{summary.total_donations:.8f}</div>
                            <div class="label">Total Donated (ZEC)</div>
                        </div>
                        <div class="stat-box">
                            <div class="value">{summary.tx_count}</div>
                            <div class="label">Total Transactions</div>
                        </div>
                    </div>

                    <div class="transactions">
                        <h2>Recent Donations</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th style="text-align: right;">Amount</th>
                                    <th style="text-align: center;">Confirmations</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tx_rows}
                            </tbody>
                        </table>
                    </div>

                    <div class="last-updated">
                        Last updated: {summary.last_updated.strftime("%Y-%m-%d %H:%M:%S")}
                    </div>
                </div>

                <div class="footer">
                    <p>Powered by Zcash Donation Tracker | <a href="/docs" style="color: white;">API Documentation</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - Zcash Donation Tracker</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f5f5f5;
                }}
                .error {{
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                h1 {{ color: #d32f2f; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>Error</h1>
                <p>{str(e)}</p>
                <p><a href="/">Return to home</a></p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
