"""FUTBIN SDK TUI - Interactive Terminal User Interface using Textual"""

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    OptionList,
    Rule,
    Select,
    Static,
)
from textual.widgets.option_list import Option

from futbin_sdk.client import FutbinClient
from futbin_sdk.models import FullPlayer, PlayerSearchOptions, PopularPlayer


def format_price(price: int) -> str:
    """Format price with K/M suffix."""
    if price >= 1_000_000:
        return f"{price / 1_000_000:.1f}M"
    elif price >= 1_000:
        return f"{price / 1_000:.1f}K"
    return str(price) if price > 0 else "-"


def get_rating_color(rating: int) -> str:
    """Get color based on rating."""
    if rating >= 90:
        return "magenta"
    elif rating >= 85:
        return "yellow"
    elif rating >= 80:
        return "green"
    elif rating >= 75:
        return "cyan"
    return "white"


class PlayerDetailScreen(ModalScreen[None]):
    """Modal screen showing player details."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    PlayerDetailScreen {
        align: center middle;
    }

    #detail-dialog {
        width: 60;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    #detail-title {
        text-align: center;
        text-style: bold;
        color: $text;
        padding: 1;
        background: $primary-darken-2;
    }

    .info-row {
        height: 3;
        padding: 0 1;
    }

    .info-item {
        width: 1fr;
        height: 3;
        content-align: center middle;
        text-align: center;
        background: $surface-darken-1;
        margin: 0 1;
    }

    .attr-row {
        height: 3;
        padding: 0 1;
    }

    .attr-item {
        width: 1fr;
        height: 3;
        content-align: center middle;
        text-align: center;
        background: $panel;
        margin: 0 1;
    }

    #close-detail-btn {
        width: 100%;
        margin-top: 1;
        border: round $primary;
    }

    #close-detail-btn:hover {
        background: $primary-lighten-1;
        border: round $primary-lighten-1;
    }

    .section-label {
        text-align: center;
        color: $primary;
        padding: 1 0;
        text-style: bold;
    }
    """

    def __init__(self, player: FullPlayer | PopularPlayer) -> None:
        super().__init__()
        self.player = player

    def compose(self) -> ComposeResult:
        player = self.player
        is_full = isinstance(player, FullPlayer)
        rating_color = get_rating_color(player.rating)

        with Container(id="detail-dialog"):
            yield Static(f"⚽ {player.name}", id="detail-title")

            with Horizontal(classes="info-row"):
                yield Static(f"[{rating_color}]★ {player.rating}[/]", classes="info-item")
                yield Static(f"[$success]PS: {format_price(player.price_ps)}[/]", classes="info-item")
                yield Static(f"[$primary]PC: {format_price(player.price_pc)}[/]", classes="info-item")

            if is_full and isinstance(player, FullPlayer):
                yield Rule()
                yield Static("Player Info", classes="section-label")

                with Horizontal(classes="info-row"):
                    yield Static(f"[$warning]{player.position}[/]", classes="info-item")
                    yield Static(f"{player.club[:18]}" if player.club else "-", classes="info-item")

                with Horizontal(classes="info-row"):
                    yield Static(f"{player.nation}" if player.nation else "-", classes="info-item")
                    yield Static(f"{player.league[:18]}" if player.league else "-", classes="info-item")

                yield Rule()
                yield Static("Attributes", classes="section-label")

                with Horizontal(classes="attr-row"):
                    yield Static(f"[$success]PAC {player.pace}[/]", classes="attr-item")
                    yield Static(f"[$error]SHO {player.shooting}[/]", classes="attr-item")
                    yield Static(f"[$primary]PAS {player.passing}[/]", classes="attr-item")

                with Horizontal(classes="attr-row"):
                    yield Static(f"[$warning]DRI {player.dribbling}[/]", classes="attr-item")
                    yield Static(f"[$secondary]DEF {player.defending}[/]", classes="attr-item")
                    yield Static(f"[$accent]PHY {player.physical}[/]", classes="attr-item")

            yield Button("Close [Esc]", variant="primary", id="close-detail-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-detail-btn":
            self.dismiss()


# ASCII Art Logo
ASCII_LOGO = """[bold $primary]
 ███████╗██╗   ██╗████████╗██████╗ ██╗███╗   ██╗
 ██╔════╝██║   ██║╚══██╔══╝██╔══██╗██║████╗  ██║
 █████╗  ██║   ██║   ██║   ██████╔╝██║██╔██╗ ██║
 ██╔══╝  ██║   ██║   ██║   ██╔══██╗██║██║╚██╗██║
 ██║     ╚██████╔╝   ██║   ██████╔╝██║██║ ╚████║
 ╚═╝      ╚═════╝    ╚═╝   ╚═════╝ ╚═╝╚═╝  ╚═══╝[/]
[dim]       ⚽ FIFA Ultimate Team Database ⚽[/]"""


class FutbinTUI(App[None]):
    """Interactive FUTBIN Terminal User Interface."""

    TITLE = "FUTBIN SDK"
    SUB_TITLE = "FIFA Ultimate Team Player Database"

    CSS = """
    #main-container {
        width: 100%;
        height: 100%;
    }

    #header-ascii {
        width: 100%;
        height: 9;
        text-align: center;
        padding: 0;
        background: $surface;
        border-bottom: solid $primary-darken-3;
    }

    #search-container {
        width: 100%;
        height: 5;
        padding: 1 2;
        background: $surface;
    }

    .search-row {
        width: 100%;
        height: 3;
    }

    #search-input {
        width: 1fr;
        margin-right: 1;
        border: round $primary-darken-2;
    }

    #search-input:focus {
        border: round $primary;
    }

    #platform-select {
        width: 10;
        border: round $primary-darken-2;
    }

    /* Google Material Design Style Buttons */
    Button {
        border: round $primary-darken-1;
        padding: 0 2;
        height: 3;
        min-width: 10;
    }

    Button:hover {
        border: round $primary;
    }

    Button:focus {
        border: round $primary;
        text-style: bold;
    }

    #search-btn {
        margin-left: 1;
        background: $primary;
        color: $text;
        border: round $primary;
    }

    #search-btn:hover {
        background: $primary-lighten-1;
    }

    #quick-actions {
        width: 100%;
        height: 5;
        padding: 1 2;
        background: $panel;
        align: center middle;
        border-bottom: solid $primary-darken-3;
    }

    .action-btn {
        margin: 0 1;
        min-width: 16;
        height: 3;
        padding: 0 3;
    }

    #btn-popular {
        background: $error;
        color: $text;
        border: round $error;
    }

    #btn-popular:hover {
        background: $error-lighten-1;
        border: round $error-lighten-1;
    }

    #btn-totw {
        background: $warning;
        color: $background;
        border: round $warning;
    }

    #btn-totw:hover {
        background: $warning-lighten-1;
        border: round $warning-lighten-1;
    }

    #btn-latest {
        background: $primary;
        color: $text;
        border: round $primary;
    }

    #btn-latest:hover {
        background: $primary-lighten-1;
        border: round $primary-lighten-1;
    }

    #btn-leagues {
        background: $accent;
        color: $text;
        border: round $accent;
    }

    #btn-leagues:hover {
        background: $accent-lighten-1;
        border: round $accent-lighten-1;
    }

    #content-container {
        width: 100%;
        height: 1fr;
        padding: 1;
    }

    #players-table {
        width: 100%;
        height: 100%;
    }

    #leagues-container {
        width: 100%;
        height: 1fr;
        padding: 1;
        display: none;
    }

    #leagues-list {
        width: 100%;
        height: 100%;
    }

    #status-bar {
        dock: bottom;
        width: 100%;
        height: 1;
        background: $primary;
        color: $background;
        text-align: center;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("1", "popular", "Popular", show=True),
        Binding("2", "totw", "TOTW", show=True),
        Binding("3", "latest", "Latest", show=True),
        Binding("4", "leagues", "Leagues", show=True),
        Binding("slash", "focus_search", "/Search", show=True),
        Binding("t", "toggle_theme", "Theme", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.current_players: list[FullPlayer] = []
        self.popular_players: list[PopularPlayer] = []
        self.current_view = "popular"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="main-container"):
            yield Static(ASCII_LOGO, id="header-ascii")

            with Container(id="search-container"):
                with Horizontal(classes="search-row"):
                    yield Input(placeholder="Search player name...", id="search-input")
                    yield Select(
                        [("PS", "PS"), ("PC", "PC")],
                        value="PS",
                        id="platform-select",
                        allow_blank=False,
                    )
                    yield Button("Search", variant="primary", id="search-btn")

            with Horizontal(id="quick-actions"):
                yield Button("🔥 Popular", id="btn-popular", classes="action-btn")
                yield Button("⭐ TOTW", id="btn-totw", classes="action-btn")
                yield Button("🆕 Latest", id="btn-latest", classes="action-btn")
                yield Button("🏆 Leagues", id="btn-leagues", classes="action-btn")

            with VerticalScroll(id="content-container"):
                yield DataTable(id="players-table", zebra_stripes=True)

            with VerticalScroll(id="leagues-container"):
                yield OptionList(id="leagues-list")

            yield Static("Ready | Press 1-4 for quick actions | t to change theme", id="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        # Use tokyo-night theme by default
        self.theme = "tokyo-night"

        table = self.query_one("#players-table", DataTable)
        table.add_columns("ID", "Name", "Rating", "Pos", "Club", "PS", "PC")
        table.cursor_type = "row"
        self.load_popular()

    def action_toggle_theme(self) -> None:
        """Toggle between themes."""
        themes = ["tokyo-night", "dracula", "monokai", "nord", "gruvbox", "catppuccin-mocha"]
        current = self.theme or "tokyo-night"
        try:
            idx = themes.index(current)
            self.theme = themes[(idx + 1) % len(themes)]
        except ValueError:
            self.theme = themes[0]
        self.notify(f"Theme: {self.theme}")

    def update_status(self, message: str) -> None:
        """Update status bar message."""
        status = self.query_one("#status-bar", Static)
        status.update(message)

    def show_players_view(self) -> None:
        """Show players table, hide leagues."""
        self.query_one("#content-container").styles.display = "block"
        self.query_one("#leagues-container").styles.display = "none"

    def show_leagues_view(self) -> None:
        """Show leagues list, hide players."""
        self.query_one("#content-container").styles.display = "none"
        self.query_one("#leagues-container").styles.display = "block"

    @work(exclusive=True)
    async def load_popular(self) -> None:
        """Load popular players."""
        self.current_view = "popular"
        table = self.query_one("#players-table", DataTable)
        table.clear()
        self.update_status("⏳ Loading popular players...")
        self.show_players_view()

        try:
            async with FutbinClient() as client:
                players = await client.get_popular_players()

            self.popular_players = players
            self.current_players = []

            for player in players:
                color = get_rating_color(player.rating)
                table.add_row(
                    str(player.futbin_id),
                    player.name,
                    f"[{color}]{player.rating}[/]",
                    "-",
                    "-",
                    f"[green]{format_price(player.price_ps)}[/]",
                    f"[cyan]{format_price(player.price_pc)}[/]",
                )

            self.update_status(f"🔥 Popular | {len(players)} players | t=theme")

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            self.update_status("❌ Error loading data")

    @work(exclusive=True)
    async def load_totw(self) -> None:
        """Load TOTW players."""
        self.current_view = "totw"
        table = self.query_one("#players-table", DataTable)
        table.clear()
        self.update_status("⏳ Loading TOTW...")
        self.show_players_view()

        try:
            async with FutbinClient() as client:
                players = await client.get_totw()

            self.current_players = players
            self.popular_players = []

            for player in players:
                color = get_rating_color(player.rating)
                club = (player.club[:10] + "..") if len(player.club) > 12 else player.club
                table.add_row(
                    str(player.futbin_id),
                    player.name or player.common_name,
                    f"[{color}]{player.rating}[/]",
                    player.position,
                    club,
                    f"[green]{format_price(player.price_ps)}[/]",
                    f"[cyan]{format_price(player.price_pc)}[/]",
                )

            self.update_status(f"⭐ TOTW | {len(players)} players | t=theme")

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            self.update_status("❌ Error loading TOTW")

    @work(exclusive=True)
    async def load_latest(self) -> None:
        """Load latest players."""
        self.current_view = "latest"
        table = self.query_one("#players-table", DataTable)
        table.clear()
        self.update_status("⏳ Loading latest players...")
        self.show_players_view()

        try:
            async with FutbinClient() as client:
                players = await client.get_latest_players()

            self.current_players = players
            self.popular_players = []

            for player in players:
                color = get_rating_color(player.rating)
                club = (player.club[:10] + "..") if len(player.club) > 12 else player.club
                table.add_row(
                    str(player.futbin_id),
                    player.name or player.common_name,
                    f"[{color}]{player.rating}[/]",
                    player.position,
                    club,
                    f"[green]{format_price(player.price_ps)}[/]",
                    f"[cyan]{format_price(player.price_pc)}[/]",
                )

            self.update_status(f"🆕 Latest | {len(players)} players | t=theme")

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            self.update_status("❌ Error loading latest")

    @work(exclusive=True)
    async def search_players(self, query: str) -> None:
        """Search players by name."""
        self.current_view = "search"
        table = self.query_one("#players-table", DataTable)
        table.clear()
        self.update_status(f"⏳ Searching '{query}'...")
        self.show_players_view()

        try:
            platform_select = self.query_one("#platform-select", Select)
            platform = str(platform_select.value) if platform_select.value else "PS"

            options = PlayerSearchOptions(platform=platform)

            async with FutbinClient() as client:
                players = await client.search_players(options)

            # Filter by name
            if query:
                query_lower = query.lower()
                players = [
                    p for p in players
                    if query_lower in (p.name or "").lower() or query_lower in (p.common_name or "").lower()
                ]

            self.current_players = players
            self.popular_players = []

            for player in players:
                color = get_rating_color(player.rating)
                club = (player.club[:10] + "..") if len(player.club) > 12 else player.club
                table.add_row(
                    str(player.futbin_id),
                    player.name or player.common_name,
                    f"[{color}]{player.rating}[/]",
                    player.position,
                    club,
                    f"[green]{format_price(player.price_ps)}[/]",
                    f"[cyan]{format_price(player.price_pc)}[/]",
                )

            self.update_status(f"🔍 '{query}' | {len(players)} results | t=theme")

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            self.update_status("❌ Search error")

    @work(exclusive=True)
    async def load_leagues(self) -> None:
        """Load leagues."""
        self.current_view = "leagues"
        results = self.query_one("#leagues-list", OptionList)
        results.clear_options()
        self.update_status("⏳ Loading leagues...")
        self.show_leagues_view()

        try:
            async with FutbinClient() as client:
                leagues = await client.get_leagues_and_clubs()

            for league in leagues:
                results.add_option(
                    Option(f"🏆 {league.name} ({len(league.clubs)} clubs)", id=str(league.league_id))
                )

            self.update_status(f"🏆 Leagues | {len(leagues)} total | t=theme")

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            self.update_status("❌ Error loading leagues")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-popular":
            self.load_popular()
        elif button_id == "btn-totw":
            self.load_totw()
        elif button_id == "btn-latest":
            self.load_latest()
        elif button_id == "btn-leagues":
            self.load_leagues()
        elif button_id == "search-btn":
            search_input = self.query_one("#search-input", Input)
            if search_input.value.strip():
                self.search_players(search_input.value.strip())
            else:
                self.notify("Enter a search term", severity="warning")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in search input."""
        if event.input.id == "search-input" and event.value.strip():
            self.search_players(event.value.strip())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in data table."""
        table = self.query_one("#players-table", DataTable)
        row_key = event.row_key

        if row_key is None:
            return

        row_data = table.get_row(row_key)
        try:
            player_id = int(row_data[0])
        except (ValueError, IndexError):
            return

        # Find the player
        player: FullPlayer | PopularPlayer | None = None

        for p in self.current_players:
            if p.futbin_id == player_id:
                player = p
                break

        if player is None:
            for pop_player in self.popular_players:
                if pop_player.futbin_id == player_id:
                    player = pop_player
                    break

        if player:
            self.push_screen(PlayerDetailScreen(player))

    def action_refresh(self) -> None:
        """Refresh current view."""
        if self.current_view == "popular":
            self.load_popular()
        elif self.current_view == "totw":
            self.load_totw()
        elif self.current_view == "latest":
            self.load_latest()
        elif self.current_view == "leagues":
            self.load_leagues()
        else:
            self.load_popular()

    def action_popular(self) -> None:
        self.load_popular()

    def action_totw(self) -> None:
        self.load_totw()

    def action_latest(self) -> None:
        self.load_latest()

    def action_leagues(self) -> None:
        self.load_leagues()

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()


def run_tui() -> None:
    """Run the TUI application."""
    app = FutbinTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
