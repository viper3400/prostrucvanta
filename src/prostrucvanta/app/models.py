from datetime import datetime, timezone

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

PROJECT_STATUS = ("Aktiv", "Pausiert", "Abgeschlossen", "Archiviert")
TASK_STATUS = ("Backlog", "Offen", "In Bearbeitung", "Blockiert", "Erledigt")
TASK_PRIORITY = ("Niedrig", "Normal", "Hoch", "Kritisch")
