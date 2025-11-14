"""Command-line interface for Zcash Donation Tracker."""

import sys
import click
import toml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .config import (
    ZcashConfig,
    get_config_path,
    ensure_config_dir,
    load_config,
    save_config
)
from .rpc_client import ZcashRPCClient, ZcashRPCError

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Zcash Donation Tracker - Track donations to Zcash z-addresses via viewing keys."""
    pass


@cli.command()
def init():
    """Initialize configuration for Zcash Donation Tracker."""
    console.print("\n[bold cyan]Zcash Donation Tracker - Initialization[/bold cyan]\n")

    # Display instructions
    instructions = """
[bold]Step 1: Create a Z-Address[/bold]

To create a shielded z-address in zcashd, run:
  $ zcash-cli z_getnewaddress

This will return a z-address (starts with 'zs' on mainnet, 'ztestsapling' on testnet).

[bold]Step 2: Export Viewing Key[/bold]

To export the viewing key for this address, run:
  $ zcash-cli z_exportviewingkey <z-address>

This will return a viewing key (starts with 'zviews' or 'zviewtestsapling').

[bold]Important:[/bold]
- The viewing key allows READ-ONLY access to incoming transactions
- It does NOT allow spending funds
- Share the z-address with donors, keep the viewing key private

For more information, see:
https://zcash.readthedocs.io/en/latest/
    """

    console.print(Panel(instructions, border_style="cyan"))

    # Prompt for configuration
    console.print("\n[bold]Configuration:[/bold]\n")

    rpc_url = click.prompt(
        "Zcash RPC URL",
        default="http://localhost:18232",
        type=str
    )

    rpc_user = click.prompt("RPC Username", type=str)
    rpc_password = click.prompt("RPC Password", type=str, hide_input=True)
    viewing_key = click.prompt("Viewing Key", type=str)

    network = click.prompt(
        "Network",
        default="testnet",
        type=click.Choice(["testnet", "mainnet"], case_sensitive=False)
    )

    # Create configuration
    config = ZcashConfig(
        rpc_url=rpc_url,
        rpc_user=rpc_user,
        rpc_password=rpc_password,
        viewing_key=viewing_key,
        network=network.lower()
    )

    # Validate configuration
    errors = config.validate()
    if errors:
        console.print("\n[bold red]Configuration errors:[/bold red]")
        for error in errors:
            console.print(f"  - {error}")
        sys.exit(1)

    # Test connection
    console.print("\n[yellow]Testing connection to zcashd...[/yellow]")
    try:
        client = ZcashRPCClient(config)
        if client.test_connection():
            console.print("[green]✓ Connection successful![/green]")
        else:
            console.print("[red]✗ Connection failed[/red]")
            sys.exit(1)
    except ZcashRPCError as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        sys.exit(1)

    # Save configuration
    save_config(config)
    config_path = get_config_path()

    console.print(f"\n[green]Configuration saved to: {config_path}[/green]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Run [cyan]zdt scan[/cyan] to scan for donations")
    console.print("  2. Run [cyan]zdt report[/cyan] to view donation summary")
    console.print("  3. Start web server with [cyan]uvicorn zdt.webapp:app --reload[/cyan]\n")


@cli.command()
def scan():
    """Scan for donations using the configured viewing key."""
    try:
        config = load_config()
    except FileNotFoundError:
        console.print("[red]Configuration not found. Please run 'zdt init' first.[/red]")
        sys.exit(1)

    # Validate configuration
    errors = config.validate()
    if errors:
        console.print("[bold red]Configuration errors:[/bold red]")
        for error in errors:
            console.print(f"  - {error}")
        console.print("\n[yellow]Please run 'zdt init' to reconfigure.[/yellow]")
        sys.exit(1)

    console.print("[yellow]Scanning for donations...[/yellow]\n")

    try:
        client = ZcashRPCClient(config)
        summary = client.scan_donations()

        console.print(f"[green]✓ Scan complete![/green]")
        console.print(f"\nTotal donations: [bold cyan]{summary.total_donations:.8f} ZEC[/bold cyan]")
        console.print(f"Number of transactions: [bold]{summary.tx_count}[/bold]")
        console.print(f"Last updated: {summary.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")

    except ZcashRPCError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--limit", "-n", default=10, help="Number of recent transactions to display")
def report(limit):
    """Display donation report with summary and recent transactions."""
    try:
        config = load_config()
    except FileNotFoundError:
        console.print("[red]Configuration not found. Please run 'zdt init' first.[/red]")
        sys.exit(1)

    # Validate configuration
    errors = config.validate()
    if errors:
        console.print("[bold red]Configuration errors:[/bold red]")
        for error in errors:
            console.print(f"  - {error}")
        sys.exit(1)

    console.print("[yellow]Generating donation report...[/yellow]\n")

    try:
        client = ZcashRPCClient(config)
        summary = client.scan_donations()

        # Display summary
        summary_text = f"""
[bold]Total Donations:[/bold] {summary.total_donations:.8f} ZEC
[bold]Total Transactions:[/bold] {summary.tx_count}
[bold]Last Updated:[/bold] {summary.last_updated.strftime('%Y-%m-%d %H:%M:%S')}
        """

        console.print(Panel(summary_text.strip(), title="Donation Summary", border_style="green"))

        # Display recent transactions
        if summary.tx_count > 0:
            console.print(f"\n[bold]Last {min(limit, summary.tx_count)} Transactions:[/bold]\n")

            table = Table(box=box.ROUNDED)
            table.add_column("Date", style="cyan")
            table.add_column("Amount (ZEC)", style="green", justify="right")
            table.add_column("Confirmations", justify="right")
            table.add_column("TX ID (truncated)", style="dim")

            recent_txs = summary.get_last_transactions(limit)

            for tx in recent_txs:
                date_str = tx.timestamp.strftime("%Y-%m-%d %H:%M") if tx.timestamp else "N/A"
                txid_short = f"{tx.txid[:8]}...{tx.txid[-8:]}" if len(tx.txid) > 16 else tx.txid

                table.add_row(
                    date_str,
                    f"{tx.amount:.8f}",
                    str(tx.confirmations),
                    txid_short
                )

            console.print(table)
        else:
            console.print("\n[yellow]No transactions found.[/yellow]")

    except ZcashRPCError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def config():
    """Display current configuration."""
    try:
        cfg = load_config()
        config_path = get_config_path()
    except FileNotFoundError:
        console.print("[red]Configuration not found. Please run 'zdt init' first.[/red]")
        sys.exit(1)

    config_text = f"""
[bold]Configuration Path:[/bold] {config_path}

[bold]RPC URL:[/bold] {cfg.rpc_url}
[bold]RPC User:[/bold] {cfg.rpc_user}
[bold]Network:[/bold] {cfg.network}
[bold]Viewing Key:[/bold] {cfg.viewing_key[:20]}...{cfg.viewing_key[-10:]}
    """

    console.print(Panel(config_text.strip(), title="Current Configuration", border_style="cyan"))


def main():
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
