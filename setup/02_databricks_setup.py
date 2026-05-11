"""
Databricks Setup — HealthFlow AI
Uploads notebooks to workspace and creates + runs the medallion-layer job.
"""

import os
import base64
import time
from dotenv import load_dotenv

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat, Language
from databricks.sdk.service.jobs import (
    NotebookTask,
    Task,
    TaskDependency,
    RunLifeCycleState,
    RunResultState,
)

load_dotenv()

# ── Credentials ──────────────────────────────────────────────────────────────
DATABRICKS_HOST       = os.getenv("DATABRICKS_HOST", "").rstrip("/")
# Strip stray quotes that may appear in .env value
DATABRICKS_TOKEN      = os.getenv("DATABRICKS_TOKEN", "").strip("'\"")
CLUSTER_ID            = os.getenv("DATABRICKS_CLUSTER_ID")
STORAGE_ACCOUNT       = os.getenv("STORAGE_ACCOUNT_NAME")
ANTHROPIC_API_KEY     = os.getenv("ANTHROPIC_API_KEY")

WORKSPACE_FOLDER = "/HealthFlow"
JOB_NAME         = "HealthFlow-Pipeline-Job"


def get_client() -> WorkspaceClient:
    return WorkspaceClient(host=DATABRICKS_HOST, token=DATABRICKS_TOKEN)


# ── Notebook content ──────────────────────────────────────────────────────────

BRONZE_NOTEBOOK = f"""# Databricks notebook source
# MAGIC %md ## Bronze Layer — Raw Ingestion

# COMMAND ----------
from pyspark.sql import functions as F

storage_account = "healthflowstorage"
container = "raw"

spark.conf.set(
    f"fs.azure.account.key.{{storage_account}}.blob.core.windows.net",
    dbutils.secrets.get(scope="healthflow", key="storage-key")
)

df = spark.read.csv(
    f"wasbs://{{container}}@{{storage_account}}.blob.core.windows.net/healthcare_dataset.csv",
    header=True,
    inferSchema=True,
)

# Rename columns with spaces to underscore names (Delta Lake requirement)
bronze_df = df \
    .withColumnRenamed("Blood Type",        "blood_type") \
    .withColumnRenamed("Medical Condition", "medical_condition") \
    .withColumnRenamed("Date of Admission", "date_of_admission") \
    .withColumnRenamed("Insurance Provider","insurance_provider") \
    .withColumnRenamed("Billing Amount",    "billing_amount") \
    .withColumnRenamed("Room Number",       "room_number") \
    .withColumnRenamed("Admission Type",    "admission_type") \
    .withColumnRenamed("Discharge Date",    "discharge_date") \
    .withColumnRenamed("Test Results",      "test_results") \
    .withColumn("ingestion_timestamp",      F.current_timestamp()) \
    .withColumn("source_file",              F.lit("healthcare_dataset.csv"))

bronze_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(
        "healthflow_catalog.bronze.patients_raw"
    )

print(f"✅ Bronze: {{bronze_df.count():,}} records")
"""

SILVER_NOTEBOOK = """# Databricks notebook source
# MAGIC %md ## Silver Layer — Cleansed & Typed Data

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType

bronze_df = spark.table("healthflow_catalog.bronze.patients_raw")

silver_df = (
    bronze_df
    .withColumn("name",               F.initcap(F.col("Name")))
    .withColumn("age",                F.col("Age").cast(IntegerType()))
    .withColumn("gender",             F.lower(F.col("Gender")))
    .withColumn("blood_type",         F.col("blood_type"))
    .withColumn("medical_condition",  F.col("medical_condition"))
    .withColumn("admission_date",     F.to_date(F.col("date_of_admission")))
    .withColumn("discharge_date",     F.to_date(F.col("discharge_date")))
    .withColumn("length_of_stay",     F.datediff(F.col("discharge_date"), F.col("date_of_admission")))
    .withColumn("doctor",             F.initcap(F.col("Doctor")))
    .withColumn("hospital",           F.col("Hospital"))
    .withColumn("insurance_provider", F.col("insurance_provider"))
    .withColumn("billing_amount",     F.round(F.col("billing_amount"), 2))
    .withColumn("room_number",        F.col("room_number").cast(IntegerType()))
    .withColumn("admission_type",     F.col("admission_type"))
    .withColumn("medication",         F.col("Medication"))
    .withColumn("test_results",       F.col("test_results"))
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .select(
        "name", "age", "gender", "blood_type", "medical_condition",
        "admission_date", "discharge_date", "length_of_stay", "doctor",
        "hospital", "insurance_provider", "billing_amount", "room_number",
        "admission_type", "medication", "test_results", "ingestion_timestamp",
    )
    .dropDuplicates()
    .dropna()
)

silver_df.write.format("delta").mode("overwrite").saveAsTable(
    "healthflow_catalog.silver.patients_clean"
)

print(f"Silver: {silver_df.count():,} records after cleansing")
"""

GOLD_NOTEBOOK = """# Databricks notebook source
# MAGIC %md ## Gold Layer — Business Aggregations

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.functions import when

silver_df = spark.table("healthflow_catalog.silver.patients_clean")

# ── Conditions Analysis ──────────────────────────────────────────────────────
conditions = silver_df.groupBy("medical_condition").agg(
    F.count("*").alias("patient_count"),
    F.round(F.avg("billing_amount"), 2).alias("avg_billing"),
    F.round(F.avg("length_of_stay"), 1).alias("avg_stay_days"),
)
conditions.write.format("delta").mode("overwrite").saveAsTable(
    "healthflow_catalog.gold.conditions_analysis"
)

# ── Hospital Performance ─────────────────────────────────────────────────────
hospitals = silver_df.groupBy("hospital").agg(
    F.count("*").alias("total_patients"),
    F.round(F.avg("billing_amount"), 2).alias("avg_billing"),
    F.sum(when(F.col("admission_type") == "Urgent", 1).otherwise(0)).alias("urgent_count"),
)
hospitals.write.format("delta").mode("overwrite").saveAsTable(
    "healthflow_catalog.gold.hospital_performance"
)

# ── Demographics ─────────────────────────────────────────────────────────────
demographics = (
    silver_df
    .withColumn(
        "age_group",
        when(F.col("age") <= 18, "0-18")
        .when(F.col("age") <= 35, "19-35")
        .when(F.col("age") <= 50, "36-50")
        .when(F.col("age") <= 65, "51-65")
        .otherwise("65+"),
    )
    .groupBy("age_group")
    .agg(
        F.count("*").alias("patient_count"),
        F.round(F.avg("billing_amount"), 2).alias("avg_billing"),
    )
)
demographics.write.format("delta").mode("overwrite").saveAsTable(
    "healthflow_catalog.gold.demographics"
)

print("Gold layer complete — conditions, hospitals, demographics written")
"""

AI_INSIGHTS_NOTEBOOK = f"""# Databricks notebook source
# MAGIC %md ## AI Insights — Claude-Powered Healthcare Analysis

# COMMAND ----------
import anthropic
import os
from datetime import datetime
from pyspark.sql import Row

client = anthropic.Anthropic(
    api_key=dbutils.secrets.get(scope="healthflow", key="anthropic-key")
)

# Load gold tables
conditions = spark.table("healthflow_catalog.gold.conditions_analysis").toPandas().to_string()
hospitals  = spark.table("healthflow_catalog.gold.hospital_performance").toPandas().to_string()

# Generate insights with Claude
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1500,
    messages=[{{
        "role": "user",
        "content": f\"\"\"You are a healthcare data analyst.
Analyze this hospital data and be concise:

CONDITIONS DATA:
{{conditions}}

HOSPITAL DATA:
{{hospitals}}

Provide:
1. Top 3 critical insights
2. Billing anomalies
3. Patient risk patterns
4. Actionable recommendations
\"\"\",
    }}],
)

report = response.content[0].text
print(report)

# Persist the report as a Delta table row
report_df = spark.createDataFrame([
    Row(report_text=report, generated_at=datetime.now().isoformat())
])
report_df.write.format("delta").mode("overwrite").saveAsTable(
    "healthflow_catalog.gold.ai_insights"
)

print("\\n✓ AI insights saved to healthflow_catalog.gold.ai_insights")
"""

NOTEBOOKS = [
    ("01_bronze_ingestion",      BRONZE_NOTEBOOK,      Language.PYTHON),
    ("02_silver_transformation", SILVER_NOTEBOOK,      Language.PYTHON),
    ("03_gold_aggregations",     GOLD_NOTEBOOK,        Language.PYTHON),
    ("04_ai_insights",           AI_INSIGHTS_NOTEBOOK, Language.PYTHON),
]


# ── Step 1: Upload Notebooks ──────────────────────────────────────────────────

def upload_notebooks(client: WorkspaceClient) -> None:
    print("  Ensuring workspace folder exists …")
    try:
        client.workspace.mkdirs(path=WORKSPACE_FOLDER)
    except Exception:
        pass  # folder may already exist

    for name, content, language in NOTEBOOKS:
        path = f"{WORKSPACE_FOLDER}/{name}"
        encoded = base64.b64encode(content.encode()).decode()
        print(f"  Uploading {path} …")
        client.workspace.import_(
            path=path,
            format=ImportFormat.SOURCE,
            language=language,
            content=encoded,
            overwrite=True,
        )
        print(f"  ✓ {name} uploaded")


# ── Step 2: Create Job ────────────────────────────────────────────────────────

def create_job(client: WorkspaceClient) -> int:
    print(f"  Creating job '{JOB_NAME}' …")

    tasks = [
        Task(
            task_key="Bronze_Ingestion",
            notebook_task=NotebookTask(
                notebook_path=f"{WORKSPACE_FOLDER}/01_bronze_ingestion"
            ),
            existing_cluster_id=CLUSTER_ID,
        ),
        Task(
            task_key="Silver_Transform",
            notebook_task=NotebookTask(
                notebook_path=f"{WORKSPACE_FOLDER}/02_silver_transformation"
            ),
            existing_cluster_id=CLUSTER_ID,
            depends_on=[TaskDependency(task_key="Bronze_Ingestion")],
        ),
        Task(
            task_key="Gold_Aggregations",
            notebook_task=NotebookTask(
                notebook_path=f"{WORKSPACE_FOLDER}/03_gold_aggregations"
            ),
            existing_cluster_id=CLUSTER_ID,
            depends_on=[TaskDependency(task_key="Silver_Transform")],
        ),
        Task(
            task_key="AI_Insights",
            notebook_task=NotebookTask(
                notebook_path=f"{WORKSPACE_FOLDER}/04_ai_insights"
            ),
            existing_cluster_id=CLUSTER_ID,
            depends_on=[TaskDependency(task_key="Gold_Aggregations")],
        ),
    ]

    job = client.jobs.create(name=JOB_NAME, tasks=tasks)
    print(f"  ✓ Job created — ID: {job.job_id}")
    return job.job_id


# ── Step 3: Run & Monitor ─────────────────────────────────────────────────────

def run_and_monitor(client: WorkspaceClient, job_id: int) -> None:
    print(f"  Triggering job {job_id} …")
    run = client.jobs.run_now(job_id=job_id)
    run_id = run.run_id
    print(f"  Job run ID: {run_id}")

    while True:
        run_state = client.jobs.get_run(run_id=run_id)
        lifecycle = run_state.state.life_cycle_state
        print(f"  Lifecycle: {lifecycle}")

        if lifecycle in (
            RunLifeCycleState.TERMINATED,
            RunLifeCycleState.SKIPPED,
            RunLifeCycleState.INTERNAL_ERROR,
        ):
            result = run_state.state.result_state
            # Print per-task status
            for task in (run_state.tasks or []):
                t_state = task.state
                print(
                    f"    Task [{task.task_key}] → "
                    f"{t_state.life_cycle_state} / {t_state.result_state}"
                )
            if result != RunResultState.SUCCESS:
                raise RuntimeError(f"Job run failed: {run_state.state.state_message}")
            break

        time.sleep(20)

    print("  ✓ All tasks completed successfully")


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main() -> int:
    """Upload notebooks, create job, run it. Returns job_id."""
    print("\n════ Databricks Setup ════")
    client = get_client()

    print("\n[Step 1] Upload Notebooks")
    upload_notebooks(client)

    print("\n[Step 2] Create Job")
    job_id = create_job(client)

    print("\n[Step 3] Run & Monitor")
    run_and_monitor(client, job_id)

    print("\n✅ Databricks notebooks uploaded and job completed\n")
    return job_id


if __name__ == "__main__":
    main()
