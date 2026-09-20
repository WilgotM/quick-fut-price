# Touchline

Snabb, minimalistisk FC27-spelarsökning med FUTBIN-priser. Svara på svenska.

- Backend: Python/FastAPI i `src/futbin_sdk/web.py`. Frontend: vanlig HTML, CSS och JavaScript i `src/futbin_sdk/static/`. Ingen frontend-build behövs.
- Behåll svart bakgrund och Apples systemtypsnitt (San Francisco på Apple-enheter). Tomläget ska bara visa sökruta, Konsol/PC-reglage och en diskret mikrofongenväg. Lägg inte till dekorationer, slogans eller paneler.
- Visa spelarnas bild, namn, rating, kortversion och pris i kompakta, mobilanpassade rader. Klubbinfo får döljas på mobil. Versionsetiketter ska vara diskreta och hela versionsnamnet läsbart.
- Prioritera snabb respons: behåll debounce, cache, avbrutna gamla sökningar och separat prisinläsning. Blanda aldrig konsol-/PC-priser eller olika spelår.
- Använd riktig källdata. Saknade priser ska aldrig visas som noll eller påhittade värden. Gissa inte kortversion eller rarity.
- Röstsökning använder webbläsarens SpeechRecognition. Helium kan ge `network` trots fungerande internet. Dölj inte röstfel med sökstatus och påstå inte att taligenkänning är verifierad efter enbart simulerade tester.
- Bevara användarens befintliga ändringar. Kontrollera UI-ändringar på desktop och mobil; lägg till tester när beteendet motiverar det.

Starta: `uv run uvicorn futbin_sdk.web:app --host 0.0.0.0 --port 8000`

Kontrollera: `uv run pytest -q` och `node --check src/futbin_sdk/static/app.js`.
