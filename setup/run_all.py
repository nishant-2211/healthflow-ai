"""
HealthFlow AI — Master Orchestrator
Runs the full pipeline setup in sequence and prints a final status report.

Usage:
    python setup/run_all.py
"""

import os
import sys
import traceback
from datetime import datetime

from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from azure.mgmt.datafactory import DataFactoryManagementClient


def _adf_client() -> DataFactoryManagementClient:
    load_dotenv()
    credential = ClientSecretCredential(
        tenant_id=os.getenv("AZURE_TENANT_ID"),
        client_id=os.getenv("AZURE_CLIENT_ID"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET"),
    )
    return DataFactoryManagementClient(credential, os.getenv("AZURE_SUBSCRIPTION_ID"))


def _adf_pipeline_exists(name: str) -> bool:
    try:
        client = _adf_client()
        rg = os.getenv("AZURE_RESOURCE_GROUP")
        adf = os.getenv("ADF_NAME")
        client.pipelines.get(rg, adf, name)
        return True
    except Exception:
        return False


def section(title: str) -> None:
    print(f"\n{'═' * 48}")
    print(f"  {title}")
    print(f"{'═' * 48}")


def check(label: str) -> None:
    print(f"  ✅  {label}")


def fail(label: str, exc: Exception) -> None:
    print(f"  ❌  {label}")
    print(f"      {exc}")


def main() -> None:
    start = datetime.now()
    print("\n" + "═" * 48)
    print("  HealthFlow AI — Pipeline Orchestrator")
    print(f"  Started: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 48)

    results: dict[str, bool] = {}

    # ── Step 1: ADF Pipeline ─────────────────────────────────────────────────
    section("Step 1 — ADF Pipeline")
    if _adf_pipeline_exists("HealthcareIngestionPipeline"):
        print("  ADF Pipeline already exists ✅")
        results["ADF Pipeline created"] = True
    else:
        try:
            from setup import adf_pipeline as adf_mod  # type: ignore[import]
            adf_mod.main()
            results["ADF Pipeline created"] = True
            check("ADF Pipeline created")
        except Exception as exc:
            results["ADF Pipeline created"] = False
            fail("ADF Pipeline created", exc)
            traceback.print_exc()

    # ── Step 2: Databricks Notebooks + Job ───────────────────────────────────
    section("Step 2 — Databricks Notebooks + Job")
    try:
        from setup import databricks_setup as db_mod  # type: ignore[import]
        db_mod.main()
        results["Databricks notebooks uploaded"] = True
        results["Databricks job created"] = True
        check("Databricks notebooks uploaded")
        check("Databricks job created")
    except Exception as exc:
        results["Databricks notebooks uploaded"] = False
        results["Databricks job created"] = False
        fail("Databricks setup", exc)
        traceback.print_exc()

    # ── Step 3: ADF ↔ Databricks Connector ──────────────────────────────────
    section("Step 3 — ADF ↔ Databricks End-to-End Connector")
    if _adf_pipeline_exists("EndToEnd_ADF_Databricks_Pipeline"):
        print("  End-to-End Pipeline already exists ✅")
        results["Pipeline triggered"] = True
    else:
        try:
            from setup import connect_adf_databricks as conn_mod  # type: ignore[import]
            conn_mod.main()
            results["Pipeline triggered"] = True
            check("Pipeline triggered (end-to-end)")
        except Exception as exc:
            results["Pipeline triggered"] = False
            fail("ADF ↔ Databricks connector", exc)
            traceback.print_exc()

    # ── Final Status Report ──────────────────────────────────────────────────
    elapsed = (datetime.now() - start).seconds
    section("Final Status Report")
    print(f"  Completed in {elapsed}s\n")

    all_ok = True
    report_lines = [
        ("ADF Pipeline created",          "ADF Pipeline created"),
        ("Databricks notebooks uploaded",  "Databricks notebooks uploaded"),
        ("Databricks job created",         "Databricks job created"),
        ("Pipeline triggered",             "Pipeline triggered"),
    ]
    for key, label in report_lines:
        ok = results.get(key, False)
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {label}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("  ✅  HealthFlow AI is LIVE")
    else:
        print("  ⚠️   Some steps failed — review errors above")
        sys.exit(1)
    print()


if __name__ == "__main__":
    # Ensure the project root is on the path so `from setup import …` works
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Re-apply module name aliases so the imports inside main() resolve correctly
    import importlib, types

    def _load(alias: str, rel_path: str) -> None:
        """Load a file and register it under two names in sys.modules."""
        spec = importlib.util.spec_from_file_location(
            alias,
            os.path.join(project_root, "setup", rel_path),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[alias] = mod
        # Also register as `setup.<name>` so the from-import in main() works
        sys.modules[f"setup.{alias.split('.')[-1]}"] = mod

    # Pre-register the dotenv load so all sub-modules share env vars
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, ".env"))

    # Register each module
    import importlib.util

    _load("adf_pipeline",          "01_adf_pipeline.py")
    _load("databricks_setup",      "02_databricks_setup.py")
    _load("connect_adf_databricks","03_connect_adf_databricks.py")

    # Make `from setup import X` work
    setup_pkg = types.ModuleType("setup")
    setup_pkg.adf_pipeline           = sys.modules["adf_pipeline"]           # type: ignore[attr-defined]
    setup_pkg.databricks_setup        = sys.modules["databricks_setup"]        # type: ignore[attr-defined]
    setup_pkg.connect_adf_databricks  = sys.modules["connect_adf_databricks"]  # type: ignore[attr-defined]
    sys.modules["setup"] = setup_pkg

    main()
