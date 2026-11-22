import os
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"D:\reality-1")
DOWNLOADS_DIR = Path.home() / "Downloads"
TARGET_JSON = BASE_DIR / "capcut_vectors.json"
DUMP_TXT = BASE_DIR / "capcut_dump.txt"
VAULT_DB = BASE_DIR / "omega_vault.db"

def sync_from_downloads() -> bool:
    if not DOWNLOADS_DIR.exists():
        return False
    candidates = sorted(DOWNLOADS_DIR.glob("capcut_vectors*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print("[i] Новых файлов capcut_vectors*.json в Загрузках нет. Используем локальный архив.")
        return False
    latest = candidates[0]
    try:
        with open(latest, "r", encoding="utf-8") as f:
            json.load(f)
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(latest, TARGET_JSON)
        latest.unlink()
        print(f"[OK] Подхвачен свежий экспорт из Загрузок: {latest.name}")
        return True
    except Exception as exc:
        print(f"[ОШИБКА] {latest.name}: {exc}")
        return False

def load_vectors() -> list[dict]:
    if not TARGET_JSON.exists():
        return []
    try:
        with open(TARGET_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("vectors"), list):
        return data["vectors"]
    return []

def init_and_migrate_db(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS capcut_vectors (uid TEXT UNIQUE, chat TEXT DEFAULT '387 1052', tag TEXT DEFAULT 'PROMPT_ENG', content TEXT NOT NULL, created_at TEXT, synced_at TEXT)")
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(capcut_vectors)").fetchall()}
    for col_name, col_def in {"uid": "TEXT", "chat": "TEXT DEFAULT '387 1052'", "tag": "TEXT DEFAULT 'PROMPT_ENG'", "content": "TEXT", "created_at": "TEXT", "synced_at": "TEXT"}.items():
        if col_name not in existing_cols:
            conn.execute(f"ALTER TABLE capcut_vectors ADD COLUMN {col_name} {col_def}")
            print(f"[DB MIGRATION] Добавлена колонка '{col_name}'.")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_capcut_vectors_uid ON capcut_vectors(uid)")
    conn.commit()

def sync_to_sqlite_and_dump(cards: list[dict]) -> int:
    if not cards:
        return 0
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0
    with sqlite3.connect(VAULT_DB) as conn:
        init_and_migrate_db(conn)
        for item in cards:
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            uid = str(item.get("id") or abs(hash(content)))
            chat = str(item.get("chat") or "387 1052").strip()
            tag = str(item.get("tag") or "PROMPT_ENG").strip()
            created_at = str(item.get("time") or now_iso).strip()
            cur = conn.execute("INSERT OR IGNORE INTO capcut_vectors (uid, chat, tag, content, created_at, synced_at) VALUES (?, ?, ?, ?, ?, ?)", (uid, chat, tag, content, created_at, now_iso))
            if cur.rowcount > 0:
                inserted += 1
        conn.commit()
        rows = conn.execute("SELECT COALESCE(chat, '387 1052'), COALESCE(tag, 'PROMPT_ENG'), COALESCE(created_at, ''), content FROM capcut_vectors ORDER BY rowid DESC").fetchall()
    with open(DUMP_TXT, "w", encoding="utf-8") as dump:
        dump.write(f"=== OMEGA VAULT · CAPCUT SYNC [387 1052] | ОБНОВЛЕНО: {now_iso} ===\nВСЕГО ВЕКТОРОВ: {len(rows)}\n\n")
        for chat, tag, created_at, content in rows:
            dump.write(f"[{created_at}] [{chat}] [{tag}]\n{content}\n" + "-" * 60 + "\n")
    return inserted

def git_auto_push(added_count: int) -> None:
    if not (BASE_DIR / ".git").exists():
        return
    files = [f for f in ["capcut_vectors.json", "capcut_dump.txt", "omega_vault.db"] if (BASE_DIR / f).exists()]
    if not files:
        return
    try:
        subprocess.run(["git", "-C", str(BASE_DIR), "add", *files], check=True)
        status = subprocess.run(["git", "-C", str(BASE_DIR), "status", "--porcelain", *files], capture_output=True, text=True, check=True)
        if status.stdout.strip():
            subprocess.run(["git", "-C", str(BASE_DIR), "commit", "-m", f"Sync CapCut 387 1052 vault (+{added_count} vectors)"], check=True)
            subprocess.run(["git", "-C", str(BASE_DIR), "push", "origin", "main"], check=True)
            print("[OK] Архив отправлен в GitHub (Bayashka1234/reality-1)!")
    except subprocess.CalledProcessError as exc:
        print(f"[!] Git push: {exc}")

def main() -> None:
    print("=== ЗАПУСК МОСТА CAPCUT_BRIDGE.PY (387 -> 1052) ===")
    sync_from_downloads()
    cards = load_vectors()
    if not cards:
        print("[i] Нет карточек для синхронизации.")
        return
    added = sync_to_sqlite_and_dump(cards)
    print(f"[OK] Обработано карточек: {len(cards)} | Добавлено новых в omega_vault.db: {added}")
    git_auto_push(added)

if __name__ == "__main__":
    main()
