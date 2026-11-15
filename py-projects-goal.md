# Entwicklungsauftrag: PyProjects – Projektverwaltung als PyHost-Plugin

## 1. Rolle und Zielsetzung

Du bist ein erfahrener Senior Python Full-Stack Developer und Softwarearchitekt mit Schwerpunkt FastAPI, SQLite, OAuth 2.0, modernen Weboberflächen und modularen Plugin-Systemen.

Deine Aufgabe ist die Konzeption und Implementierung eines neuen Plugins namens **PyProjects** für die bestehende PyHost-Plattform.

PyProjects soll eine schlanke, benutzerfreundliche Projektverwaltung sein, die Hauptprojekte, Unterprojekte und Tasks organisiert und ein interaktives Kanban-Board bereitstellt.

Die Anwendung soll keine umfangreiche Projektmanagement-Suite werden, sondern ein bewusst einfaches, wartbares und gut integriertes Werkzeug.

**Wichtig:** Entwickle ein tatsächlich lauffähiges Plugin. Beschränke dich nicht auf Architekturvorschläge, Pseudocode oder Mockups.

## 2. Verbindliche Referenzprojekte

### PyHost – Plugin-Plattform

Repository:
https://github.com/viper3400/pyhost

Analysiere insbesondere:

- README.md
- AGENTS.md
- Plugin-Vertrag und Plugin-Discovery
- Beispiele unter `examples/hello_plugin`
- ASGI-Mounting und URL-Prefix-Verhalten
- Plugin-Lifecycle
- Installation, Paketierung und Tests

PyProjects muss als eigenständiges, installierbares Python-Paket funktionieren.

Verwende den bestehenden Entry-Point-Mechanismus `tool_host.plugins`.

Verändere den PyHost-Core nicht, sofern dies nicht zwingend notwendig ist.

### FeedVanta – Architektur- und Integrationsvorbild

Repository:
https://github.com/viper3400/feedvanta

Analysiere insbesondere:

- `app/plugin.py`
- `app/main.py`
- `app/auth.py`
- `app/db.py`
- `app/templates/`
- `app/static/`
- `pyproject.toml`
- `AGENTS.md`
- Bestehende Tests

FeedVanta ist die maßgebliche Vorlage für:

1. Plugin-Registrierung
2. Google-Authentifizierung
3. Benutzerverwaltung
4. Session-Handling
5. Berechtigungen
6. SQLite-Datenhaltung
7. FastAPI-Routing
8. Reverse-Proxy-Unterstützung
9. Layout und Frontend-Architektur
10. Paketierung und Release-Prozess

Übernimm bewährte Konzepte, aber kopiere keinen unnötigen FeedVanta-spezifischen Code.

Stelle sicher, dass PyProjects technisch unabhängig von FeedVanta installiert und betrieben werden kann.

## 3. Funktionaler Umfang

### 3.1 Hauptprojekte

Ein Hauptprojekt ist die oberste organisatorische Ebene.

Jedes Hauptprojekt besitzt mindestens folgende Eigenschaften:

- Eindeutige ID
- Name
- Beschreibung
- Status: Aktiv, Pausiert, Abgeschlossen, Archiviert
- Farbe zur visuellen Kennzeichnung
- Erstellungsdatum
- Änderungsdatum
- Optionales Startdatum
- Optionales Zieldatum
- Eigentümer

Funktionen:

- Hauptprojekt erstellen
- Hauptprojekt bearbeiten
- Hauptprojekt archivieren
- Hauptprojekt löschen
- Zugehörige Unterprojekte anzeigen
- Zugehörige Tasks anzeigen
- Projektfortschritt auf Basis erledigter Tasks berechnen

Beim Löschen eines Hauptprojekts muss ausdrücklich auf betroffene Unterprojekte und Tasks hingewiesen werden.

### 3.2 Unterprojekte

Jedes Hauptprojekt kann beliebig viele Unterprojekte enthalten.

Unterprojekte besitzen:

- Eindeutige ID
- Zugehöriges Hauptprojekt
- Name
- Beschreibung
- Status
- Farbe (optional, sonst vom Hauptprojekt abgeleitet)
- Erstellungsdatum
- Änderungsdatum
- Optionales Startdatum
- Optionales Zieldatum

Funktionen:

- Unterprojekt erstellen
- Unterprojekt bearbeiten
- Unterprojekt verschieben
- Unterprojekt archivieren oder löschen
- Zugehörige Tasks anzeigen
- Fortschritt berechnen

Für das MVP reicht eine Hierarchie mit genau zwei Projektebenen:

Hauptprojekt → Unterprojekt → Task

Keine beliebig tiefe Projektverschachtelung implementieren.

### 3.3 Taskverwaltung

Tasks sind die eigentlichen Arbeitseinheiten.

Ein Task besitzt:

- Eindeutige ID
- Titel
- Beschreibung
- Zugehöriges Hauptprojekt
- Optionales Unterprojekt
- Status
- Priorität
- Erstellungsdatum
- Änderungsdatum
- Optionales Fälligkeitsdatum
- Optionales Startdatum
- Zuständiger Benutzer (optional)
- Ersteller
- Sortierposition innerhalb des Kanban-Boards

Task-Status:

1. Backlog
2. Offen
3. In Bearbeitung
4. Blockiert
5. Erledigt

Prioritäten:

- Niedrig
- Normal
- Hoch
- Kritisch

Funktionen:

- Task erstellen
- Task bearbeiten
- Task löschen
- Task einem Benutzer zuweisen
- Task einem anderen Unterprojekt zuordnen
- Status ändern
- Priorität ändern
- Task duplizieren
- Task als erledigt markieren
- Tasks nach Status, Projekt, Priorität und Benutzer filtern
- Tasks nach Fälligkeit und Priorität sortieren

Tasks dürfen direkt einem Hauptprojekt zugeordnet werden, ohne zwingend einem Unterprojekt anzugehören.

### 3.4 Kanban-Board

Implementiere ein modernes, interaktives Kanban-Board als zentrale Arbeitsansicht.

Spalten:

- Backlog
- Offen
- In Bearbeitung
- Blockiert
- Erledigt

Jede Task wird als Karte angezeigt.

Eine Karte zeigt mindestens:

- Titel
- Projekt oder Unterprojekt
- Priorität
- Optionales Fälligkeitsdatum
- Optional zuständigen Benutzer
- Visuelle Kennzeichnung über Farben

**Drag & Drop ist eine Kernanforderung.**

Benutzer sollen Tasks:

- Zwischen Spalten verschieben
- Innerhalb einer Spalte sortieren
- Per Klick öffnen und bearbeiten

Änderungen müssen zuverlässig in SQLite gespeichert werden.

Die Oberfläche soll unmittelbar auf Änderungen reagieren, ohne die gesamte Seite neu laden zu müssen.

Das Board soll verschiedene Ansichten unterstützen:

**Globales Board:** Alle für den Benutzer sichtbaren Tasks, projektübergreifend.

**Hauptprojekt-Board:** Alle Tasks eines Hauptprojekts einschließlich seiner Unterprojekte.

**Unterprojekt-Board:** Nur Tasks eines ausgewählten Unterprojekts.

Zusätzliche Funktionen:

- Filter nach Projekten
- Filter nach Priorität
- Filter nach zuständigem Benutzer
- Suchfeld
- Anzahl Tasks pro Spalte
- Schnelles Erstellen einer Task direkt in einer Spalte
- Responsive Darstellung

Verwende eine leichtgewichtige, gut wartbare Drag-and-Drop-Lösung. Bevorzuge die bestehende Frontend-Architektur gegenüber einem zusätzlichen komplexen JavaScript-Framework.

Sorge auch für eine bedienbare Alternative zu Drag & Drop, beispielsweise über eine Statusauswahl.

## 4. Authentifizierung und Benutzerverwaltung

**Die Benutzeranmeldung muss sich so verhalten wie in FeedVanta.**

Analysiere die tatsächliche Implementierung in FeedVanta, bevor du die Authentifizierung entwickelst.

### Google OAuth

- Anmeldung über Google
- OAuth-Implementierung mit Authlib
- Serverseitige Prüfung der OAuth-Identität
- Eindeutige Identifizierung über `google_sub`
- Speicherung der Benutzer in SQLite
- Session-basierte Authentifizierung
- Logout
- Schutz aller administrativen und projektbezogenen Endpunkte

Verwende dieselben bewährten Sicherheits- und Session-Konzepte wie FeedVanta.

### Benutzerverwaltung

Beim ersten erfolgreichen Login wird ein Benutzer angelegt.

Der erste Benutzer erhält automatisch die Berechtigung:

`Global Administration`

Globale Administratoren können:

- Benutzer anzeigen
- Globale Administratorrechte vergeben
- Globale Administratorrechte entziehen
- Zugriffe auf PyProjects verwalten

Der letzte globale Administrator darf nicht entfernt werden.

Zusätzlich soll eine Berechtigung `Project Access` existieren.

Normale Benutzer benötigen diese Berechtigung, um PyProjects verwenden zu dürfen. Globale Administratoren erhalten Zugriff unabhängig von dieser zusätzlichen Berechtigung.

Für die erste Version gilt:

- Globale Administratoren dürfen sämtliche Projekte verwalten.
- Benutzer mit Project Access dürfen die Projekte und Tasks verwenden.
- Tasks können angemeldeten Benutzern zugewiesen werden.
- Projektbezogene Rollen und private Projekte sind zunächst nicht erforderlich.

Berechtigungen müssen serverseitig durchgesetzt werden, auch bei direkten API-Aufrufen.

### Wichtige Architekturvorgabe

PyHost selbst stellt nicht automatisch eine gemeinsame Benutzeridentität für alle Plugins bereit.

Prüfe deshalb die tatsächliche Authentifizierungsarchitektur von FeedVanta.

Implementiere PyProjects zunächst mit einer eigenen, von FeedVanta unabhängigen Authentifizierungs- und Benutzerdatenhaltung nach demselben Muster.

Eine gemeinsame Anmeldung über mehrere Plugins darf nicht vorausgesetzt oder simuliert werden.

Dokumentiere mögliche Erweiterungen für eine spätere zentrale Authentifizierung.

## 5. Datenbank

Verwende SQLite, analog zu FeedVanta.

Konfigurierbarer Datenbankpfad:

`PYPROJECTS_DB`

Standard:

`data/pyprojects.db`

Vorgeschlagene Tabellen:

- users
- user_permissions
- projects
- subprojects
- tasks

Definiere geeignete Fremdschlüssel, Indizes und Constraints.

Besonders wichtig:

- Konsistente Projektzuordnungen
- Eindeutige Task-IDs
- Transaktionale Änderungen
- SQLite Foreign Keys
- Sichere Löschoperationen
- Stabile Sortierpositionen für Kanban
- Datenbankmigrationen bei Schemaänderungen

Nutze ein versioniertes Migrationskonzept, das sich am bestehenden FeedVanta-Ansatz orientiert.

Es dürfen bei Updates keine bestehenden Projektdaten verloren gehen.

## 6. Weboberfläche und UX

Die Anwendung soll optisch und technisch zu FeedVanta passen, aber eine eigene Identität erhalten.

Bevorzugter Stack:

- FastAPI
- Jinja2
- Tailwind CSS
- Vanilla JavaScript oder eine kleine passende JavaScript-Bibliothek
- SQLite

Vermeide unnötige Frameworks und aufwendige Build-Pipelines.

### Navigationsstruktur

**Dashboard**

Zeigt:

- Anzahl aktiver Hauptprojekte
- Anzahl Unterprojekte
- Offene Tasks
- Überfällige Tasks
- Kürzlich bearbeitete Tasks
- Projektfortschritte

**Projekte**

Zeigt Hauptprojekte und die zugehörigen Unterprojekte.

Eine Baumansicht oder klar gegliederte Kartenansicht ist geeignet.

**Kanban**

Zentrale Taskverwaltung mit Drag & Drop.

**Tasks**

Tabellarische oder listenbasierte Ansicht aller Tasks mit Filtern und Sortierung.

**Administration**

Benutzerverwaltung und Berechtigungen, nur für Administratoren.

### Designanforderungen

- Modern und minimalistisch
- Desktop-optimiert
- Auf Tablets nutzbar
- Auf Smartphones sinnvoll bedienbar
- Klare visuelle Hierarchie
- Gute Lesbarkeit
- Gut erkennbare Prioritäten und Status
- Konsistente Dialoge und Formulare
- Verständliche Fehlermeldungen
- Deutsche Benutzeroberfläche
- Zugängliche Bedienelemente und Tastaturbedienung

Vermeide unnötige Animationen und visuelle Überladung.

## 7. Plugin-Integration in PyHost

PyProjects muss den vorhandenen Plugin-Vertrag erfüllen.

Vorgesehene Metadaten:

- ID: `pyprojects`
- Name: `PyProjects`
- Beschreibung: `Lightweight project and task management`
- Plugin-Pfad: `/pyprojects`

Registrierung über:

`[project.entry-points."tool_host.plugins"]`

Beispiel:

`pyprojects = "app.plugin:PLUGIN"`

Die genaue Implementierung muss mit dem aktuellen PyHost-Vertrag übereinstimmen.

Das Plugin soll:

- Unabhängig installierbar sein
- Über PyHost automatisch entdeckt werden
- Eine eigene FastAPI-App bereitstellen
- Einen eigenen Datenbank-Lifecycle besitzen
- Keine Änderungen am PyHost-Core erfordern
- Unter `/pyprojects/` erreichbar sein

### Reverse Proxy

Unterstütze bestehende PyHost-Mechanismen für:

- Root-Path
- Externe URL-Prefixe
- HTTPS hinter Reverse Proxies
- OAuth-Callback-URLs
- Statische Ressourcen
- Redirects

Teste insbesondere verschachtelte externe Pfade wie:

`https://example.com/tools/pyprojects/`

Übernimm keine fest verdrahteten absoluten URL-Pfade, die beim Betrieb hinter einem Reverse Proxy fehlschlagen.

## 8. Sicherheit

Implementiere mindestens:

- Sichere Session-Cookies
- Konfigurierbare HTTPS-only-Cookies
- CSRF-Schutz für zustandsändernde Browseraktionen
- Sichere OAuth-State-Validierung
- Serverseitige Berechtigungsprüfung
- Eingabevalidierung mit Pydantic
- Parametrisierte SQL-Abfragen
- Schutz vor XSS
- Schutz gegen unzulässige Projekt- und Task-Zugriffe
- Sichere Behandlung von Datenbankfehlern
- Keine Secrets im Repository

Verwende Umgebungskonfigurationen analog zu FeedVanta.

Vorgeschlagene Variablen:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `PYPROJECTS_SESSION_SECRET`
- `PYPROJECTS_SECURE_COOKIES`
- `PYPROJECTS_DB`

Prüfe sämtliche Sicherheitsannahmen anhand des tatsächlichen Codes und korrigiere keine vermeintlichen Probleme durch unsichere Workarounds.

## 9. Technische Qualitätsanforderungen

Halte die Architektur möglichst einfach.

Trenne Verantwortlichkeiten für:

- Datenbankzugriffe
- Datenmodelle
- Geschäftslogik
- Authentifizierung
- API-Routen
- HTML-Views
- Frontend-Skripte

Vermeide eine einzige übergroße `main.py`.

Nutze Python-Typannotationen.

Orientiere dich an den bestehenden Konventionen von FeedVanta.

Verwende `uv` für Dependency-Management.

Berücksichtige die Python-Version aus den Repositories.

Füge nur Abhängigkeiten hinzu, die tatsächlich benötigt werden.

## 10. Tests

Erstelle automatisierte Tests mit pytest.

Mindestens zu testen:

1. Plugin-Erkennung durch PyHost
2. Erstellen und Bearbeiten von Hauptprojekten
3. Erstellen und Bearbeiten von Unterprojekten
4. Erstellen von Tasks
5. Zuordnung von Tasks zu Projekten
6. Task-Statusänderungen
7. Kanban-Sortierung
8. Konsistenz beim Verschieben von Tasks
9. Berechtigungsprüfungen
10. Zugriff ohne Anmeldung
11. Administratorrechte
12. Schutz des letzten Administrators
13. Datenbankmigrationen
14. Verhalten bei ungültigen Eingaben
15. Betrieb mit URL-Prefix
16. Fehlerfälle und konkurrierende Änderungen

OAuth-Tests müssen mit kontrollierten Testdaten und Mocks möglich sein. Live-Google-Zugangsdaten dürfen für die automatisierten Tests nicht erforderlich sein.

## 11. Dokumentation und Deployment

Erstelle eine vollständige README.md mit:

- Funktionsübersicht
- Architektur
- Installation
- Konfiguration
- Google-OAuth-Einrichtung
- Lokaler Entwicklung
- PyHost-Integration
- Datenbankpfad
- Reverse-Proxy-Beispiel
- Ausführung der Tests
- Build eines Python-Wheels
- Release-Vorgehen

Erstelle zusätzlich:

- `.env.example`
- `AGENTS.md`
- `CHANGES.md`
- Geeignete `.gitignore`
- Konfiguration für reproduzierbare Dependency-Installation

Orientiere dich am Paketierungs- und Release-Verfahren von FeedVanta.

## 12. Vorgehensweise des Agenten

Arbeite in folgenden Phasen.

### Phase 1 – Analyse

Untersuche zuerst PyHost und FeedVanta.

Lies die AGENTS.md-Dateien und die relevanten Implementierungen.

Dokumentiere kompakt:

- Die Plugin-Schnittstelle
- Den Authentifizierungsablauf
- Die Benutzer- und Berechtigungsverwaltung
- Die Datenbankarchitektur
- Das Frontend-Konzept
- Das URL- und Reverse-Proxy-Verhalten
- Den Release-Prozess

Identifiziere technische Risiken und Abweichungen von den hier vorgeschlagenen Annahmen.

### Phase 2 – Architektur

Erstelle:

- Projektstruktur
- Datenbankschema
- Beziehungen der Datenmodelle
- API-Konzept
- Seiten- und Navigationskonzept
- Kanban-Interaktionskonzept
- Migrationskonzept

Entscheide pragmatisch und vermeide Overengineering.

### Phase 3 – Implementierung

Implementiere das MVP in kleinen, nachvollziehbaren Schritten:

1. Paketstruktur und Plugin-Registrierung
2. Datenbank und Migrationen
3. Google OAuth und Benutzerverwaltung
4. Hauptprojekte
5. Unterprojekte
6. Tasks
7. Kanban-Board
8. Dashboard
9. Administration
10. UI-Polishing und Dokumentation

Halte die Anwendung nach jedem größeren Schritt möglichst lauffähig.

### Phase 4 – Qualitätssicherung

Führe Tests aus und behebe Probleme.

Kontrolliere insbesondere:

- Erfolgreiches Laden in PyHost
- Funktionierendes Login
- Korrekte Zugriffskontrolle
- Konsistenz der Datenbank
- Kanban-Drag-and-Drop
- Reverse-Proxy-Kompatibilität

Kennzeichne nicht ausführbare Tests ausdrücklich als ungeprüft.

### Phase 5 – Abschluss

Liefere:

- Den vollständigen Quellcode
- Installationsanleitung
- Konfigurationsbeispiel
- Dokumentation
- Testergebnisse
- Bekannte Einschränkungen
- Sinnvolle Vorschläge für Version 2

## 13. Abgrenzung des MVP

Folgende Funktionen sind ausdrücklich nicht Teil der ersten Version:

- Zeiterfassung
- Gantt-Diagramme
- Dateianhänge
- Kommentare oder Diskussionen
- E-Mail-Benachrichtigungen
- Wiederkehrende Tasks
- Beliebig tiefe Projektverschachtelung
- Komplexe Rollen pro Projekt
- Externe Projektmanagement-Integrationen
- Echtzeit-Synchronisierung über WebSockets

Die Architektur darf spätere Erweiterungen ermöglichen, aber sie sollen nicht vorsorglich implementiert werden.

## 14. Verbindliche Arbeitsregeln

1. Analysiere zuerst den tatsächlich vorhandenen Code.
2. Halte dich an die Vorgaben der AGENTS.md-Dateien.
3. Erfinde keine PyHost-APIs oder Authentifizierungsfunktionen.
4. Verwende FeedVanta als Referenz für die Anmeldung und Plugin-Integration.
5. Bevorzuge einfache, bereits etablierte Lösungen.
6. Arbeite testorientiert.
7. Dokumentiere wichtige Architekturentscheidungen.
8. Vermeide Änderungen an nicht betroffenen Repositories.
9. Bewahre vorhandene Daten bei Migrationen.
10. Erstelle keine unnötigen Features außerhalb des MVP.
11. Verwende Conventional Commits.
12. Führe keine Commits oder Pushes auf produktive Hauptbranches ohne entsprechende Freigabe aus.

**Beginne mit der Analyse der beiden Repositories und setze danach die vollständige MVP-Implementierung um. Triff bei kleineren technischen Unklarheiten sinnvolle, dokumentierte Entscheidungen selbstständig.**