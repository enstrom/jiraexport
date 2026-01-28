# 🎫 Jira Export till PDF

Exportera Jira-tickets till professionella PDF-dokument med alla fält och bilagor inkluderade.

## ✨ Funktioner

- **Fullständig export** - Alla fält exporteras: titel, beskrivning, status, prioritet, assignee, custom fields m.m.
- **Bilagor inkluderas** - Bilder visas inline i PDF:en, övriga filer listas
- **Kommentarer** - Alla kommentarer inkluderas med författare och tidsstämpel
- **Flexibel sökning** - Exportera enskilda issues, hela projekt eller med JQL-queries
- **Professionell design** - Snygg layout baserad på Jiras designspråk

## 🚀 Installation

### 1. Klona eller ladda ner projektet

```bash
cd /Users/enstrom/Documents/Code/Jira\ export
```

### 2. Skapa virtuell miljö (rekommenderat)

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# eller: venv\Scripts\activate  # Windows
```

### 3. Installera beroenden

```bash
pip install -r requirements.txt
```

### 4. Konfigurera Jira-anslutning

Kopiera exempelfilen och fyll i dina uppgifter:

```bash
cp env_example.txt .env
```

Redigera `.env` med dina Jira-uppgifter:

```env
# Din Jira-instans URL
JIRA_URL=https://ditt-foretag.atlassian.net

# Din Jira-epost
JIRA_EMAIL=din-email@example.com

# API Token (skapa på: https://id.atlassian.com/manage-profile/security/api-tokens)
JIRA_API_TOKEN=din-api-token-här
```

## 📖 Användning

### Interaktivt läge

```bash
python main.py
```

Startar ett interaktivt menysystem där du kan välja vad som ska exporteras.

### Exportera specifik issue

```bash
python main.py PROJ-123
```

### Exportera flera issues

```bash
python main.py PROJ-123 PROJ-124 PROJ-125
```

### Exportera alla issues i ett projekt

```bash
python main.py --project PROJ
```

### Filtrera på issue-typ

```bash
python main.py --project PROJ --type Story
python main.py --project PROJ --type Bug
```

### Använda JQL-query

```bash
# Alla issues tilldelade mig
python main.py --jql "assignee = currentUser()"

# Issues skapade senaste veckan
python main.py --jql "project = PROJ AND created >= -7d"

# Öppna buggar med hög prioritet
python main.py --jql "project = PROJ AND type = Bug AND priority = High AND status != Done"
```

### Övriga alternativ

```bash
# Ange utdatamapp
python main.py PROJ-123 --output ./mina-exporter

# Hoppa över nedladdning av bilagor
python main.py PROJ-123 --no-attachments

# Begränsa antal resultat
python main.py --project PROJ --max-results 50
```

## 📁 Utdatastruktur

```
exports/
├── PROJ-123.pdf
├── PROJ-124.pdf
├── PROJ-125.pdf
└── attachments/
    ├── PROJ-123/
    │   ├── screenshot.png
    │   └── document.pdf
    └── PROJ-124/
        └── design.png
```

## 🔧 API Token

För att ansluta till Jira behöver du en API-token:

1. Gå till: https://id.atlassian.com/manage-profile/security/api-tokens
2. Klicka på **"Create API token"**
3. Ge den ett namn (t.ex. "Jira Export")
4. Kopiera token och lägg in i `.env`-filen

> ⚠️ **Viktigt**: Spara aldrig din API-token i versionshantering!

## 📋 Fält som exporteras

| Kategori | Fält |
|----------|------|
| **Grundläggande** | Nyckel, Titel, Beskrivning, Status, Prioritet, Typ |
| **Personer** | Tilldelad, Rapportör |
| **Planering** | Sprint, Story Points, Fix Versions, Epic |
| **Organisation** | Komponenter, Etiketter, Parent |
| **Tid** | Skapad, Uppdaterad, Löst |
| **Relationer** | Subtasks, Länkade issues |
| **Innehåll** | Bilagor (med bilder inline), Kommentarer |
| **Custom** | Alla custom fields med värden |

## 🐛 Felsökning

### "Saknade konfigurationer"
Kontrollera att `.env`-filen finns och innehåller alla nödvändiga värden.

### "Kunde inte ansluta till Jira"
- Verifiera att JIRA_URL är korrekt
- Kontrollera att API-token är giltig
- Säkerställ att du har behörighet till projektet

### Bilder visas inte i PDF
- Kontrollera att du inte använt `--no-attachments`
- Verifiera att bildformatet stöds (PNG, JPG, GIF, WEBP)

## 📄 Licens

MIT License - Fri att använda och modifiera.
