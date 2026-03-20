# ✈ SkyQuery — Flight Search App

A Trip.com-style flight search application built with **React** (frontend) and **Flask + Hive** (backend), querying 80M+ flight itineraries.

---

## 📁 Project Structure

```
webapp/
├── flask_api.py              # Flask backend (deploy on VM)
├── README.md                 # This file
└── frontend/                 # React frontend (run on Windows)
    ├── src/
    │   ├── api.js            # API helper (axios)
    │   ├── App.js            # Router setup
    │   ├── App.css           # Dark theme styles
    │   ├── index.css          # Base styles
    │   ├── components/
    │   │   └── Navbar.js     # Navigation bar with health indicator
    │   └── pages/
    │       ├── FlightSearch.js      # Flight search with cards
    │       ├── WhereToFly.js        # Bar chart of destinations
    │       ├── WhenToFly.js         # Price trends by month
    │       ├── AirlineComparison.js # Compare airline prices
    │       ├── Chatbot.js           # AI text-to-SQL chatbot
    │       └── AirportExplorer.js   # Airport search
    └── package.json
```

---

## 🚀 Setup Instructions

### 1. Backend (VM — 192.168.56.101)

Copy `flask_api.py` to your VM and run:

```bash
# Install dependencies (if not already)
pip install flask flask-cors pyhive thrift openai

# (Optional) Set OpenAI API key for chatbot feature
export OPENAI_API_KEY="sk-your-key-here"

# Run the Flask server
python flask_api.py
```

The API will be available at `http://192.168.56.101:5000`.

**Test it:**
```bash
curl http://192.168.56.101:5000/api/health
curl http://192.168.56.101:5000/api/tables
```

### 2. Frontend (Windows PC)

```bash
# Navigate to the frontend folder
cd "d:\Internship\Final project\webapp\frontend"

# Install dependencies (already done if you cloned this)
npm install

# Start the development server
npm start
```

The React app will open at `http://localhost:3000`.

---

## 🔌 API Endpoints

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/api/health` | GET | Check Hive connection | |
| `/api/tables` | GET | List database tables | |
| `/api/search-flights` | GET | Search flights | `?origin=ATL&dest=LAX&nonstop=true&sort=cheapest&limit=20` |
| `/api/where-to-fly` | GET | Cheapest destinations | `?origin=ATL&limit=10&nonstop=false` |
| `/api/when-to-fly` | GET | Price trends by month | `?origin=ATL&dest=LAX` |
| `/api/airline-comparison` | GET | Compare airlines on route | `?origin=ATL&dest=LAX` |
| `/api/airports` | GET | Search airports | `?q=Tokyo&limit=20` |
| `/api/chatbot` | POST | AI text-to-SQL | `{"question": "cheapest flights from ATL"}` |

---

## 📱 Pages

1. **✈ Flight Search** — Search flights by route with Trip.com-style flight cards
2. **🗺 Where to Fly** — Bar chart showing cheapest destinations from any airport
3. **📅 When to Fly** — Area chart showing price trends by month (min/avg/max)
4. **📊 Airline Comparison** — Grouped bar chart comparing airline prices on a route
5. **🤖 AI Chatbot** — Natural language to SQL powered by OpenAI + Hive
6. **🏢 Airport Explorer** — Search airports by name, city, or IATA code

---

## ⚠ Important Notes

- **Hive queries take 2–8 minutes** because ext_itineraries has ~80M rows (full table scan)
- **All ext_itineraries columns are STRING type** — the API uses `CAST()` for numeric operations
- The green/red dot in the navbar shows real-time backend connection status
- Every page has a "Show HiveQL Query" toggle to see the generated SQL
- The chatbot requires `OPENAI_API_KEY` environment variable on the VM
- API timeout is set to 10 minutes to accommodate slow Hive queries

---

## 🎨 Tech Stack

- **Frontend:** React, React Router, Recharts, Lucide Icons, Axios
- **Backend:** Flask, Flask-CORS, PyHive
- **Database:** Apache Hive (ticketmeta09 on Hadoop)
- **AI:** OpenAI GPT-3.5-turbo (for chatbot)
