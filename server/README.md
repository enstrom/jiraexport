# Jira PDF Export Server

REST API-server som genererar PDF:er med bilder från Jira-issues.

## Snabb deployment till Render (gratis)

### 1. Skapa Render-konto
Gå till [render.com](https://render.com) och registrera dig (gratis).

### 2. Anslut GitHub
1. Pusha denna kod till ett GitHub-repo
2. I Render Dashboard, klicka "New" → "Web Service"
3. Anslut ditt GitHub-repo

### 3. Konfigurera tjänsten
- **Name:** `jira-pdf-export`
- **Runtime:** Python 3
- **Build Command:** `pip install -r server/requirements.txt`
- **Start Command:** `cd server && gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app`
- **Plan:** Free

### 4. Lägg till miljövariabler
I Render Dashboard → Environment:

```
JIRA_URL=https://ditt-företag.atlassian.net
JIRA_EMAIL=din-email@företag.com
JIRA_API_TOKEN=din-api-token
```

### 5. Deploya
Klicka "Create Web Service" - deployment startar automatiskt.

Din server är nu tillgänglig på: `https://jira-pdf-export.onrender.com`

## Uppdatera Forge-appen

Ändra `PDF_SERVER_URL` i `forge-app/static/bulk-export/src/index.jsx`:

```javascript
const PDF_SERVER_URL = 'https://jira-pdf-export.onrender.com';
```

Bygg och deploya sedan Forge-appen:

```bash
cd forge-app/static/bulk-export && npm run build
cd ../../ && forge deploy --environment staging
```

## API-endpoints

### GET /health
Hälsokontroll.

### POST /api/export
Exportera flera issues.

**Request:**
```json
{
  "issue_keys": ["SOMU-31", "SOMU-48"]
}
```

**Response:**
```json
{
  "success": true,
  "pdfs": [
    {
      "issue_key": "SOMU-31",
      "filename": "SOMU-31.pdf",
      "pdf_base64": "..."
    }
  ],
  "errors": [],
  "total": 2,
  "exported": 2,
  "failed": 0
}
```

### GET /api/export/single/:issue_key
Exportera en issue. Lägg till `?download=true` för att ladda ner filen direkt.

## Lokal utveckling

```bash
cd server
pip install -r requirements.txt
python app.py
```

Servern startar på `http://localhost:5000`.
