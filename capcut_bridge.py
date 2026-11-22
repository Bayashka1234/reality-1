import asyncio
import json
import sys
from pathlib import Path
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CAPCUT_VECTORS_RAW_URL = "https://raw.githubusercontent.com/Bayashka1234/reality-1/main/capcut_vectors.json"
PORTAL_GATEWAY_URL = "https://dreamthemuse.github.io/Dream-the-Muse-/portal_omega.html"
TELEGRAM_BOT_URL = "https://t.me/MuseArchitect3871052_bot"
CAPCUT_CHANNEL_ID = "id0184534066"

def extract_records(raw_data) -> list[dict]:
    if isinstance(raw_data, list):
        return [item for item in raw_data if isinstance(item, dict)]
    if isinstance(raw_data, dict):
        vectors = raw_data.get("vectors", [])
        if isinstance(vectors, list):
            return [item for item in vectors if isinstance(item, dict)]
    return []

def format_dialogue_preview(dialogue: list, max_messages: int = 3) -> str:
    if not isinstance(dialogue, list) or not dialogue:
        return ""
    valid_msgs = [m for m in dialogue if isinstance(m, dict) and str(m.get("text", "")).strip()]
    if not valid_msgs:
        return ""
    lines = [f"  💬 Диалог вектора (реплик: {len(valid_msgs)}):"]
    for msg in valid_msgs[-max_messages:]:
        role = "АРХИТЕКТОР" if msg.get("role") == "user" else "ВЕКТОР Ω"
        msg_time = msg.get("time", "—")
        text = str(msg.get("text", "")).strip().replace("\n", " ")
        if len(text) > 140:
            text = text[:137] + "..."
        lines.append(f"     • [{msg_time}] {role}: {text}")
    return "\n".join(lines)

async def load_capcut_387_chat(limit: int = 20, include_dialogues: bool = True, prefer_local: bool = True) -> str:
    records: list[dict] = []
    source_label = "не определён"
    candidate_paths = (
        Path(r"D:\Projects\reality-1\capcut_vectors.json"),
        Path("capcut_vectors.json"),
        Path(r"D:\reality-1\capcut_vectors.json"),
    )

    def read_local() -> tuple[list[dict], str]:
        for local_path in candidate_paths:
            if local_path.exists():
                try:
                    data = json.loads(local_path.read_text(encoding="utf-8"))
                    parsed = extract_records(data)
                    if parsed:
                        return parsed, f"локальный файл ({local_path})"
                except Exception:
                    continue
        return [], ""

    async def read_remote() -> tuple[list[dict], str]:
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(CAPCUT_VECTORS_RAW_URL)
                if resp.status_code == 200:
                    parsed = extract_records(resp.json())
                    if parsed:
                        return parsed, "GitHub (Bayashka1234/reality-1)"
        except Exception:
            pass
        return [], ""

    if prefer_local:
        records, source_label = read_local()
        if not records:
            records, source_label = await read_remote()
    else:
        records, source_label = await read_remote()
        if not records:
            records, source_label = read_local()

    header = (
        "⚡ ВОССТАНОВЛЕННЫЙ ЧАТ CAPCUT · ТРЕНДЫ ИИ\n"
        f"Тема: 387 → 1052 | CapCut ID: {CAPCUT_CHANNEL_ID}\n"
        f"Бот: @MuseArchitect3871052_bot ({TELEGRAM_BOT_URL})\n"
        f"Шлюз Портала Ω: {PORTAL_GATEWAY_URL}\n"
        "────────────────────"
    )

    if not records:
        return f"{header}\nАрхив пуст или временно недоступен.\nСформируйте промпты или диалоги в Портале Ω v4.3, скачайте JSON и выполните SYNC_CAPCUT.bat."

    total_dialogues = sum(1 for r in records if isinstance(r.get("dialogue"), list) and len(r["dialogue"]) > 0)
    blocks = [f"{header}\nИсточник: {source_label} | Векторов: {len(records)} | С диалогами: {total_dialogues}"]

    for idx, item in enumerate(records[:limit], start=1):
        tag = item.get("tag", "VECTOR")
        time_str = item.get("time", "—")
        capcut_id = item.get("capcut_id", CAPCUT_CHANNEL_ID)
        content = str(item.get("content", "")).strip()
        entry_lines = [f"#{idx} [{tag}] · {time_str} · ({capcut_id})", content]
        if include_dialogues:
            dialogue_block = format_dialogue_preview(item.get("dialogue", []))
            if dialogue_block:
                entry_lines.append(dialogue_block)
        blocks.append("\n".join(entry_lines))

    if len(records) > limit:
        blocks.append(f"… и ещё записей в архиве: {len(records) - limit}")

    return "\n\n".join(blocks)

if __name__ == "__main__":
    print(asyncio.run(load_capcut_387_chat(limit=20, include_dialogues=True)))
