# 🎫 Jira PDF Exporter - Forge App

En Atlassian Forge-app som exporterar Jira-issues till professionella PDF-dokument med alla fält och bilagor.

## ✨ Funktioner

- **Issue Panel** - Export-knapp direkt på varje issue
- **Bulk Export** - Exportera flera issues samtidigt via projekt-sida
- **Alla fält** - Titel, beskrivning, status, prioritet, custom fields
- **Bilagor** - Listas i PDF:en
- **Kommentarer** - Inkluderas med författare och datum
- **Länkade issues** - Subtasks och issue-länkar

## 🚀 Installation & Deploy

### Förutsättningar

1. **Node.js** version 18 eller högre
2. **Atlassian CLI** (Forge CLI)

### Steg 1: Installera Forge CLI

```bash
npm install -g @forge/cli
```

### Steg 2: Logga in på Atlassian

```bash
forge login
```

Du kommer att omdirigeras till Atlassian för att skapa en API-token.

### Steg 3: Installera dependencies

```bash
cd forge-app
npm install
```

### Steg 4: Registrera appen

```bash
forge register
```

Detta skapar en unik app-ID för din app.

### Steg 5: Bygg TypeScript

```bash
npm run build
```

### Steg 6: Deploya appen

```bash
forge deploy
```

### Steg 7: Installera i din Jira-instans

```bash
forge install
```

Välj:
- Product: Jira
- Site: `dgroupse.atlassian.net` (eller din instans)

## 🔧 Utveckling

### Lokal utveckling med tunnel

```bash
forge tunnel
```

Detta skapar en tunnel så att ändringar syns direkt utan ny deploy.

### Bygg och deploya

```bash
npm run build && forge deploy
```

### Se loggar

```bash
forge logs
```

## 📁 Projektstruktur

```
forge-app/
├── manifest.yml          # Forge app-konfiguration
├── package.json          # NPM dependencies
├── tsconfig.json         # TypeScript-konfiguration
├── src/
│   ├── index.ts          # Huvudentrypoint
│   ├── jira-client.ts    # Jira API-klient
│   └── pdf-exporter.ts   # PDF-generator
└── static/
    ├── icon.svg          # App-ikon
    ├── issue-panel/      # UI för issue-panel
    │   └── build/
    │       └── index.html
    └── bulk-export/      # UI för bulk-export
        └── build/
            └── index.html
```

## 🎯 Användning

### Exportera en issue

1. Öppna en issue i Jira
2. Klicka på **"PDF Export"** panelen i sidofältet
3. Klicka **"Exportera till PDF"**
4. Ladda ner PDF:en

### Bulk-export

1. Gå till ett projekt
2. Klicka på **"Bulk PDF Export"** i projektmenyn
3. Skriv en JQL-query (t.ex. `project = SOMU AND status = Done`)
4. Klicka **"Sök issues"**
5. Välj de issues du vill exportera
6. Klicka **"Exportera valda"**
7. Ladda ner PDF:erna

## 🔐 Behörigheter

Appen begär följande behörigheter:

| Behörighet | Beskrivning |
|------------|-------------|
| `read:jira-work` | Läsa issues, projekt, bilagor |
| `read:jira-user` | Läsa användarinformation |
| `storage:app` | Spara temporär data |

## 📦 Publicera på Marketplace

### 1. Förbered för distribution

```bash
forge lint
```

### 2. Skapa distribution

1. Gå till [developer.atlassian.com](https://developer.atlassian.com)
2. Välj din app
3. Gå till "Distribution"
4. Fyll i information om appen

### 3. Security review

Atlassian granskar säkerheten innan publicering.

### 4. Publicera

När granskningen är godkänd kan du publicera på Marketplace!

## 🐛 Felsökning

### "App not found"
```bash
forge register
forge deploy
```

### "Permission denied"
Kontrollera att behörigheterna i `manifest.yml` är korrekta.

### "Build failed"
```bash
npm run build
```
Kontrollera TypeScript-fel.

### Visa loggar
```bash
forge logs --tail
```

## 📄 Licens

MIT License

---

**Skapad av Kristian Enström** 
