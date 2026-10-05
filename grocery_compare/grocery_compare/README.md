# 🛒 GroceryCompare

**Type in a grocery item, see where it's cheaper: BigBasket or JioMart.**

---

## What is this project?

When you buy groceries online, the same packet of milk or atta can cost different amounts on different apps.
Checking each app one by one is boring. **GroceryCompare does it for you.**

You search for something like `milk`, and it shows you:

- The price on **BigBasket** and on **JioMart**, side by side
- **Which one is cheaper**, highlighted
- The **price per 100 g / 100 ml**, so a 500 g pack and a 1 kg pack can be compared fairly
- **How the price changed over time** (a graph)
- A **basket** that tells you the cheapest way to buy your whole shopping list (e.g. *"buy the milk on JioMart and the atta on BigBasket to save ₹25"*)
- **Analytics**: charts showing which store is cheaper overall, which gives bigger discounts, and so on

---

## The big picture (how it works)

The project has **two parts** that run at the same time, plus a **browser robot**:

```
   YOU
    │  type "milk"
    ▼
┌──────────────────┐        ┌─────────────────────┐        ┌──────────────────────┐
│  FRONTEND        │  asks  │  BACKEND            │ opens  │  CHROME (robot)      │
│  the website you │ ─────► │  the "brain"        │ ─────► │  visits BigBasket &  │
│  see and click   │ ◄───── │  (Python)           │ ◄───── │  JioMart, reads the  │
│  (React)         │ answers│                     │ prices │  prices off the page │
└──────────────────┘        └─────────┬───────────┘        └──────────────────────┘
                                      │ saves every price
                                      ▼
                             ┌──────────────────┐
                             │  DATABASE        │
                             │  (grocery.db)    │
                             │  a file of all   │
                             │  prices ever seen│
                             └──────────────────┘
```

Step by step, when you search `milk`:

1. **The frontend** (the website) sends your search to the backend.
2. **The backend** checks the database: *"did I already look up milk in the last 6 hours?"*
   - **Yes** → it answers instantly from the database.
   - **No** → it opens a real **Chrome window** that visits BigBasket and JioMart, just like you would, and reads the prices off the page. This is called **web scraping** and takes about 30–60 seconds.
3. The backend **cleans up** the data (turns "1 kg", "2 x 500 g" and so on into the same unit) and **matches** the same product across the two stores (e.g. "Amul Taaza 500 ml" on both).
4. Every price is **saved** in the database. That's how the price-history graphs are built.
5. The website shows you the comparison.

**Bonus:** while the backend is running, it automatically re-checks 15 popular items (milk, eggs, rice…) every 12 hours, so the history graphs grow by themselves.

> ⚠️ **Heads-up:** BigBasket sometimes detects the robot and blocks it. When that happens the app **doesn't try to sneak past**.
> It just shows the message *"BigBasket blocked the request, showing JioMart only"*. This is expected and not a bug.

---

## What's inside the folder

```
grocery-compare/
├── backend/            ← the "brain" (Python)
│   ├── app/            ← the backend code
│   │   ├── scrapers/   ← the Chrome robot that reads BigBasket & JioMart
│   │   ├── services/   ← cleaning, matching, analytics, auto-refresh timer
│   │   └── routers/    ← the "doors" the website knocks on (the API)
│   ├── tests/          ← automatic checks that the code works
│   ├── seed_scrape.py  ← optional: fills the database with popular items
│   └── grocery.db      ← the database (created automatically)
├── frontend/           ← the website (React)
│   └── src/pages/      ← one file per page: Home, Search, Product, Basket, Analytics
├── README.md           ← you are here
└── TECHNICAL.md        ← detailed version for developers
```

**Tools used (in one line each):**

| Tool | What it does here |
|---|---|
| **Python + FastAPI** | runs the backend |
| **Selenium** | controls Chrome to visit the store websites |
| **BeautifulSoup** | reads product names and prices out of the web page |
| **SQLite** | the database, a single file, nothing to install |
| **Pandas / NumPy** | does the maths for the analytics page |
| **React + Vite** | builds the website |
| **Plotly** | draws the charts |

---

## How to start the project

### Step 0: Install these once

You need **3 things** on your computer:

| What | Why | Where to get it |
|---|---|---|
| **Python 3.11 or newer** | runs the backend | https://www.python.org/downloads/ |
| **Node.js 20 or newer** | runs the website | https://nodejs.org/ (pick "LTS") |
| **Google Chrome** | the robot uses it | https://www.google.com/chrome/ |

> **Windows:** when installing Python, **tick the box "Add python.exe to PATH"** on the first screen.
>
> **Mac:** you can also install with Homebrew: `brew install python node` and `brew install --cask google-chrome`.

To check they're installed, open a terminal and run:

| Windows (PowerShell) | Mac (Terminal) |
|---|---|
| `python --version` | `python3 --version` |
| `node --version` | `node --version` |

Each should print a version number. If it says "not found", reinstall that tool (and on Windows, restart the terminal).

**How to open a terminal:**
- **Windows:** press the Start key, type `PowerShell`, press Enter.
- **Mac:** press `Cmd + Space`, type `Terminal`, press Enter.

---

### 🪟 Windows

You'll use **two PowerShell windows**: one for the backend, one for the website. Keep both open.

**Window 1: backend**

```powershell
cd "C:\path\to\grocery-compare\backend"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

When you see `Uvicorn running on http://127.0.0.1:8000`, the backend is up. **Leave this window open.**

> If `venv\Scripts\activate` shows a red error about *"running scripts is disabled"*, run this once, then try again:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (type `Y` when asked).

**Window 2: website**

```powershell
cd "C:\path\to\grocery-compare\frontend"
npm install
copy .env.example .env
npm run dev
```

When you see `Local: http://localhost:5173/`, open **http://localhost:5173** in your browser. 🎉

---

### 🍎 Mac

You'll use **two Terminal windows**: one for the backend, one for the website. Keep both open.

**Window 1: backend**

```bash
cd /path/to/grocery-compare/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

When you see `Uvicorn running on http://127.0.0.1:8000`, the backend is up. **Leave this window open.**

**Window 2: website**

```bash
cd /path/to/grocery-compare/frontend
npm install
cp .env.example .env
npm run dev
```

When you see `Local: http://localhost:5173/`, open **http://localhost:5173** in your browser. 🎉

> **Tip:** instead of typing the path after `cd`, type `cd ` (with a space) and drag the folder into the terminal window.

---

### Starting it again later

The install steps (`venv`, `pip install`, `npm install`, `copy`/`cp`) are **only needed the first time**. Next time:

| | Windows | Mac |
|---|---|---|
| **Backend** | `cd backend` → `venv\Scripts\activate` → `uvicorn app.main:app --reload --port 8000` | `cd backend` → `source venv/bin/activate` → `uvicorn app.main:app --reload --port 8000` |
| **Website** | `cd frontend` → `npm run dev` | `cd frontend` → `npm run dev` |

**To stop:** click the terminal window and press `Ctrl + C`.

---

## Using the app

1. **Search** for an item (e.g. `milk`). The first time, a Chrome window opens by itself and visits the stores. **Don't close it**; it closes on its own. Wait about 30–60 seconds.
2. **Change your pincode** with the 📍 button at the top. Prices differ by area.
3. Click **+ Basket** on items, then open **Basket** to see the cheapest way to buy everything.
4. Click a product name to see its **price history**.
5. Open **Analytics** for charts comparing the two stores.

**Optional: fill the database in one go.** With the backend running, open a **third** terminal:

```bash
cd backend
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac
python seed_scrape.py          # checks 15 popular items (about 10 minutes)
```

**Optional: run the automatic checks** (in the backend folder with the venv active): `pytest`

---

## Something not working?

| Problem | Fix |
|---|---|
| `python` / `node` "not recognized" or "not found" | Install it (Step 0), then **close and reopen** the terminal. On Mac use `python3`. |
| Website says *"Can't reach the backend"* | The backend window isn't running. Start it (Window 1). |
| "BigBasket blocked the request…" | Normal. BigBasket blocked the robot; JioMart prices still show. Try again after 30+ minutes. |
| Search takes long | The first search for an item really opens the stores (about 30–60 s). Repeat searches are instant for 6 hours. |
| `port 8000` or `5173` "already in use" | An old copy is still running. Close the other terminal, or restart your computer. |
| Chrome opens and closes with an error | Update Google Chrome to the latest version. |
| Charts say "only one price so far" | History builds up over time as the app re-checks prices. Come back later. |

---

## Please note

This is a **student / educational project**. It is not connected to BigBasket or JioMart. It visits their websites slowly and politely,
and prices can be out of date, so always double-check in the store's app before buying.

For the detailed developer version (API list, settings, design decisions) see **[TECHNICAL.md](TECHNICAL.md)**.
