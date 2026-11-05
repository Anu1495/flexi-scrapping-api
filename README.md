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

## Notes

- The integration requests read-only Sheets permissions.
- The first row is used for JSON property names. Empty headers become `column_1`, `column_2`, etc.; repeated headers get numeric suffixes.
- The data endpoint currently has no caller authentication. Add Azure App Service Authentication or API authentication before exposing sensitive sheet data publicly.