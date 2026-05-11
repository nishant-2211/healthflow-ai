<div align="center">

# 🏥 HealthFlow AI

### Enterprise Healthcare Data Pipeline + AI Insights Dashboard

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.57+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Azure](https://img.shields.io/badge/Azure_Data_Factory-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com)
[![Databricks](https://img.shields.io/badge/Databricks-FF3621?style=for-the-badge&logo=databricks&logoColor=white)](https://databricks.com)
[![Claude AI](https://img.shields.io/badge/Claude_AI-D97706?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)
[![Delta Lake](https://img.shields.io/badge/Delta_Lake-003366?style=for-the-badge&logo=apachespark&logoColor=white)](https://delta.io)

An end-to-end enterprise healthcare data pipeline that ingests, transforms, and surfaces insights from **55,500 patient records** — fully automated from raw CSV to interactive AI-powered dashboard using Azure Data Factory, Databricks Medallion Architecture, and Anthropic Claude.

</div>

---

## 🎬 Demo

![HealthFlow AI Demo](demo.gif)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HealthFlow AI — Data Pipeline                        │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐     ┌──────────────────┐     ┌────────────────────┐
  │  GitHub  │────▶│  Azure Data      │────▶│  Azure Data Lake   │
  │  CSV     │     │  Factory (ADF)   │     │  Storage Gen2      │
  └──────────┘     └──────────────────┘     └────────┬───────────┘
                        Daily + Incremental           │
                                                      ▼
                   ┌──────────────────────────────────────────────┐
                   │              Databricks Workspace             │
                   │                                              │
                   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
                   │  │  Bronze  │─▶│  Silver  │─▶│   Gold   │  │
                   │  │  55,500  │  │  54,966  │  │Aggregated│  │
                   │  │  records │  │  records │  │  tables  │  │
                   │  └──────────┘  └──────────┘  └────┬─────┘  │
                   │   Delta Lake    Delta Lake         │         │
                   └───────────────────────────────────┼─────────┘
                                                       │
                                          ┌────────────▼──────────────┐
                                          │      Claude AI (Anthropic) │
                                          │   Healthcare Insights       │
                                          └────────────┬───────────────┘
                                                       │
                                          ┌────────────▼───────────────┐
                                          │   Streamlit Dashboard       │
                                          │   (Interactive Analytics)   │
                                          └────────────────────────────┘
```

---

## ✅ Features

- [x] **Automated ingestion** — Azure Data Factory pulls CSV from GitHub to ADLS Gen2 on a daily schedule
- [x] **Incremental loading** — `IncrementalIngestionPipeline` copies only new/changed records, avoiding full reloads
- [x] **Medallion Architecture** — Bronze → Silver → Gold with Delta Lake for ACID-compliant storage
- [x] **Data quality enforcement** — Silver layer fixes names, standardises dates, computes length of stay, and deduplicates
- [x] **Multi-dimensional aggregations** — Gold tables for conditions, hospital performance, and demographics
- [x] **AI-generated insights** — Claude analyses Gold data and writes a structured healthcare report stored back in Delta
- [x] **Orchestrated Databricks Job** — `HealthFlow-Pipeline-Job` runs all four notebooks sequentially with dependency tracking
- [x] **One-command setup** — `python3 setup/run_all.py` provisions ADF, uploads notebooks, creates the Databricks job, and wires up the end-to-end pipeline
- [x] **Interactive dashboard** — Streamlit app with live Databricks SQL queries, five KPI cards, four analytical tabs, and a sidebar pipeline-status panel

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Orchestration** | Azure Data Factory (ADF) |
| **Cloud Storage** | Azure Data Lake Storage Gen2 |
| **Processing Engine** | Databricks + PySpark |
| **Architecture Pattern** | Medallion (Bronze / Silver / Gold) |
| **Storage Format** | Delta Lake |
| **AI / LLM** | Anthropic Claude API |
| **Dashboard** | Streamlit |
| **Language** | Python 3.12 |
| **Package Manager** | UV |
| **Version Control** | GitHub |

---

## 🥉🥈🥇 Medallion Architecture

### Bronze — Raw Ingestion
Stores the exact data as delivered by ADF from ADLS Gen2. No transformations applied — acts as the immutable source of truth.

| Table | Records |
|---|---|
| `healthflow_catalog.bronze.patients_raw` | 55,500 |

### Silver — Cleaned & Enriched
Business-ready data after quality enforcement. Removes 534 duplicate/malformed records and enriches each row.

| Table | Records |
|---|---|
| `healthflow_catalog.silver.patients_clean` | 54,966 |

**Transformations applied:**
- Patient names standardised (title case, whitespace normalised)
- Admission/discharge dates parsed into consistent `yyyy-MM-dd` format
- `length_of_stay` computed from admission → discharge delta
- Duplicates removed based on patient ID + admission date composite key

### Gold — Aggregated Insights
Analytical tables pre-aggregated for fast dashboard queries and AI consumption.

| Table | Purpose |
|---|---|
| `healthflow_catalog.gold.conditions_analysis` | Patient count, avg billing, avg stay per condition |
| `healthflow_catalog.gold.hospital_performance` | Top hospitals ranked by volume and urgency |
| `healthflow_catalog.gold.demographics` | Age group distributions and billing trends |
| `healthflow_catalog.gold.ai_insights` | Claude-generated healthcare report + timestamp |

---

## 📁 Project Structure

```
healthflow-ai/
├── app.py                              # Streamlit dashboard (main entry point)
├── pyproject.toml                      # Project metadata + dependencies (UV)
├── .env                                # Environment variables (not committed)
│
├── setup/                              # One-time infrastructure provisioning
│   ├── run_all.py                      # Master orchestrator — run this first
│   ├── 01_adf_pipeline.py             # Creates ADF pipelines + linked services
│   ├── 02_databricks_setup.py         # Uploads notebooks + creates Databricks job
│   ├── 03_connect_adf_databricks.py   # Wires ADF trigger → Databricks job
│   └── add_secret.py                   # Adds secrets to Databricks secret scope
│
├── databricks/                         # PySpark notebooks (uploaded by setup)
│   ├── 01_bronze_ingestion.ipynb      # ADLS Gen2 → Bronze Delta table
│   ├── 02_silver_transformation.ipynb # Cleaning, dedup, enrichment
│   ├── 03_gold_aggregations.ipynb     # Analytical aggregations
│   └── 04_ai_insights.ipynb           # Claude AI report generation
│
├── adf/
│   └── pipeline_config.json            # ADF pipeline definitions
│
├── data/
│   └── raw/healthcare_dataset.csv      # Source dataset (55,500 records)
│
├── src/
│   ├── ai_insights.py                  # Claude API integration helpers
│   ├── pipeline.py                     # Pipeline utility functions
│   └── visualizer.py                   # Chart helpers
│
└── notebooks/
    └── healthflow.ipynb                # Exploratory notebook
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) package manager
- Azure subscription with:
  - Azure Data Factory instance
  - Azure Data Lake Storage Gen2 account
  - Service Principal with Contributor access
- Databricks workspace (Standard or Premium tier)
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone https://github.com/nishant-2211/healthflow-ai.git
cd healthflow-ai

# Install dependencies with UV
uv sync

# Activate the virtual environment
source .venv/bin/activate    # macOS / Linux
# .venv\Scripts\activate     # Windows
```

### Environment Variables

Create a `.env` file in the project root (use the template below):

```env
# ── Azure Credentials ──────────────────────────────
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group

# ── Azure Data Factory ─────────────────────────────
ADF_NAME=healthflow-adf
ADF_LOCATION=eastus

# ── Azure Data Lake Storage Gen2 ───────────────────
STORAGE_ACCOUNT_NAME=healthflowstorage
STORAGE_CONTAINER_NAME=healthdata

# ── Databricks ─────────────────────────────────────
DATABRICKS_HOST=https://adb-xxxxxxxxxxxx.azuredatabricks.net
DATABRICKS_TOKEN=your-databricks-pat-token
DATABRICKS_CLUSTER_ID=your-cluster-id
DATABRICKS_WAREHOUSE_ID=your-sql-warehouse-id

# ── Anthropic Claude AI ────────────────────────────
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### Running Locally

**Step 1 — Provision infrastructure** *(one time only)*

```bash
python3 setup/run_all.py
```

This single command:
1. Creates ADF pipelines (`HealthcareIngestionPipeline` + `IncrementalIngestionPipeline`)
2. Uploads all four Databricks notebooks to the workspace
3. Creates `HealthFlow-Pipeline-Job` in Databricks with sequential task dependencies
4. Wires up the end-to-end ADF → Databricks trigger pipeline

**Step 2 — Launch the dashboard**

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 🔐 Environment Variables Reference

| Variable | Description | Example |
|---|---|---|
| `AZURE_TENANT_ID` | Azure Active Directory tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_CLIENT_ID` | Service Principal application ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_CLIENT_SECRET` | Service Principal secret | `your~secret~value` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_RESOURCE_GROUP` | Resource group containing ADF + storage | `healthflow-rg` |
| `ADF_NAME` | Azure Data Factory instance name | `healthflow-adf` |
| `ADF_LOCATION` | Azure region | `eastus` |
| `STORAGE_ACCOUNT_NAME` | ADLS Gen2 account name | `healthflowstorage` |
| `STORAGE_CONTAINER_NAME` | Blob container name | `healthdata` |
| `DATABRICKS_HOST` | Databricks workspace URL | `https://adb-xxx.azuredatabricks.net` |
| `DATABRICKS_TOKEN` | Personal access token | `dapi...` |
| `DATABRICKS_CLUSTER_ID` | Compute cluster ID | `0101-xxxxxx-xxxxxxxx` |
| `DATABRICKS_WAREHOUSE_ID` | SQL warehouse ID (used by Streamlit) | `xxxxxxxxxxxxxxxx` |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | `sk-ant-...` |

---

## ⚡ Databricks Setup

### Adding Secrets

Store sensitive values in a Databricks secret scope so notebooks can read credentials at runtime without any hardcoding:

```bash
# Create the secret scope (one time)
databricks secrets create-scope --scope healthflow-scope

# Populate secrets via the helper script
python3 setup/add_secret.py
```

### Running the Pipeline Manually

Trigger the full pipeline from the Databricks UI, or via the CLI:

```bash
databricks jobs run-now --job-id <HealthFlow-Pipeline-Job-ID>
```

Or run notebooks individually in order from the Databricks workspace:

```
01_bronze_ingestion      →   02_silver_transformation
    →   03_gold_aggregations   →   04_ai_insights
```

### Databricks Job — Task Sequence

`HealthFlow-Pipeline-Job` orchestrates four tasks with explicit sequential dependencies:

```
Bronze_Ingestion
      │
      ▼
Silver_Transform
      │
      ▼
Gold_Aggregations
      │
      ▼
AI_Insights   ← calls Claude API, writes report to gold.ai_insights
```

---

## 🔄 ADF Pipeline Configuration

Two pipelines handle data ingestion:

| Pipeline | Trigger | Behaviour |
|---|---|---|
| `HealthcareIngestionPipeline` | Daily at midnight UTC | Full copy of the healthcare CSV from GitHub to ADLS Gen2 |
| `IncrementalIngestionPipeline` | On-demand / event-driven | Copies only records modified since the last successful run |

ADF uses an **HTTP Linked Service** to pull the source CSV directly from GitHub, and a **ADLS Gen2 Linked Service** (authenticated via Service Principal) as the sink. No intermediate compute is required — ADF handles the copy activity natively.

---

## 📊 Dataset Overview

| Metric | Value |
|---|---|
| Total patient records | 55,500 |
| Clean records after Silver transform | 54,966 |
| Medical conditions covered | 6 |
| Average billing amount | $25,544 |
| Average length of stay | 15.5 days |
| Urgent admission rate | 33.5% |

**Medical Conditions:**
`Arthritis` · `Diabetes` · `Hypertension` · `Obesity` · `Cancer` · `Asthma`

---

## ☁️ Deployment Note

This project is designed for **local development and portfolio demonstration**. Running a full Databricks cluster continuously incurs significant cloud cost. The recommended workflow:

1. Run `python3 setup/run_all.py` **once** to provision all infrastructure
2. Trigger the Databricks job when you need fresh data
3. Run `streamlit run app.py` locally — it queries the Databricks SQL Warehouse on demand
4. **Terminate the Databricks cluster** when not in use to minimise spend

For production deployment, containerise the Streamlit app (Docker) and host it on Azure App Service or AKS, with the Databricks job running on a scheduled cluster policy with auto-termination.

---

## 🧠 What I Learned

1. **Medallion Architecture in practice** — Separating raw, clean, and aggregated layers forces you to think about schema evolution, idempotency, and data quality at each boundary — not as an afterthought at the end.

2. **ADF as a declarative orchestrator** — Pipeline-as-JSON makes infrastructure reproducible and version-controllable. The incremental copy pattern using watermark tables was a meaningful improvement over naive full reloads.

3. **Delta Lake for reliable pipelines** — ACID transactions and time-travel made it safe to re-run notebooks mid-development without corrupting downstream tables. Upserts via `MERGE INTO` replaced fragile overwrite logic.

4. **LLMs as analytical co-processors** — Calling Claude on pre-aggregated Gold data, rather than raw records, produces sharper and more accurate insights. The prompt structure matters as much as the model choice.

5. **End-to-end data engineering vs. isolated scripts** — Wiring ADF → ADLS → Databricks → Claude → Streamlit exposed how failures propagate across system boundaries. Defensive error handling, connection retries, and graceful fallbacks in the dashboard made the difference between a demo that works once and one that holds up under real conditions.

---

## 👤 Author

**Nishant Garg**  
MCA Graduate — The NorthCap University

[![LinkedIn](https://img.shields.io/badge/LinkedIn-nishant2211-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/nishant2211)
[![GitHub](https://img.shields.io/badge/GitHub-nishant--2211-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/nishant-2211)

---

<div align="center">

Built with Azure · Databricks · Claude AI · Streamlit

</div>
