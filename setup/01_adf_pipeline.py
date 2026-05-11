"""
ADF Pipeline Setup — HealthFlow AI
Creates linked services, datasets, pipelines, triggers, and runs ingestion.
"""

import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from azure.identity import ClientSecretCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.datafactory.models import (
    LinkedServiceResource,
    HttpLinkedService,
    AzureBlobFSLinkedService,
    SecureString,
    DatasetResource,
    HttpDataset,
    AzureBlobFSDataset,
    TextFormat,
    LinkedServiceReference,
    PipelineResource,
    CopyActivity,
    HttpSource,
    AzureBlobFSSink,
    DatasetReference,
    TriggerResource,
    ScheduleTrigger,
    ScheduleTriggerRecurrence,
    TriggerPipelineReference,
    PipelineReference,
    CreateRunResponse,
)

load_dotenv()

# ── Credentials ──────────────────────────────────────────────────────────────
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP  = os.getenv("AZURE_RESOURCE_GROUP")
TENANT_ID       = os.getenv("AZURE_TENANT_ID")
CLIENT_ID       = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET   = os.getenv("AZURE_CLIENT_SECRET")
ADF_NAME        = os.getenv("ADF_NAME")
STORAGE_ACCOUNT = os.getenv("STORAGE_ACCOUNT_NAME")
STORAGE_KEY     = os.getenv("STORAGE_ACCOUNT_KEY")
SOURCE_URL      = os.getenv("SOURCE_URL")


def get_client() -> DataFactoryManagementClient:
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    return DataFactoryManagementClient(credential, SUBSCRIPTION_ID)


# ── Step 1: Linked Services ───────────────────────────────────────────────────

def create_http_linked_service(client: DataFactoryManagementClient) -> None:
    print("  Creating HTTP linked service …")
    ls = LinkedServiceResource(
        properties=HttpLinkedService(
            url="https://raw.githubusercontent.com",
            enable_server_certificate_validation=True,
            authentication_type="Anonymous",
        )
    )
    client.linked_services.create_or_update(
        RESOURCE_GROUP, ADF_NAME, "HttpSourceService", ls
    )
    print("  ✓ HttpSourceService created")


def create_adls_linked_service(client: DataFactoryManagementClient) -> None:
    print("  Creating ADLS Gen2 linked service …")
    ls = LinkedServiceResource(
        properties=AzureBlobFSLinkedService(
            url=f"https://{STORAGE_ACCOUNT}.dfs.core.windows.net",
            account_key=SecureString(value=STORAGE_KEY),
        )
    )
    client.linked_services.create_or_update(
        RESOURCE_GROUP, ADF_NAME, "ADLSGen2Service", ls
    )
    print("  ✓ ADLSGen2Service created")


# ── Step 2: Datasets ──────────────────────────────────────────────────────────

def create_source_dataset(client: DataFactoryManagementClient) -> None:
    print("  Creating source dataset …")
    ds = DatasetResource(
        properties=HttpDataset(
            linked_service_name=LinkedServiceReference(
                type="LinkedServiceReference",
                reference_name="HttpSourceService"
            ),
            format=TextFormat(
                column_delimiter=",",
                row_delimiter="\n",
                first_row_as_header=True,
            ),
            relative_url="/nishant-2211/healthflow-ai/main/data/raw/healthcare_dataset.csv",
            request_method="GET",
        )
    )
    client.datasets.create_or_update(
        RESOURCE_GROUP, ADF_NAME, "HealthcareSourceCSV", ds
    )
    print("  ✓ HealthcareSourceCSV dataset created")


def create_sink_dataset(client: DataFactoryManagementClient) -> None:
    print("  Creating sink dataset …")
    ds = DatasetResource(
        properties=AzureBlobFSDataset(
            linked_service_name=LinkedServiceReference(
                type="LinkedServiceReference",
                reference_name="ADLSGen2Service"
            ),
            format=TextFormat(
                column_delimiter=",",
                row_delimiter="\n",
                first_row_as_header=True,
            ),
            folder_path="raw",
            file_name="healthcare_dataset.csv",
        )
    )
    client.datasets.create_or_update(
        RESOURCE_GROUP, ADF_NAME, "HealthcareSinkCSV", ds
    )
    print("  ✓ HealthcareSinkCSV dataset created")


# ── Step 3: Copy Pipeline ─────────────────────────────────────────────────────

def create_ingestion_pipeline(client: DataFactoryManagementClient) -> None:
    print("  Creating HealthcareIngestionPipeline …")
    copy_activity = CopyActivity(
        name="CopyHealthcareData",
        source=HttpSource(http_request_timeout="00:01:40"),
        sink=AzureBlobFSSink(),
        inputs=[DatasetReference(type="DatasetReference", reference_name="HealthcareSourceCSV")],
        outputs=[DatasetReference(type="DatasetReference", reference_name="HealthcareSinkCSV")],
    )
    pipeline = PipelineResource(activities=[copy_activity])
    client.pipelines.create_or_update(
        RESOURCE_GROUP, ADF_NAME, "HealthcareIngestionPipeline", pipeline
    )
    print("  ✓ HealthcareIngestionPipeline created")


# ── Step 4: Schedule Trigger ──────────────────────────────────────────────────

def create_daily_trigger(client: DataFactoryManagementClient) -> None:
    print("  Creating DailyIngestionTrigger …")
    start_time = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)

    trigger = TriggerResource(
        properties=ScheduleTrigger(
            recurrence=ScheduleTriggerRecurrence(
                frequency="Day",
                interval=1,
                start_time=start_time,
            ),
            pipelines=[
                TriggerPipelineReference(
                    pipeline_reference=PipelineReference(
                        type="PipelineReference",
                        reference_name="HealthcareIngestionPipeline"
                    )
                )
            ],
        )
    )
    client.triggers.create_or_update(
        RESOURCE_GROUP, ADF_NAME, "DailyIngestionTrigger", trigger
    )
    # Activate the trigger
    client.triggers.begin_start(
        RESOURCE_GROUP, ADF_NAME, "DailyIngestionTrigger"
    ).result()
    print("  ✓ DailyIngestionTrigger created and started")


# ── Step 5: Incremental Pipeline ──────────────────────────────────────────────

def create_incremental_pipeline(client: DataFactoryManagementClient) -> None:
    """
    Copies only files modified after a LastModified watermark.
    Uses the modifiedDatetimeStart/End filter on the HTTP source.
    In production the watermark would be read from a control table.
    """
    print("  Creating IncrementalIngestionPipeline …")

    # Watermark: last 24 h as a simple default
    watermark = datetime.now(timezone.utc) - timedelta(hours=24)

    copy_activity = CopyActivity(
        name="IncrementalCopyHealthcareData",
        source=HttpSource(
            http_request_timeout="00:01:40",
            additional_headers=f"If-Modified-Since: {watermark.strftime('%a, %d %b %Y %H:%M:%S GMT')}",
        ),
        sink=AzureBlobFSSink(),
        inputs=[DatasetReference(type="DatasetReference", reference_name="HealthcareSourceCSV")],
        outputs=[DatasetReference(type="DatasetReference", reference_name="HealthcareSinkCSV")],
    )
    pipeline = PipelineResource(activities=[copy_activity])
    client.pipelines.create_or_update(
        RESOURCE_GROUP, ADF_NAME, "IncrementalIngestionPipeline", pipeline
    )
    print("  ✓ IncrementalIngestionPipeline created")


# ── Step 6: Run & Monitor ─────────────────────────────────────────────────────

def run_and_monitor(client: DataFactoryManagementClient) -> str:
    import time

    print("  Triggering HealthcareIngestionPipeline …")
    run: CreateRunResponse = client.pipelines.create_run(
        RESOURCE_GROUP, ADF_NAME, "HealthcareIngestionPipeline"
    )
    run_id = run.run_id
    print(f"  Pipeline run ID: {run_id}")

    while True:
        run_status = client.pipeline_runs.get(RESOURCE_GROUP, ADF_NAME, run_id)
        status = run_status.status
        print(f"  Status: {status}")
        if status in ("Succeeded", "Failed", "Cancelled"):
            break
        time.sleep(15)

    if status != "Succeeded":
        raise RuntimeError(f"Pipeline run ended with status: {status}")

    print("  ✓ Pipeline completed successfully")
    return run_id


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main() -> str:
    """Run all ADF setup steps. Returns the pipeline run_id."""
    print("\n════ ADF Pipeline Setup ════")
    client = get_client()

    print("\n[Step 1] Linked Services")
    create_http_linked_service(client)
    create_adls_linked_service(client)

    print("\n[Step 2] Datasets")
    create_source_dataset(client)
    create_sink_dataset(client)

    print("\n[Step 3] Ingestion Pipeline")
    create_ingestion_pipeline(client)

    print("\n[Step 4] Daily Trigger")
    create_daily_trigger(client)

    print("\n[Step 5] Incremental Pipeline")
    create_incremental_pipeline(client)

    print("\n[Step 6] Run & Monitor")
    run_id = run_and_monitor(client)

    print("\n✅ ADF Pipeline created and executed\n")
    return run_id


if __name__ == "__main__":
    main()
