# HN-AI-05 — Cross-Hospital Resource Rebalancer

An emergency operations dashboard that simulates oxygen cylinder availability across six district hospitals, uses linear trend regression to predict imminent shortages before safety thresholds are breached, and deterministically optimizes inter-hospital resource transfers with strict donor safety guarantees.

---

## 1. Architecture

```text
React (Vite + TypeScript + Recharts)
        ↓ (2-second polling)
FastAPI Backend (/api/state)
        ↓
Deterministic Simulator (6 Hospitals, 3s ticks)
        ↓
Depletion Trend Regression (Units/hr & Time-to-shortage)
        ↓
Deterministic Transfer Optimizer (Donor safety constraint)
        ↓
Gemini API / Fallback Explanation (<= 25 words operational rationale)
        ↓
MongoDB Atlas / In-Memory Fallback Persistence
```

### Core Invariant: Python Owns the Decision
Per strict system specification, Gemini is **never** permitted to decide:
- Whether a transfer happens
- Source hospital (`H-B`)
- Destination hospital (`H-A`)
- Transfer quantity (`40 cylinders`)
- Dispatch deadline (`45-60 min`)
- Donor safety constraints

Gemini only receives an already calculated recommendation and produces a concise operational explanation. If Gemini times out, errors, or the API key is omitted, the system seamlessly uses a deterministic fallback explanation with zero service degradation.

---

## 2. Directory Structure

```text
hospital-resource-rebalancer/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── SummaryCards.tsx
│   │   │   ├── ControlBar.tsx
│   │   │   ├── HospitalGrid.tsx
│   │   │   ├── HospitalCard.tsx
│   │   │   ├── RecommendationPanel.tsx
│   │   │   ├── LiveChart.tsx
│   │   │   ├── EvaluationPanel.tsx
│   │   │   └── ReplayModal.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   ├── routes/
│   │   │   └── api.py
│   │   └── services/
│   │       ├── simulator.py
│   │       ├── predictor.py
│   │       ├── optimizer.py
│   │       ├── gemini.py
│   │       ├── evaluation.py
│   │       └── replay.py
│   ├── test_backend.py
│   ├── test_e2e_acceptance.py
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
│
├── test_live_http.py
├── .gitignore
└── README.md
```

---

## 3. Local Setup

### Backend

```bash
cd backend
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## 4. Environment Variables

Create `backend/.env` (or copy from `backend/.env.example`):

```env
# Optional: MongoDB Atlas connection string. If omitted, backend automatically
# activates the In-Memory Fallback store with zero data loss or downtime.
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=hospital_rebalancer

# Optional: Google Gemini API key. If omitted, deterministic fallback explanation is used.
GEMINI_API_KEY=

# Server port (default: 8000)
PORT=8000
```

---

## 5. MongoDB Atlas Setup

1. **Create Cluster**: Visit [MongoDB Atlas](https://www.mongodb.com/atlas) and deploy a free shared M0 cluster.
2. **Create Database User**: Under *Security > Database Access*, create a user with Read and Write permissions.
3. **Allow Network Access**: Under *Security > Network Access*, add IP address `0.0.0.0/0` (allow access from anywhere) or your current development IP.
4. **Copy Connection String**: Click *Connect > Drivers > Python*, copy the URI.
5. **Configure**: Paste the connection string into `backend/.env` under `MONGODB_URI`.
6. **Fallback Mode**: If MongoDB Atlas is unavailable or unconfigured, the application runs in `DATABASE: DEMO FALLBACK (In-Memory)` mode without crashing.

---

## 6. Judge Presentation & Demo Flow

### Step 1 — Establish Baseline
Open dashboard at `http://localhost:5173`. Show the 6 monitored hospitals (`H-A` through `H-F`).
> *"This system continuously monitors simulated oxygen availability across six district facilities."*

### Step 2 — Start Simulation
Click **[ START SIMULATION ]**. Observe live readings updating every 3 seconds, telemetry points appending to the Recharts curve.
> *"Readings are persisted and used to estimate depletion trends in real-time."*

### Step 3 — Inject Surge
Click the prominent red/amber **[ INJECT SURGE ]** button.
> *"We are now simulating an acute demand surge at District Hospital A."*

### Step 4 — Prediction
Watch Hospital A's stock plummet toward its safety limit (60 cylinders). The trend regression detects the drop and flags status as **CRITICAL** with shortage horizon < 2.0 hours.
> *"The trend model detects that Hospital A will reach its safety threshold first."*

### Step 5 — Recommendation
The **Operational Redistribution Optimizer** immediately surfaces:
- **Transfer**: `Hospital B → Hospital A`
- **Quantity**: `40 Oxygen Cylinders`
- **Deadline**: `Dispatch within ~45-60 minutes`
- **Donor Safety**: Verified safe surplus (+45 cylinders above threshold).
> *"The optimizer selects Hospital B because it can donate 40 cylinders while strictly retaining its required safety reserve."*

### Step 6 — Gemini Operational Explanation
Point to the AI explanation card:
> *"Gemini does not make the decision. It converts the already calculated recommendation into a concise operational justification."*

### Step 7 — Human Approval
Click **[ APPROVE TRANSFER ]**:
- Hospital A stock immediately jumps +40 cylinders.
- Hospital B stock decreases -40 cylinders.
- Hospital A time-to-shortage is extended and status recovers.
- Recommendation changes to `APPROVED`.
- `Shortage-Hours Prevented` metric increments in real-time.

### Step 8 — Counterfactual Replay
Click **[ REPLAY SCENARIO ]**:
- View the comparison between **Without System** (unmanaged surge, 5.5 shortage-hours) and **With System** (stabilized intervention, 4.5 shortage-hours).
- Demonstrates **1.0+ shortage-hours prevented** with zero donor breaches.

### Step 9 — Held-out Evaluation
View the **Model Evaluation** card:
- Displays **Model MAE (8.5)** vs **Baseline MAE (35.9)** on held-out simulated data.
- Shows real ~76% relative error reduction over the naive single-step baseline.

### Step 10 — Clean Reset
Click **[ RESET ]** to return the simulation to its exact initial state ready for another demonstration.

---

## 7. Verification & Automated Test Suites

The codebase includes two automated verification test suites:

```bash
# 1. Ten unit & service checks (tests 1-10 from Section 48):
python backend/test_backend.py

# 2. Automated end-to-end demo acceptance test (Section 49):
python backend/test_e2e_acceptance.py

# 3. Live HTTP end-to-end integration test against running servers:
python test_live_http.py
```

All suites execute and verify 100% of the demo requirements.

---

## 8. Render Deployment Configuration

### Backend Web Service
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**: `MONGODB_URI`, `GEMINI_API_KEY`, `PORT`

### Frontend Static Site
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist`
