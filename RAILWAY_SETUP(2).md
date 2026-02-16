# Railway.app Setup-Anleitung — Komplett kostenlos 24/7

## Schritt 1: GitHub Repository erstellen

### 1.1 GitHub Account erstellen (falls noch nicht vorhanden)
- Gehe zu https://github.com
- Sign up (kostenlos)

### 1.2 Neues Repository erstellen
- Klicke oben rechts auf "+" → "New repository"
- Name: `discord-point-bot` (oder beliebig)
- Visibility: **Private** (empfohlen)
- ✅ Initialize with README
- Create repository

### 1.3 Dateien hochladen
Klicke auf "Add file" → "Upload files" und lade diese 3 Dateien hoch:

**Datei 1: `bot.py`** (dein vollständiger Bot-Code)
**Datei 2: `requirements.txt`**
**Datei 3: `Procfile`**

Dann "Commit changes"

---

## Schritt 2: Railway Account erstellen

### 2.1 Zu Railway gehen
- Gehe zu https://railway.app
- Klicke "Login" oben rechts

### 2.2 Mit GitHub verbinden
- Klicke "Login with GitHub"
- Authorize Railway (erlaubt Railway Zugriff auf deine Repos)
- ✅ Bestätige mit GitHub-Passwort

### 2.3 Email bestätigen
Railway schickt eine Bestätigungsmail → Link klicken

---

## Schritt 3: Bot deployen

### 3.1 Neues Projekt erstellen
- Im Railway Dashboard: **"New Project"**
- Wähle **"Deploy from GitHub repo"**

### 3.2 Repository auswählen
- Suche dein Repository: `discord-point-bot`
- Klicke drauf

### 3.3 Deploy Settings
Railway erkennt automatisch:
- ✅ Python erkannt
- ✅ requirements.txt gefunden
- ✅ Procfile gefunden

**Nichts ändern**, einfach warten bis "Deploy" erscheint

### 3.4 Discord Token hinzufügen
**WICHTIG — Bot startet erst nach diesem Schritt!**

1. Klicke auf dein Projekt
2. Klicke auf den Service (z.B. "discord-point-bot")
3. Gehe zum Tab **"Variables"**
4. Klicke **"+ New Variable"**
5. Key: `BOT_TOKEN`
6. Value: `DEIN_DISCORD_TOKEN_HIER`
7. **Add** klicken

Der Bot startet jetzt automatisch neu und sollte online gehen!

---

## Schritt 4: Überprüfen ob Bot läuft

### 4.1 Logs ansehen
- Im Railway Dashboard → dein Service
- Tab **"Deployments"** → letzte Deployment anklicken
- **"View Logs"**

Du solltest sehen:
```
✅ Bot online: DeinBotName#1234
```

### 4.2 In Discord testen
- Gehe zu deinem Discord Server
- Der Bot sollte online sein (grüner Punkt)
- Teste einen Command (z.B. in #task-creation die Buttons)

---

## Wichtige Infos:

### ✅ Kostenlos 24/7
- 500 Stunden/Monat kostenlos
- Reicht locker für einen Bot (720h = 1 Monat)
- Kein Schlafmodus
- Kein manueller Neustart nötig

### 📊 Monitoring
**Variables Tab:**
- Hier kannst du jederzeit `BOT_TOKEN` ändern

**Deployments Tab:**
- Zeigt alle Deployments und Logs
- Bei Änderungen am GitHub Repo deployt Railway automatisch neu

**Settings Tab:**
- Service Name ändern
- Restarts konfigurieren

### 🔄 Code updaten
Wenn du den Bot-Code ändern willst:
1. Ändere Dateien in GitHub (Edit file → Commit)
2. Railway deployt automatisch neu
3. Fertig!

### 🛑 Bot stoppen
Im Service → Settings → ganz unten "Delete Service"

---

## Troubleshooting:

**Bot geht nicht online:**
- Logs checken (Deployments → View Logs)
- `BOT_TOKEN` richtig gesetzt? (Variables Tab)
- Discord Token valid? (https://discord.com/developers/applications)

**"No Procfile found":**
- Prüfe dass `Procfile` (KEIN .txt!) im Root des Repos liegt
- Inhalt muss genau sein: `worker: python bot.py`

**"Module not found":**
- `requirements.txt` vorhanden?
- Enthält: `py-cord` und `pytz`

**Railway zeigt "Out of credits":**
- Free Tier hat 500h/Monat
- Checke Usage im Dashboard
- Evtl. alten Service gelöscht der noch läuft?

---

Fertig! Dein Bot läuft jetzt 24/7 kostenlos auf Railway 🚀
