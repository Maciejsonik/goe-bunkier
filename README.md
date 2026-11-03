# 🎙️ CO-STREAM GOE • System Statystyk Widowni

Real-time stream tracker, analityka widowni i generator grafik porównawczych dla **Co-streamu GoE (Kielecki Bunkier)** oraz ekipy **Nervariena**.

---

## ⚡ Architektura

- **Backend (Python 3):**
  - Działa lokalnie na komputerze (zbieranie co 15s bez API key i bez blokad botów).
  - Równoległy scraping Twitch GQL + YouTube.
  - Zapis historii do SQLite (`history.db`).
  - Generowanie grafik 1080x1350 w estetyce plakatu GoE:
    - `battle_card.png` (Karta LIVE z awatarami w ramkach)
    - `goe_summary.png` (Oś czasu widowni GoE: YouTube vs Twitch)
    - `stream_summary.png` (Oś czasu pojedynku: GoE vs Nervarien)
  - Serwer HTTP z API REST i obsługą tuneli (Cloudflare / Localtunnel).

- **Frontend (GitHub Pages / Standalone HTML):**
  - Czysty HTML5, CSS i Chart.js – zero zbędnych bibliotek.
  - 2 dedykowane, niezależne wykresy (GoE Only oraz GoE vs Nervarien).
  - Filtry pojedynczych transmisji (aż do pojedynczego streama).
  - Wybór zakresu czasowego wykresów (15 min, 30 min, 1 godz., 2 godz., Cały stream).
  - Wskaźnik stanu backendu z możliwością podania własnego adresu API.

---

## 🚀 Jak uruchomić

### 1. Uruchomienie lokalne backendu:
```bash
# Uruchomienie serwera na porcie 5050 ze zbieraczem co 15s w tle:
python3 server.py
```
Panel będzie dostępny pod adresem: `http://localhost:5050`

### 2. Udostępnienie backendu przez Cloudflare Tunnel:
```bash
cloudflared tunnel --url http://127.0.0.1:5050
```

### 3. Frontend na GitHub Pages:
Włącz GitHub Pages w ustawieniach repozytorium:
- **Settings** -> **Pages** -> **Source**: `Deploy from a branch` -> branch: `main` / root (`/`).
- Strona będzie dostępna publicznie pod adresem: `https://<twoj-login>.github.io/<nazwa-repo>/`.

---

## 📸 Tryb CLI

```bash
# Pojedynczy pomiar w terminalu i zapis grafik:
python3 main.py

# Wygenerowanie wykresu podsumowania GoE:
python3 main.py --summary --mode GOE

# Wygenerowanie wykresu porównania z Nervarienem:
python3 main.py --summary --mode COMPARISON

# Eksport całej historii do CSV:
python3 main.py --export-csv stream_data.csv
```

---
*#bunkier • DEJF \| CZARNYPIOTRUS \| BIALITO \| MAJUTEK \| PEDRO \| MAGVAYER \| JASKIER*
