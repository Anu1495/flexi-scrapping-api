# Google Sheets Read API

A small FastAPI service that reads a worksheet range and returns each data row as a JSON object. The first row in the configured range is treated as the column headers.

## Project layout

```text
app/
  api/routes.py          HTTP endpoints
  core/config.py         Environment-based settings
  services/sheets.py     Google Sheets API integration
  main.py                FastAPI application
.env.example             Local settings template
requirements.txt         Python dependencies
```

## Google setup

1. In Google Cloud Console, enable the **Google Sheets API** for the project associated with the service account.
2. Open `google_service_account.json` locally and copy the `client_email` value (do not share the file or commit it).
3. Share the target spreadsheet with that service-account email, with Viewer access.
4. Copy the spreadsheet ID from its URL. For a URL like `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`, the ID is the portion between `/d/` and `/edit`.
5. Set `GOOGLE_SHEETS_SPREADSHEET_ID` and `GOOGLE_SHEETS_RANGE` in `.env`. The range accepts A1 notation, for example `Sheet1!A:Z` or `'Sales Data'!A1:F500`. If you only know the worksheet's numeric `gid` from its URL, use `gid=1051183713!A:Z`; the service resolves the tab name automatically.

The service account file already in the project root is used by default for local development. It is ignored by Git. Never commit or publish it.

## Run locally (Windows PowerShell)

From the project directory:

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`, then replace the spreadsheet ID and range with your values.

4. Start the development server:

   ```powershell
   python -m uvicorn app.main:app --reload
   ```

5. Try these URLs:

   - `http://127.0.0.1:8000/api/v1/health` — health check
   - `http://127.0.0.1:8000/api/v1/sheets/data` — sheet rows as JSON
   - `http://127.0.0.1:8000/docs` — interactive API documentation

Example response:

```json
[
  {"Name": "Ada", "Email": "ada@example.com"},
  {"Name": "Grace", "Email": "grace@example.com"}
]
```

## Deploy to Azure App Service

Create an App Service using a supported Python runtime, deploy this project directory, and set these App Service **Configuration → Application settings**:

- `GOOGLE_SHEETS_SPREADSHEET_ID`: spreadsheet ID
- `GOOGLE_SHEETS_RANGE`: range such as `Sheet1!A:Z`
- `GOOGLE_SERVICE_ACCOUNT_JSON`: the complete contents of the service-account JSON file

App Service application settings are provided to the process as environment variables. Keep the credential setting secret, restrict access to the Azure resource, and do not upload the JSON key file with the deployment. For production, prefer storing credentials in Azure Key Vault and using managed references where available.

Set the App Service startup command to:

```text
gunicorn --bind=0.0.0.0:8000 --timeout 600 -k uvicorn.workers.UvicornWorker app.main:app
```

After deployment, the endpoint is `https://<your-app-name>.azurewebsites.net/api/v1/sheets/data`; interactive docs are at `/docs`.

### GitHub Actions: Azure login reports “No subscriptions found”

If `deploy` fails in `azure/login@v2` with `No subscriptions found`, deployment has not started. The configured identity cannot see an accessible Azure subscription. Check the identity's Azure role assignments, subscription status, and repository secrets; changing application code or retrying without correcting access will not resolve this failure.

The workflow `.github/workflows/master_flexi-rates-api.yml` uses these repository Actions secrets:

| Secret | Required value |
| --- | --- |
| `AZUREAPPSERVICE_CLIENTID_17DE7FBA42634A5990ED9D6351F0E044` | Application (client) ID of the deployment service principal |
| `AZUREAPPSERVICE_TENANTID_15C11B66DEEA466B9473224F447604DA` | Directory (tenant) ID containing that service principal and subscription |
| `AZUREAPPSERVICE_SUBSCRIPTIONID_B33BAF200A6A42EF95AF2BEF92BFBE91` | Active subscription ID containing `flexi-rates-api` |

An Azure administrator with permission to assign roles at the app's scope can grant the deployment service principal **Website Contributor** on the target App Service. In Azure Cloud Shell (Bash), signed into the target tenant as that administrator, replace the placeholders and run:

```bash
az account set --subscription '<subscription-id>' &&
app_scope=$(az webapp show --resource-group '<resource-group>' --name flexi-rates-api --query id --output tsv) &&
principal_id=$(az ad sp show --id '<application-client-id>' --query id --output tsv) &&
az role assignment create \
  --assignee-object-id "$principal_id" \
  --assignee-principal-type ServicePrincipal \
  --role 'Website Contributor' \
  --scope "$app_scope"
```

Use the service principal's object ID, not the app registration's object ID. Prefer this app-scoped role over subscription-wide Contributor access. If the secrets refer to the wrong identity, tenant, or subscription, correct them in **Settings → Secrets and variables → Actions** instead.

Keep the workflow's `id-token: write` permission and OIDC login. Do not set `allow-no-subscriptions: true`: App Service deployment needs subscription access, so that option would only defer the failure. Once access changes have propagated, rerun the failed workflow from the Actions tab. These Azure access changes must be applied outside this repository.

## Notes

- The integration requests read-only Sheets permissions.
- The first row is used for JSON property names. Empty headers become `column_1`, `column_2`, etc.; repeated headers get numeric suffixes.
- The data endpoint currently has no caller authentication. Add Azure App Service Authentication or API authentication before exposing sensitive sheet data publicly.