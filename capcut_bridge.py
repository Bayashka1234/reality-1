import os
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

# Основные пути проекта Reality-1 и системной папки Загрузки
BASE_DIR = Path(r"D:\reality-1")
DOWNLOADS_DIR = Path.home() / "Downloads"
TARGET_JSON = BASE_DIR / "capcut_vectors.json"
DUMP_TXT = BASE_DIR / "capcut_dump.txt"
VAULT_DB = BASE_DIR / "omega_vault.db"


def sync_from_downloads() -> bool:
    """Находит свежий capcut_vectors*.json в папке Загрузки и переносит его в D:\\reality-1."""
    if not DOWNLOADS_DIR.exists():
        print(f"[!] Папка загрузок не найдена: {DOWNLOADS_DIR}")
        return False

    candidates = sorted(
        DOWNLOADS_DIR.glob("capcut_vectors*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        print("[i] Новых файлов capcut_vectors*.json в папке Загрузки нет. Используем локальный архив.")
        return False

    latest = candidates[0]
    try:
        # Проверяем валидность JSON перед переносом
        with open(latest, "r", encoding="utf-8") as f:
            json.load(f)

        BASE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(latest, TARGET_JSON)
        latest.unlink()  # Удаляем обработанный дубликат из Загрузок
        print(f"[OK] Подхвачен и перенесён свежий экспорт из Загрузок: {latest.name}")
        return True
    except Exception as exc:
        print(f"[ОШИБКА] Не удалось обработать {latest.name}: {exc}")
        return False


def load_vectors() -> list[dict]:
    """Считывает и нормализует карточки из capcut_vectors.json."""
    if not TARGET_JSON.exists():
        print(f"[!] Файл {TARGET_JSON} пока отсутствует.")
        return []

    try:
        with open(TARGET_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"[ОШИБКА ЧТЕНИЯ JSON]: {exc}")
        return []

    # Поддержка формата массива карточек (v6.4/v6.5) и вложенного объекта vectors
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("vectors"), list):
        return data["vectors"]
    return []


def init_db(conn: sqlite3.Connection) -> None:
    """Создаёт или проверяет таблицу векторов в SQLite-базе omega_vault.db."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS capcut_vectors (
            uid TEXT PRIMARY KEY,
            chat TEXT NOT NULL,
            tag TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT,
            synced_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def sync_to_sqlite_and_dump(cards: list[dict]) -> int:
    """Сохраняет уникальные карточки «387 1052» в omega_vault.db и формирует capcut_dump.txt."""
    if not cards:
        return 0

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0

    with sqlite3.connect(VAULT_DB) as conn:
        init_db(conn)
        for item in cards:
            content = str(item.get("content", "")).strip()
            if not content:
                continue

            uid = str(item.get("id") or abs(hash(content)))
            chat = str(item.get("chat") or "387 1052").strip()
            tag = str(item.get("tag") or "PROMPT_ENG").strip()
            created_at = str(item.get("time") or now_iso).strip()

            cur = conn.execute(
                """
                INSERT OR IGNORE INTO capcut_vectors (uid, chat, tag, content, created_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (uid, chat, tag, content, created_at, now_iso),
            )
            if cur.rowcount > 0:
                inserted += 1
        conn.commit()

        # Обновляем текстовый дамп для быстрого просмотра
        rows = conn.execute(
            "SELECT chat, tag, created_at, content FROM capcut_vectors ORDER BY rowid DESC"
        ).fetchall()

    with open(DUMP_TXT, "w", encoding="utf-8") as dump:
        dump.write(f"=== OMEGA VAULT · CAPCUT SYNC [387 1052] | ОБНОВЛЕНО: {now_iso} ===\n")
        dump.write(f"ВСЕГО ВЕКТОРОВ В БАЗЕ: {len(rows)}\n\n")
        for chat, tag, created_at, content in rows:
            dump.write(f"[{created_at}] [{chat}] [{tag}]\n{content}\n" + "-" * 60 + "\n")

    return inserted


def git_auto_push(added_count: int) -> None:
    """Фиксирует обновлённые архивы capcut_vectors.json, capcut_dump.txt и omega_vault.db в GitHub."""
    if not (BASE_DIR / ".git").exists():
        print("[!] Папка .git не найдена в D:\\reality-1 — авто-пуш пропущен.")
        return

    files_to_stage = ["capcut_vectors.json", "capcut_dump.txt", "omega_vault.db"]
    existing_files = [f for f in files_to_stage if (BASE_DIR / f).exists()]
    if not existing_files:
        return

    try:
        subprocess.run(["git", "-C", str(BASE_DIR), "add", *existing_files], check=True)
        status = subprocess.run(
            ["git", "-C", str(BASE_DIR), "status", "--porcelain", *existing_files],
            capture_output=True,
            text=True,
            check=True,
        )
        if not status.stdout.strip():
            print("[i] В Git нет новых изменений в файлах архива.")
            return

        msg = f"Sync CapCut 387 1052 vault (+{added_count} vectors)"
        subprocess.run(["git", "-C", str(BASE_DIR), "commit", "-m", msg], check=True)
        subprocess.run(["git", "-C", str(BASE_DIR), "push", "origin", "main"], check=True)
        print("[OK] Архив успешно отправлен в репозиторий GitHub (Bayashka1234/reality-1)!")
    except subprocess.CalledProcessError as exc:
        print(f"[!] Ошибка при отправке в GitHub: {exc}")


def main() -> None:
    print("=== ЗАПУСК МОСТА CAPCUT_BRIDGE.PY (387 -> 1052) ===")
    sync_from_downloads()
    cards = load_vectors()
    if not cards:
        print("[i] Нет карточек для синхронизации. Нажмите «СКАЧАТЬ capcut_vectors.json» в Портале Ω.")
        return

    added = sync_to_sqlite_and_dump(cards)
    print(f"[OK] Обработано карточек: {len(cards)} | Добавлено новых в omega_vault.db: {added}")
    print(f"[OK] Текстовый дамп обновлён: {DUMP_TXT}")
    git_auto_push(added)


if __name__ == "__main__":
    main()
