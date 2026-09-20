"""FUTBIN SDK CLI - Beautiful command line interface for FUTBIN API"""

import asyncio
from typing import Any

import click
import pyfiglet
from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from futbin_sdk.client import FutbinClient
from futbin_sdk.models import FullPlayer, Platform, PlayerSearchOptions

console = Console()

# ASCII Art Banner
BANNER = """
╔═══════════════════════════════════════════════════════════════════════════╗
║  ███████╗██╗   ██╗████████╗██████╗ ██╗███╗   ██╗    ███████╗██████╗ ██╗  ██║
║  ██╔════╝██║   ██║╚══██╔══╝██╔══██╗██║████╗  ██║    ██╔════╝██╔══██╗██║ ██╔╝║
║  █████╗  ██║   ██║   ██║   ██████╔╝██║██╔██╗ ██║    ███████╗██║  ██║█████╔╝ ║
║  ██╔══╝  ██║   ██║   ██║   ██╔══██╗██║██║╚██╗██║    ╚════██║██║  ██║██╔═██╗ ║
║  ██║     ╚██████╔╝   ██║   ██████╔╝██║██║ ╚████║    ███████║██████╔╝██║  ██╗║
║  ╚═╝      ╚═════╝    ╚═╝   ╚═════╝ ╚═╝╚═╝  ╚═══╝    ╚══════╝╚═════╝ ╚═╝  ╚═╝║
║                                                                             ║
║              ⚽ FIFA Ultimate Team Player Database CLI ⚽                   ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""


def create_header() -> Panel:
    """Create a styled header panel with ASCII art."""
    # Use pyfiglet for dynamic ASCII art
    fig = pyfiglet.Figlet(font="slant", width=60)
    ascii_art = fig.renderText("FUTBIN")

    # Create colorful ASCII art
    lines = ascii_art.strip().split("\n")
    styled_lines: list[Text] = []
    colors = ["bright_cyan", "cyan", "blue", "bright_blue", "magenta", "bright_magenta"]

    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        styled_lines.append(Text(line, style=f"bold {color}"))

    # Combine ASCII art lines
    art_text = Text("\n").join(styled_lines)

    # Subtitle
    subtitle = Text()
    subtitle.append("⚽ ", style="bold yellow")
    subtitle.append("FIFA Ultimate Team Player Database CLI", style="bold white")
    subtitle.append(" ⚽", style="bold yellow")

    # Version info
    version_text = Text("v0.1.0", style="dim italic")

    # Create group with all elements
    content = Group(
        Align.center(art_text),
        Text(""),
        Align.center(subtitle),
        Align.center(version_text),
    )

    return Panel(
        content,
        box=box.DOUBLE,
        border_style="bright_cyan",
        padding=(1, 2),
    )


def format_price(price: int) -> str:
    """Format price with K/M suffix."""
    if price >= 1_000_000:
        return f"{price / 1_000_000:.1f}M"
    elif price >= 1_000:
        return f"{price / 1_000:.1f}K"
    return str(price)


def get_rating_style(rating: int) -> str:
    """Get color style based on rating."""
    if rating >= 90:
        return "bold magenta"
    elif rating >= 85:
        return "bold yellow"
    elif rating >= 80:
        return "bold green"
    elif rating >= 75:
        return "cyan"
    return "white"


def create_player_table(players: list[FullPlayer], platform: str = "PS") -> Table:
    """Create a beautiful table for player display."""
    table = Table(
        title="🎮 Players",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="blue",
        show_lines=True,
    )

    table.add_column("ID", style="dim", width=8)
    table.add_column("Name", style="bold white", width=20)
    table.add_column("Rating", justify="center", width=7)
    table.add_column("Position", justify="center", width=8)
    table.add_column("Club", width=15)
    table.add_column("Nation", width=12)
    table.add_column("Price", justify="right", style="green", width=10)
    table.add_column("PAC", justify="center", width=5)
    table.add_column("SHO", justify="center", width=5)
    table.add_column("PAS", justify="center", width=5)
    table.add_column("DRI", justify="center", width=5)
    table.add_column("DEF", justify="center", width=5)
    table.add_column("PHY", justify="center", width=5)

    for player in players:
        price = player.price_ps if platform.upper() == "PS" else player.price_pc
        rating_style = get_rating_style(player.rating)

        table.add_row(
            str(player.futbin_id),
            player.name or player.common_name,
            Text(str(player.rating), style=rating_style),
            player.position,
            player.club[:15] if player.club else "-",
            player.nation[:12] if player.nation else "-",
            format_price(price),
            str(player.pace),
            str(player.shooting),
            str(player.passing),
            str(player.dribbling),
            str(player.defending),
            str(player.physical),
        )

    return table


def create_price_panel(player_id: int, price_data: dict[str, Any], platform: str) -> Panel:
    """Create a price info panel."""
    content = Table.grid(padding=(0, 2))
    content.add_column(style="cyan")
    content.add_column(style="green")

    content.add_row("Current Price:", format_price(price_data.get("price", 0)))
    content.add_row("Min Price:", format_price(price_data.get("min_price", 0)))
    content.add_row("Max Price:", format_price(price_data.get("max_price", 0)))
    content.add_row("Updated:", price_data.get("updated", "N/A"))

    return Panel(
        content,
        title=f"💰 Player #{player_id} Price ({platform})",
        border_style="green",
        box=box.ROUNDED,
    )


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0", prog_name="futbin")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """FUTBIN SDK - FIFA Ultimate Team Player Database CLI

    Query player prices, search players, and explore FUTBIN data.
    """
    if ctx.invoked_subcommand is None:
        # Show header with ASCII art
        console.print(create_header())
        console.print()

        # Create commands table
        commands_table = Table(
            title="📋 Available Commands",
            box=box.ROUNDED,
            header_style="bold cyan",
            border_style="blue",
            show_lines=False,
        )
        commands_table.add_column("Command", style="bold green", width=12)
        commands_table.add_column("Description", style="white")

        commands_table.add_row("tui", "Launch interactive TUI mode")
        commands_table.add_row("price", "Get player price by FUTBIN ID")
        commands_table.add_row("search", "Search players with filters")
        commands_table.add_row("totw", "Get Team of the Week players")
        commands_table.add_row("latest", "Get latest players added")
        commands_table.add_row("popular", "Get popular/trending players")
        commands_table.add_row("leagues", "List all leagues and clubs")
        commands_table.add_row("versions", "List all card versions")

        console.print(commands_table)
        console.print()

        # Usage examples
        examples = Table.grid(padding=(0, 2))
        examples.add_column(style="dim")
        examples.add_column(style="cyan")

        examples.add_row("Usage:", "futbin [COMMAND] [OPTIONS]")
        examples.add_row("Example:", "futbin price 12345 --platform PS")
        examples.add_row("Example:", "futbin search --rating-min 85")
        examples.add_row("Help:", "futbin [COMMAND] --help")

        console.print(Panel(examples, title="💡 Quick Start", border_style="yellow", box=box.ROUNDED))


@cli.command()
def tui() -> None:
    """Launch interactive TUI mode with keyboard navigation."""
    from futbin_sdk.tui import run_tui

    run_tui()


@cli.command()
@click.argument("player_id", type=int)
@click.option("--platform", "-p", type=click.Choice(["PS", "PC", "XB"]), default="PS", help="Game platform")
def price(player_id: int, platform: str) -> None:
    """Get player price by FUTBIN ID."""
    console.print(create_header())

    with console.status("[bold cyan]Fetching player price...", spinner="dots"):
        try:
            client = FutbinClient()
            plat = Platform(platform)
            player_price = asyncio.run(_get_price(client, player_id, plat))

            price_data = {
                "price": player_price.price,
                "min_price": player_price.min_price,
                "max_price": player_price.max_price,
                "updated": player_price.updated,
            }
            console.print(create_price_panel(player_id, price_data, platform))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


async def _get_price(client: FutbinClient, player_id: int, platform: Platform) -> Any:
    """Async helper to get player price."""
    async with client:
        return await client.get_player_price(player_id, platform)


@cli.command()
@click.option("--platform", "-p", type=click.Choice(["PS", "PC"]), default="PS", help="Game platform")
@click.option("--page", type=int, default=1, help="Page number")
@click.option("--rating-min", type=int, help="Minimum rating")
@click.option("--rating-max", type=int, help="Maximum rating")
@click.option("--position", type=str, help="Position filter (comma-separated)")
@click.option("--nation", type=int, help="Nation ID")
@click.option("--league", type=int, help="League ID")
@click.option("--club", type=int, help="Club ID")
@click.option("--price-min", type=int, help="Minimum price")
@click.option("--price-max", type=int, help="Maximum price")
def search(
    platform: str,
    page: int,
    rating_min: int | None,
    rating_max: int | None,
    position: str | None,
    nation: int | None,
    league: int | None,
    club: int | None,
    price_min: int | None,
    price_max: int | None,
) -> None:
    """Search players with filters."""
    console.print(create_header())

    options = PlayerSearchOptions(
        platform=platform,
        page=page,
        min_rating=rating_min,
        max_rating=rating_max,
        position=position.split(",") if position else None,
        nation_id=nation,
        league_id=league,
        club_id=club,
        min_price=price_min,
        max_price=price_max,
    )

    with console.status("[bold cyan]Searching players...", spinner="dots"):
        try:
            players = asyncio.run(_search_players(options))
            if players:
                console.print(create_player_table(players, platform))
                console.print(f"\n[dim]Found {len(players)} players on page {page}[/dim]")
            else:
                console.print("[yellow]No players found matching your criteria.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


async def _search_players(options: PlayerSearchOptions) -> list[FullPlayer]:
    """Async helper to search players."""
    async with FutbinClient() as client:
        return await client.search_players(options)


@cli.command()
@click.option("--platform", "-p", type=click.Choice(["PS", "PC"]), default="PS", help="Game platform")
def totw(platform: str) -> None:
    """Get Team of the Week players."""
    console.print(create_header())

    with console.status("[bold cyan]Fetching TOTW...", spinner="dots"):
        try:
            players = asyncio.run(_get_totw())
            if players:
                console.print(create_player_table(players, platform))
                console.print(f"\n[dim]Total: {len(players)} TOTW players[/dim]")
            else:
                console.print("[yellow]No TOTW players available.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


async def _get_totw() -> list[FullPlayer]:
    """Async helper to get TOTW players."""
    async with FutbinClient() as client:
        return await client.get_totw()


@cli.command()
@click.option("--platform", "-p", type=click.Choice(["PS", "PC"]), default="PS", help="Game platform")
def latest(platform: str) -> None:
    """Get latest players added to the database."""
    console.print(create_header())

    with console.status("[bold cyan]Fetching latest players...", spinner="dots"):
        try:
            players = asyncio.run(_get_latest())
            if players:
                console.print(create_player_table(players, platform))
                console.print(f"\n[dim]Total: {len(players)} new players[/dim]")
            else:
                console.print("[yellow]No new players available.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


async def _get_latest() -> list[FullPlayer]:
    """Async helper to get latest players."""
    async with FutbinClient() as client:
        return await client.get_latest_players()


@cli.command()
def popular() -> None:
    """Get popular/trending players."""
    console.print(create_header())

    with console.status("[bold cyan]Fetching popular players...", spinner="dots"):
        try:
            players = asyncio.run(_get_popular())
            if players:
                table = Table(
                    title="🔥 Popular Players",
                    box=box.ROUNDED,
                    header_style="bold cyan",
                    border_style="red",
                )
                table.add_column("ID", style="dim", width=8)
                table.add_column("Name", style="bold white", width=25)
                table.add_column("Rating", justify="center", width=7)
                table.add_column("PS Price", justify="right", style="green", width=12)
                table.add_column("PC Price", justify="right", style="blue", width=12)

                for player in players:
                    rating_style = get_rating_style(player.rating)
                    table.add_row(
                        str(player.futbin_id),
                        player.name,
                        Text(str(player.rating), style=rating_style),
                        format_price(player.price_ps),
                        format_price(player.price_pc),
                    )

                console.print(table)
                console.print(f"\n[dim]Total: {len(players)} popular players[/dim]")
            else:
                console.print("[yellow]No popular players available.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


async def _get_popular() -> Any:
    """Async helper to get popular players."""
    async with FutbinClient() as client:
        return await client.get_popular_players()


@cli.command()
def leagues() -> None:
    """List all leagues and clubs."""
    console.print(create_header())

    with console.status("[bold cyan]Fetching leagues...", spinner="dots"):
        try:
            leagues_data = asyncio.run(_get_leagues())
            if leagues_data:
                table = Table(
                    title="🏆 Leagues",
                    box=box.ROUNDED,
                    header_style="bold cyan",
                    border_style="yellow",
                )
                table.add_column("ID", style="dim", width=6)
                table.add_column("League Name", style="bold white", width=30)
                table.add_column("Clubs", justify="right", width=8)

                for league in leagues_data:
                    table.add_row(
                        str(league.league_id),
                        league.name,
                        str(len(league.clubs)),
                    )

                console.print(table)
                console.print(f"\n[dim]Total: {len(leagues_data)} leagues[/dim]")
            else:
                console.print("[yellow]No leagues available.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


async def _get_leagues() -> Any:
    """Async helper to get leagues."""
    async with FutbinClient() as client:
        return await client.get_leagues_and_clubs()


@cli.command()
def versions() -> None:
    """List all card versions."""
    console.print(create_header())

    with console.status("[bold cyan]Fetching card versions...", spinner="dots"):
        try:
            versions_data = asyncio.run(_get_versions())
            if versions_data:
                table = Table(
                    title="🃏 Card Versions",
                    box=box.ROUNDED,
                    header_style="bold cyan",
                    border_style="magenta",
                )
                table.add_column("Key", style="dim", width=15)
                table.add_column("Name", style="bold white", width=30)
                table.add_column("Image ID", width=15)

                for version in versions_data:
                    table.add_row(
                        version.key,
                        version.name,
                        version.img,
                    )

                console.print(table)
                console.print(f"\n[dim]Total: {len(versions_data)} card versions[/dim]")
            else:
                console.print("[yellow]No card versions available.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


async def _get_versions() -> Any:
    """Async helper to get card versions."""
    async with FutbinClient() as client:
        return await client.get_card_versions()


def main() -> None:
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
