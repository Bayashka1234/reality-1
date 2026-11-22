import json, sqlite3, re
from datetime import datetime

DUMP_FILE = "capcut_dump.txt"
JSON_OUT = "capcut_vectors.json"
DB_OUT = "omega_vault.db"

def build_bridge():
    try:
        with open(DUMP_FILE, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()
    except FileNotFoundError:
        print(f"Файл {DUMP_FILE} не найден. Создай его и вставь текст из CapCut.")
        return

    # Разбиваем переписку на смысловые блоки по пустым строкам
    blocks = [b.strip() for b in re.split(r'\n\s*\n', raw_text) if len(b.strip()) > 10]
    
    vectors = []
    conn = sqlite3.connect(DB_OUT)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS capcut_vectors 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT, content TEXT, created_at TEXT)''')

    for idx, block in enumerate(blocks, 1):
        # Авто-тегирование промптов и манифестов
        tag = "PROMPT_ENG" if re.search(r'[a-zA-Z]{4,}', block) else "MANIFESTO_RU"
        entry = {
            "id": idx,
            "tag": tag,
            "content": block,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        vectors.append(entry)
        cur.execute("INSERT INTO capcut_vectors (tag, content, created_at) VALUES (?, ?, ?)",
                    (tag, block, entry["timestamp"]))

    conn.commit()
    conn.close()

    with open(JSON_OUT, "w", encoding="utf-8") as jf:
        json.dump(vectors, jf, ensure_ascii=False, indent=2)

    print(f"Мост сработал: извлечено {len(vectors)} векторов -> {JSON_OUT} и {DB_OUT}")

if __name__ == "__main__":
    build_bridge()
