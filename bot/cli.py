"""
Binance Futures Testnet Trading Bot
------------------------------------
Place MARKET, LIMIT, STOP (STOP_LIMIT), and STOP_MARKET orders from the command line.

Usage:
  python -m bot.cli place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
  python -m bot.cli place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 120000
  python -m bot.cli place --symbol BTCUSDT --side SELL --type STOP --quantity 0.01 --stop-price 60000 --price 59900
  python -m bot.cli place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 95000
  python -m bot.cli price --symbol BTCUSDT
  python -m bot.cli account
"""

import os
from typing import Optional

import typer
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bot.client import BinanceAPIError, BinanceFuturesClient
from bot.logging_config import setup_logging
from bot.orders import OrderService
from bot.validators import validate_all, validate_symbol

load_dotenv()
setup_logging()

console = Console()
app = typer.Typer(
    help="Binance Futures Testnet — place and track orders",
    add_completion=False
)


def build_client():
    key = os.getenv("BINANCE_API_KEY", "").strip()
    secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not key or not secret:
        console.print(Panel(
            "[red]BINANCE_API_KEY and BINANCE_API_SECRET not set.[/]\n\n"
            "Copy [cyan].env.example[/] to [cyan].env[/] and add your testnet credentials.\n"
            "Get them from: https://testnet.binancefuture.com",
            title="Missing credentials",
            border_style="red"
        ))
        raise typer.Exit(1)

    return BinanceFuturesClient(api_key=key, api_secret=secret)


def print_request_table(params):
    t = Table(title="Order Request", box=box.ROUNDED, border_style="cyan")
    t.add_column("Field", style="bold")
    t.add_column("Value")

    side_color = "green" if params["side"] == "BUY" else "red"

    t.add_row("Symbol", f"[yellow]{params['symbol']}[/]")
    t.add_row("Side", f"[{side_color}]{params['side']}[/]")
    t.add_row("Type", params["order_type"])
    t.add_row("Quantity", str(params["quantity"]))

    if params.get("price"):
        t.add_row("Limit Price", str(params["price"]))
    if params.get("stop_price"):
        t.add_row("Stop Price", str(params["stop_price"]))

    console.print()
    console.print(t)


def print_result_table(result):
    if result.success:
        status_color = "green" if result.status in ("FILLED", "NEW") else "yellow"

        t = Table(title="Order Response", box=box.ROUNDED, border_style="green")
        t.add_column("Field", style="bold")
        t.add_column("Value")

        for label, value in result.display_rows():
            if label == "Status":
                t.add_row(label, f"[{status_color}]{value}[/]")
            elif label == "Side":
                c = "green" if value == "BUY" else "red"
                t.add_row(label, f"[{c}]{value}[/]")
            else:
                t.add_row(label, str(value) if value else "-")

        console.print()
        console.print(t)
        console.print(f"\n[bold green]Order placed successfully![/]\n")
    else:
        console.print()
        console.print(Panel(
            f"[red]{result.error}[/]",
            title="Order Failed",
            border_style="red"
        ))
        console.print()


@app.command()
def place(
    symbol: str = typer.Option(..., "--symbol", "-s", help="e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", help="BUY or SELL"),
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET / LIMIT / STOP / STOP_MARKET"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="e.g. 0.01"),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="required for LIMIT"),
    stop_price: Optional[float] = typer.Option(None, "--stop-price", help="required for STOP and STOP_MARKET"),
    time_in_force: str = typer.Option("GTC", "--tif", help="GTC / IOC / FOK (LIMIT only)"),
):
    """Place a new order on Binance Futures Testnet."""
    console.rule("[cyan]Binance Futures Testnet Bot[/]")

    try:
        params = validate_all(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValueError as e:
        console.print(Panel(f"[red]{e}[/]", title="Validation Error", border_style="red"))
        raise typer.Exit(1)

    print_request_table(params)

    client = build_client()
    service = OrderService(client)

    with console.status("Submitting order...", spinner="dots"):
        result = service.place(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
            time_in_force=time_in_force,
        )

    print_result_table(result)

    if not result.success:
        raise typer.Exit(1)


@app.command()
def price(
    symbol: str = typer.Option(..., "--symbol", "-s", help="e.g. BTCUSDT"),
):
    """Check current price for a symbol."""
    console.rule("[cyan]Price Check[/]")

    try:
        sym = validate_symbol(symbol)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)

    client = build_client()

    with console.status(f"Fetching {sym} price...", spinner="dots"):
        try:
            data = client.get_price(sym)
        except (BinanceAPIError, ConnectionError, TimeoutError) as e:
            console.print(Panel(f"[red]{e}[/]", title="Error", border_style="red"))
            raise typer.Exit(1)

    t = Table(box=box.ROUNDED, border_style="cyan", show_header=False)
    t.add_column("k", style="bold")
    t.add_column("v")
    t.add_row("Symbol", data.get("symbol", sym))
    t.add_row("Price", f"[yellow]{data.get('price', 'N/A')}[/]")

    console.print()
    console.print(t)
    console.print()


@app.command()
def account():
    """Show account balances."""
    console.rule("[cyan]Account Info[/]")

    client = build_client()

    with console.status("Loading account...", spinner="dots"):
        try:
            data = client.get_account()
        except (BinanceAPIError, ConnectionError, TimeoutError) as e:
            console.print(Panel(f"[red]{e}[/]", title="Error", border_style="red"))
            raise typer.Exit(1)

    assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) > 0]

    if not assets:
        console.print("\n[yellow]No funded assets found.[/]\n")
        return

    t = Table(title="Balances", box=box.ROUNDED, border_style="cyan")
    t.add_column("Asset", style="bold yellow")
    t.add_column("Wallet Balance", justify="right")
    t.add_column("Unrealised PnL", justify="right")

    for a in assets:
        pnl = float(a.get("unrealizedProfit", 0))
        color = "green" if pnl >= 0 else "red"
        t.add_row(
            a.get("asset", ""),
            a.get("walletBalance", "0"),
            f"[{color}]{pnl:.4f}[/]",
        )

    console.print()
    console.print(t)
    console.print()


if __name__ == "__main__":
    app()
