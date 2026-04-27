from datetime import datetime
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")


def build_now_briefing(now: datetime | None = None) -> str:
    now = (now or datetime.now(PARIS)).astimezone(PARIS)
    return (
        "# Informations jour et heure actuel\n"
        f"- Date : {now:%Y-%m-%d}\n"
        f"- Jour : {now:%A}\n"
        f"- Heure : {now:%H:%M} (Europe/Paris)"
    )
