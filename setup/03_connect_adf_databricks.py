"""
ADF ↔ Databricks End-to-End Connector — HealthFlow AI
Creates an ADF pipeline that:
  1. Runs the CSV ingestion (HealthcareIngestionPipeline).
  2. On success → fires the Databricks job via a web activity webhook.
"""

import os
import time
from dotenv import load_dotenv

from azure.identity import ClientSecretCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.datafactory.models import (
    PipelineResource,
    ExecutePipelineActivity,
    PipelineReference,
    WebActivity,
    ActivityDependency,
    DependencyCondition,
)

load_dotenv()

# ── Credentials ──────────────────────────────────────────────────────────────
SUBSCRIPTION_ID   = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP    = os.getenv("AZURE_RESOURCE_GROUP")
TENANT_ID         = os.getenv("AZURE_TENANT_ID")
CLIENT_ID         = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET     = os.getenv("AZURE_CLIENT_SECRET")
ADF_NAME          = os.getenv("ADF_NAME")
DATABRICKS_HOST   = os.getenv("DATABRICKS_HOST", "").rstrip("/")
DATABRICKS_TOKEN  = os.getenv("DATABRICKS_TOKEN", "").strip("'\"")

E2E_PIPELINE_NAME = "EndToEnd_ADF_Databricks_Pipeline"


def get_adf_client() -> DataFactoryManagementClient:
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    return DataFactoryManagementClient(credential, SUBSCRIPTION_ID)


def get_databricks_job_id() -> int:
    """Fetch the job_id of the HealthFlow-Pipeline-Job from Databricks REST API."""
    import requests

    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}
    url = f"{DATABRICKS_HOST}/api/2.1/jobs/list"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    jobs = resp.json().get("jobs", [])
    for job in jobs:
        if job.get("settings", {}).get("name") == "HealthFlow-Pipeline-Job":
            return int(job["job_id"])
    raise ValueError(
        "HealthFlow-Pipeline-Job not found in Databricks. "
        "Run 02_databricks_setup.py first."
    )


def create_e2e_pipeline(
    client: DataFactoryManagementClient, job_id: int
) -> None:
    print(f"  Creating {E2E_PIPELINE_NAME} (job_id={job_id}) …")

    # Activity 1 — run the existing ADF ingestion pipeline
    ingest_activity = ExecutePipelineActivity(
        name="RunIngestionPipeline",
        pipeline=PipelineReference(type="PipelineReference", reference_name="HealthcareIngestionPipeline"),
        wait_on_completion=True,
    )

    # Activity 2 — trigger the Databricks job via REST webhook
    # Runs only after the ingestion pipeline succeeds.
    # Bearer token is passed as a plain header; for production, move it to Key Vault.
    import json
    databricks_webhook = WebActivity(
        name="TriggerDatabricksJob",
        method="POST",
        url=f"{DATABRICKS_HOST}/api/2.1/jobs/run-now",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        },
        body=json.dumps({"job_id": job_id}),
        depends_on=[
            ActivityDependency(
                activity="RunIngestionPipeline",
                dependency_conditions=[DependencyCondition.SUCCEEDED],
            )
        ],
    )

    pipeline = PipelineResource(activities=[ingest_activity, databricks_webhook])
    client.pipelines.create_or_update(
        RESOURCE_GROUP, ADF_NAME, E2E_PIPELINE_NAME, pipeline
    )
    print(f"  ✓ {E2E_PIPELINE_NAME} created")


def run_and_monitor_e2e(client: DataFactoryManagementClient) -> None:
    print(f"  Triggering {E2E_PIPELINE_NAME} …")
    run = client.pipelines.create_run(
        RESOURCE_GROUP, ADF_NAME, E2E_PIPELINE_NAME
    )
    run_id = run.run_id
    print(f"  Run ID: {run_id}")

    while True:
        status = client.pipeline_runs.get(
            RESOURCE_GROUP, ADF_NAME, run_id
        ).status
        print(f"  Status: {status}")
        if status in ("Succeeded", "Failed", "Cancelled"):
            break
        time.sleep(15)

    if status != "Succeeded":
        # Fetch activity-level detail for debugging
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        runs = client.activity_runs.query_by_pipeline_run(
            RESOURCE_GROUP,
            ADF_NAME,
            run_id,
            filter_parameters={
                "lastUpdatedAfter": (now - timedelta(hours=1)).isoformat(),
                "lastUpdatedBefore": now.isoformat(),
            },
        )
        for r in runs.value:
            print(f"  Activity [{r.activity_name}] → {r.status}: {r.error}")
        raise RuntimeError(f"End-to-end pipeline ended with status: {status}")

    print("  ✓ End-to-end pipeline completed successfully")


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n════ ADF ↔ Databricks Connector ════")

    print("\n[Step 1] Fetch Databricks job ID")
    job_id = get_databricks_job_id()
    print(f"  Found job_id: {job_id}")

    adf_client = get_adf_client()

    print("\n[Step 2] Create End-to-End Pipeline")
    create_e2e_pipeline(adf_client, job_id)

    print("\n[Step 3] Run & Monitor")
    run_and_monitor_e2e(adf_client)

    print("\n✅ Full end-to-end automation pipeline created and executed\n")


if __name__ == "__main__":
    main()
