# Google Sheets Read API

A small FastAPI service that reads data from one of several hotel Google Sheets and returns each data row as a JSON object. The first row in the selected tab is treated as the column headers.

## Project layout

```text
app/
  api/routes.py          HTTP endpoints
   core/config.py         Credential settings
   core/hotels.py         Hotel scrape IDs and Google Sheet mappings
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
5. The supported hotels and tabs are registered in `app/core/hotels.py`. The API reads columns A:Z from each configured tab, using its `gid` from the URL to locate the tab.

Share each of the four spreadsheets with the service-account `client_email` as a Viewer. The service account file in the project root is used by default for local development. It is ignored by Git. Never commit or publish it.

| Hotel | Short form | `scrape_id` |
| --- | --- | ---: |
| Indigo London Paddington | HILP | 4 |
| Mercure London Paddington | MLP | 3 |
| Mercure London Hyde Park | MLHP | 6 |
| Holiday Inn Leicester Wigston | HILW | 7 |

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
   - `http://127.0.0.1:8000/api/v1/sheets/data?scrape_id=4` — all rate records for Indigo London Paddington
   - `http://127.0.0.1:8000/api/v1/sheets/data?scrape_id=3&checkin_date=2026-11-05` — rate records for Mercure London Paddington on November 5, 2026 (blank Date cells continue the preceding date group)
   - `http://127.0.0.1:8000/api/v1/sheets/data?scrape_id=6` — all rows for Mercure London Hyde Park
   - `http://127.0.0.1:8000/api/v1/sheets/data?scrape_id=7` — all rows for Holiday Inn Leicester Wigston
   - `http://127.0.0.1:8000/docs` — interactive API documentation

Each sheet row is converted to the API's rate-record shape. `timeStamp` is the UTC response-generation time, `price` and `availability` are numeric when present, and meal/refund flags are derived from `Rate Type`.

```json
[
   {
      "checkIn": "2026-11-05",
      "timeStamp": "2026-11-06T12:30:00Z",
      "source": null,
      "ratePlanCode": null,
      "roomType": "1 Queen Premium with Private Patio",
      "price": 256,
      "adults": 2,
      "children": 0,
      "infants": 0,
      "refundable": false,
      "breakfast": false,
      "lunch": false,
      "dinner": false,
      "nights": 1,
      "availability": 0
   }
]
```

## Deploy to Azure App Service

Create an App Service using a supported Python runtime, deploy this project directory, and set this App Service **Configuration → Application setting**:

- `GOOGLE_SERVICE_ACCOUNT_JSON`: the complete contents of the service-account JSON file

App Service application settings are provided to the process as environment variables. Keep the credential setting secret, restrict access to the Azure resource, and do not upload the JSON key file with the deployment. For production, prefer storing credentials in Azure Key Vault and using managed references where available.

Set the App Service startup command to:

```text
gunicorn --bind=0.0.0.0:8000 --timeout 600 -k uvicorn.workers.UvicornWorker app.main:app
```

After deploying the updated code, request `https://<your-app-name>.azurewebsites.net/api/v1/sheets/data?scrape_id=4`; use `scrape_id=3`, `6`, or `7` for the other hotels. Add `&checkin_date=YYYY-MM-DD` to filter that hotel's transformed records by the `Date` column. Interactive docs are at `/docs`.

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
- `scrape_id` is required. Supported values are `3`, `4`, `6`, and `7`; other values receive HTTP 400.
- Required sheet columns are `Date`, `Room Type`, `Rate`, `Rate Type`, and `Availability`. Rows with a blank `Date` inherit the preceding nonblank date, matching the sheet's grouped-date layout.
- `refundable` is true for `Refundable` and `Refundable with Breakfast`; `breakfast` is true for `Non-Refundable with Breakfast` and `Refundable with Breakfast`.
- The first row is used for JSON property names. Empty headers become `column_1`, `column_2`, etc.; repeated headers get numeric suffixes.
- The data endpoint currently has no caller authentication. Add Azure App Service Authentication or API authentication before exposing sensitive sheet data publicly.