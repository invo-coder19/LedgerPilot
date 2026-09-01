# 🚀 LedgerPilot — Autonomous AI Finance Controller

[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-FF6F00.svg)](https://langchain-ai.github.io/langgraph/)

> **LedgerPilot** is a production-grade, enterprise-ready **Autonomous AI Finance Controller**. It seamlessly bridges multi-source financial reconciliation, machine learning anomaly classification, LangGraph-driven AI root-cause investigation, and deterministic confidence-gated policy control to automatically resolve bounded low-risk discrepancies while safely escalating high-risk exceptions to human finance managers.

---

## 🌟 Executive Summary & Core Value Proposition

Modern high-volume fintechs and merchant payment ecosystems process millions of transactions daily across payment gateways, issuing banks, internal order ledgers, and settlement files. Manual exception resolution causes operational bottlenecks, reconciliation lag, and financial leakage.

**LedgerPilot solves this with end-to-end autonomous controller architecture:**
1. **Multi-Way Ingestion & Reconciliation:** Ingests payments, invoices, settlements, and bank ledger records with high-precision fuzzy/exact multi-pass matching.
2. **ML Classification & Anomaly Detection:** Real-time exception type prediction and statistical anomaly isolation using tree-based ensemble models.
3. **AI Finance Investigator (LangGraph):** Autonomous investigative agent that formulates hypotheses, retrieves document evidence via hybrid vector search (RAG), and establishes causal audit trails without hallucinating financial actions.
4. **Autonomous Controller with Confidence Gates:** Deterministic policy engine enforcing transaction limits, risk ceilings, and dual-key manager approval workflows.
5. **Failure Simulation & Benchmark Verification:** Fully reproducible synthetic benchmark framework with 9 failure injection scenarios and ground-truth metrics.

---

## 🏗️ System Architecture

```
                                  ┌──────────────────────────────────────────────┐
                                  │           DATA INGESTION LAYER               │
                                  │  Payments · Invoices · Settlements · Banks   │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                                                         ▼
                                  ┌──────────────────────────────────────────────┐
                                  │      MULTI-WAY RECONCILIATION ENGINE         │
                                  │   Rule Matching · Fuzzy Windowing · Fees     │
                                  └──────────────┬────────────────┬──────────────┘
                                                 │                │
                                 (Matched: Safe) │                │ (Exceptions Detected)
                                                 ▼                ▼
                                  ┌────────────────┐   ┌─────────────────────────┐
                                  │ Reconciled DB  │   │  ML PREDICTION PIPELINE │
                                  │ Ledger Records │   │ Classification & Anomaly│
                                  └────────────────┘   └────────────┬────────────┘
                                                                    │
                                                                    ▼
                                                       ┌─────────────────────────┐
                                                       │  AI INVESTIGATOR AGENT  │
                                                       │   (LangGraph + RAG)     │
                                                       └────────────┬────────────┘
                                                                    │
                                                                    ▼
                                                       ┌─────────────────────────┐
                                                       │ RISK & CONFIDENCE GATES │
                                                       │ (Deterministic Formula) │
                                                       └────────────┬────────────┘
                                                                    │
                                      ┌─────────────────────────────┴─────────────────────────────┐
                                      │                                                           │
                                      ▼                                                           ▼
                        ┌───────────────────────────┐                               ┌───────────────────────────┐
                        │   AUTO-RESOLUTION PATH    │                               │   HUMAN ESCALATION PATH   │
                        │ • Confidence >= 0.90      │                               │ • Medium/High Risk        │
                        │ • Low Financial Risk      │                               │ • Missing Evidence        │
                        │ • Policy Whitelisted      │                               │ • Tiered Manager Approval │
                        └─────────────┬─────────────┘                               └─────────────┬─────────────┘
                                      │                                                           │
                                      ▼                                                           ▼
                        ┌───────────────────────────┐                               ┌───────────────────────────┐
                        │   IDEMPOTENT EXECUTOR     │                               │      APPROVAL PORTAL      │
                        │   ACID Financial Actions  │                               │    Audit-Logged Review    │
                        └─────────────┬─────────────┘                               └─────────────┬─────────────┘
                                      │                                                           │
                                      └─────────────────────────────┬─────────────────────────────┘
                                                                    ▼
                                                      ┌───────────────────────────┐
                                                      │ IMMUTABLE AUDIT LOG ENGINE│
                                                      │  Complete Decision Lineage│
                                                      └───────────────────────────┘
```

---

## 🛡️ Safety & Governance: Why LedgerPilot Can Be Trusted

| Governance Pillar | Implementation in LedgerPilot |
| :--- | :--- |
| **No Unbounded LLM Actions** | LLMs produce advisory hypotheses only; mutations are executed strictly by deterministic policy engines. |
| **Confidence Gating** | Autonomy requires $\ge 90\%$ deterministic confidence. Scores $< 70\%$ automatically require human intervention. |
| **Merchant Data Isolation** | Strict tenancy boundaries; vector search and database queries are partitioned by merchant ID. |
| **ACID Guarantees** | Every ledger mutation runs within atomic database transactions; partial failures trigger automatic rollback. |
| **Reversibility & Rollback** | Automated actions retain state snapshots (`previous_state` / `new_state`) supporting 1-click audit-backed rollback. |
| **Auditability** | Every decision records inputs, ML confidence vector, cited evidence IDs, policy version, and actor ID. |

---

## 🧪 Ground-Truth Benchmark & Evaluation Framework

LedgerPilot includes a native evaluation suite for measuring precision, recall, and financial error rate.

### Run Benchmark via CLI
```bash
# 1. Generate 1,000 synthetic ground-truth cases with seed 42
python -m app.evaluation generate_dataset --records 1000 --seed 42 --name benchmark_v1 --version v1

# 2. Run automated evaluation against the benchmark dataset
python -m app.evaluation run --dataset benchmark_v1 --version v1

# 3. Generate detailed Markdown or JSON evaluation report
python -m app.evaluation report --run <RUN_ID> --format markdown --output benchmark_report.md
```

### Key Benchmark Metrics Output
* **Reconciliation Exact Match Accuracy:** $\ge 98.5\%$
* **ML Exception Classification F1-Weighted:** $\ge 0.92$
* **Citation Correctness (Anti-Hallucination):** $100\%$ (all citations verified)
* **Auto-Resolution Precision:** $\ge 99.2\%$
* **Autonomous Financial Error Rate:** $< 0.1\%$

---

## 🔬 9 Failure Simulation Scenarios

Test system resilience against unpredictable production conditions:

1. `missing_evidence` — Missing bank statement record $\rightarrow$ Confidence decreases below auto threshold $\rightarrow$ Routed to Human Review.
2. `contradictory_evidence` — Conflicting settlement vs bank amount $\rightarrow$ Contradiction detected $\rightarrow$ Controller BLOCKS action.
3. `llm_failure` — Simulated LLM timeout/503 $\rightarrow$ Graceful fallback to deterministic signals $\rightarrow$ Escalate.
4. `ml_failure` — Corrupted ML artifact $\rightarrow$ Model unavailability flagged $\rightarrow$ Safe fallback to human queue.
5. `action_failure` — Database failure mid-execution $\rightarrow$ Transaction rolled back $\rightarrow$ Action marked `FAILED` with audit trail.
6. `db_error` — Transaction rollback test $\rightarrow$ Zero partial financial state in database.
7. `duplicate_worker` — Identical task retry from Celery $\rightarrow$ Idempotency key blocks duplicate execution.
8. `kill_switch` — Global kill switch active $\rightarrow$ All pending/new automated actions immediately halted.
9. `policy_failure` — Policy missing/deactivated $\rightarrow$ System defaults to `BLOCK`, never open execution.

---

## 💻 Tech Stack

* **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
* **Database & Vector Store:** PostgreSQL 16+, `pgvector`
* **Caching & Asynchronous Processing:** Redis
* **Machine Learning:** Scikit-Learn, XGBoost, Pandas, NumPy, Joblib
* **AI & Agent Workflow:** LangGraph, LangChain, Google Gemini
* **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Heroicons, Recharts
* **Observability & Testing:** Structlog, Pytest, HTTPX

---

## 🚀 Quick Start Guide

### Prerequisites
* [Docker & Docker Compose](https://www.docker.com/) OR
* Python 3.11+, Node.js 18+, PostgreSQL 16+, Redis 7+

### Option 1: Quickstart with Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/invo-coder19/LedgerPilot.git
cd LedgerPilot

# 2. Copy environment configuration
cp .env.example .env

# 3. Start all services (Backend, Frontend, PostgreSQL, Redis)
docker compose up -d --build

# 4. Apply database migrations
docker compose exec backend alembic upgrade head

# 5. Seed initial users, merchants, rules, and demo data
docker compose exec backend python -m app.seed
```

### Option 2: Local Development Setup

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations and seed
alembic upgrade head
python -m app.seed

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The services will be accessible at:
* **Frontend Web App:** `http://localhost:5173`
* **FastAPI Interactive Docs:** `http://localhost:8000/docs`
* **Health Endpoint:** `http://localhost:8000/health/detailed`

---

## 🔐 Default Demo Credentials

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@ledgerpilot.dev` | `Admin@123` | Full access, Kill switch, Demo resets, User management |
| **Finance Manager** | `manager@ledgerpilot.dev` | `Manager@123` | Policy approvals, Exception override, Controller runs |
| **Finance Analyst** | `analyst@ledgerpilot.dev` | `Analyst@123` | Exception review, Investigation trigger, Copilot |
| **Viewer** | `viewer@ledgerpilot.dev` | `Viewer@123` | Read-only access to dashboards, reports, and logs |

---

## 📡 API Endpoint Overview

| Module | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/v1/auth/login` | JWT authentication and token issuance |
| **Reconciliation** | `POST` | `/api/v1/reconciliation/run` | Execute multi-source reconciliation batch |
| **Exceptions** | `GET` | `/api/v1/exceptions` | Filter and paginate detected discrepancies |
| **Intelligence** | `POST` | `/api/v1/intelligence/classify` | ML exception classification & anomaly score |
| **Investigations**| `POST` | `/api/v1/investigations/{id}/start` | Trigger LangGraph AI causal investigation |
| **Controller** | `POST` | `/api/v1/controller/runs` | Execute autonomous controller decision cycle |
| **Approvals** | `POST` | `/api/v1/approvals/{id}/approve` | Manager dual-key sign-off for actions |
| **Actions** | `POST` | `/api/v1/actions/{id}/rollback` | Safe rollback of executed actions |
| **Evaluation** | `GET` | `/api/v1/evaluation/summary` | Retrieve latest ground-truth benchmark metrics |
| **Simulation** | `POST` | `/api/v1/simulation/run/{scenario}` | Run one of the 9 failure injection scenarios |
| **Demo** | `POST` | `/api/v1/demo/preset/{id}` | Load demonstration scenario presets (A/B/C/D) |
| **Health** | `GET` | `/health/detailed` | Real-time health status of DB, Redis, ML & LLM |

---

## 👥 Demo Presets for Presentations

Access these via the API or Frontend Settings:
* **Preset A (Safe Automation):** High volume of safe fee variances demonstrating autonomous auto-resolution.
* **Preset B (Mixed Operations):** Balanced distribution across all exception types demonstrating multi-path routing.
* **Preset C (High Risk / Escalations):** High-value mismatches and missing invoices demonstrating approval gates.
* **Preset D (Failure & Recovery):** Active contradictions triggering circuit breakers and fallback modes.

---


