"""
Add secrets to the Databricks 'healthflow' secret scope.
Run this once before executing the main pipeline.

Usage:
    python setup/add_secret.py
"""

import os
from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient

load_dotenv()

DATABRICKS_HOST  = os.getenv("DATABRICKS_HOST", "").rstrip("/")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "").strip("'\"")
SCOPE            = "healthflow"

client = WorkspaceClient(host=DATABRICKS_HOST, token=DATABRICKS_TOKEN)

# Ensure the secret scope exists
existing_scopes = [s.name for s in client.secrets.list_scopes()]
if SCOPE not in existing_scopes:
    client.secrets.create_scope(scope=SCOPE)
    print(f"✅ Secret scope '{SCOPE}' created")
else:
    print(f"  Scope '{SCOPE}' already exists")

# Anthropic API key
client.secrets.put_secret(
    scope=SCOPE,
    key="anthropic-key",
    string_value=os.getenv("ANTHROPIC_API_KEY"),
)
print("✅ Anthropic key added!")

# Storage account key
client.secrets.put_secret(
    scope=SCOPE,
    key="storage-key",
    string_value=os.getenv("STORAGE_ACCOUNT_KEY"),
)
print("✅ Storage key added!")
