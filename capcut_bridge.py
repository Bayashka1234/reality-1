import asyncio
import json
from pathlib import Path
import httpx

CAPCUT_VECTORS_RAW_URL = (
    "https://raw.githubusercontent.com/Bayashka1234/reality-1/main/capcut_vectors.json"
)


async def load_capcut_387_chat(limit: int = 20) -> str:
    """Загружает восстановленные записи чата CapCut '387 1052' из GitHub или локального файла."""
    records = []

    # 1. Пробуем получить актуальный JSON из репозитория Reality-1
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            resp = await client.get(CAPCUT_VECTORS_RAW_URL)
            if resp.status_code == 200:
                data = resp.json()
                records = data if isinstance(data, list) else data.get("vectors", [])
    except Exception:
        pass

    # 2. Резервное чтение с локального диска, если запущено локально
    if not records:
        candidate_paths = (
            Path("capcut_vectors.json"),
            Path(r"D:\Projects\reality-1\capcut_vectors.json"),
            Path(r"D:\reality-1\capcut_vectors.json"),
        )
        for local_path in candidate_paths:
            if local_path.exists():
                try:
                    data = json.loads(local_path.read_text(encoding="utf-8"))
                    records = data if isinstance(data, list) else data.get("vectors", [])
                    if records:
                        break
                except Exception:
                    pass

    header = (
        "⚡ ВОССТАНОВЛЕННЫЙ ЧАТ CAPCUT · ТРЕНДЫ ИИ\n"
        "Тема: 387 → 1052 | CapCut ID: id0184534066\n"
        "Шлюз Портала Ω: https://dreamthemuse.github.io/Dream-the-Muse-/portal_omega.html\n"
        "────────────────────\n"
    )

    if not records:
        return (
            header
            + "Архив пуст или временно недоступен.\n"
            + "Сформируйте промпты в Портале Ω и выполните синхронизацию (SYNC_CAPCUT.bat)."
        )

    # 3. Форматируем найденные векторы
    blocks = [header.rstrip()]
    for idx, item in enumerate(records[:limit], start=1):
        tag = item.get("tag", "VECTOR")
        time_str = item.get("time", "—")
        content = str(item.get("content", "")).strip()
        blocks.append(f"#{idx} [{tag}] · {time_str}\n{content}")

    if len(records) > limit:
        blocks.append(f"\n… и ещё записей в архиве: {len(records) - limit}")

    return "\n\n".join(blocks)


if __name__ == "__main__":
    print(asyncio.run(load_capcut_387_chat()))
