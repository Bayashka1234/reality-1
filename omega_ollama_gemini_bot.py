import asyncio
import os
import sys
from collections import defaultdict
from pathlib import Path
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJ_DIR = Path(r"D:\Projects\reality-1")
if str(PROJ_DIR) not in sys.path:
    sys.path.insert(0, str(PROJ_DIR))

from capcut_bridge import load_capcut_387_chat

def load_env() -> dict:
    env = dict(os.environ)
    env_file = Path(r"C:\Users\Bayas\.env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env

CFG = load_env()
BOT_TOKEN = CFG.get("TELEGRAM_BOT_TOKEN") or ""
GEMINI_KEY = CFG.get("GEMINI_API_KEY") or ""
OPENROUTER_KEY = CFG.get("OPENROUTER_API_KEY") or ""
PREFERRED_OLLAMA = CFG.get("OLLAMA_MODEL") or "architect-local:latest"
TG_API_BASE = "https://api." + "telegram.org" + "/bot" + BOT_TOKEN

SYSTEM_PROMPT = (
    "Ты — ИИ-ассистент проекта «Dream the Muse // Архитектор 387 → 1052» "
    "(канал CapCut ID: id0184534066). Отвечай глубоко, точно и по делу на языке пользователя."
)

CHAT_HISTORY: dict[int, list[dict]] = defaultdict(list)

async def ask_ai(client: httpx.AsyncClient, chat_id: int, user_text: str) -> str:
    history = CHAT_HISTORY[chat_id]
    history.append({"role": "user", "text": user_text})
    if len(history) > 10:
        del history[:-10]

    # 1. Локальная Ollama (architect-local:latest / qwen3:4b)
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=2.5) as local_cli:
            tags_res = await local_cli.get("http://127.0.0")
            if tags_res.status_code == 200:
                models = [m["name"] for m in tags_res.json().get("models", [])]
                model_name = next((m for m in models if PREFERRED_OLLAMA in m), models[0] if models else None)
                if model_name:
                    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + [
                        {"role": "assistant" if m["role"] == "model" else "user", "content": m["text"]}
                        for m in history
                    ]
                    async with httpx.AsyncClient(trust_env=False, timeout=60.0) as gen_cli:
                        res = await gen_cli.post(
                            "http://127.0.0",
                            json={"model": model_name, "stream": False, "messages": msgs},
                        )
                    if res.status_code == 200:
                        reply = res.json().get("message", {}).get("content", "").strip()
                        if reply:
                            history.append({"role": "model", "text": reply})
                            return f"{reply}\n\n[⚡ Ollama · {model_name}]"
    except Exception:
        pass

    # 2. Резерв: Google Gemini (если указан AIza...)
    if GEMINI_KEY.startswith("AIza"):
        try:
            res = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
                json={
                    "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in history],
                },
                timeout=30.0,
            )
            if res.status_code == 200:
                reply = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if reply:
                    history.append({"role": "model", "text": reply})
                    return f"{reply}\n\n[⚡ Google Gemini]"
        except Exception:
            pass

    # 3. Резерв: OpenRouter (:free) по вашему ключу sk-or-...
    if OPENROUTER_KEY.startswith("sk-or-"):
        try:
            msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + [
                {"role": "assistant" if m["role"] == "model" else "user", "content": m["text"]}
                for m in history
            ]
            res = await client.post(
                "https://openrouter.ai",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                json={"model": "openrouter/free", "messages": msgs},
                timeout=30.0,
            )
            if res.status_code == 200:
                reply = res.json()["choices"][0]["message"]["content"].strip()
                if reply:
                    history.append({"role": "model", "text": reply})
                    return f"{reply}\n\n[⚡ OpenRouter Free]"
        except Exception:
            pass

    return "ИИ-движки временно не ответили. Проверьте службу Ollama."

async def connect_tg() -> httpx.AsyncClient:
    for proxy_url in ("socks5h://127.0.0.1:10808", "socks5://127.0.0.1:10808", "http://127.0.0.1:10808", None):
        cli = httpx.AsyncClient(proxy=proxy_url, trust_env=False, timeout=35.0)
        try:
            r = await cli.get(f"{TG_API_BASE}/getMe", timeout=8.0)
            if r.status_code == 200 and r.json().get("ok"):
                print(f"[OK] Telegram подключён ({proxy_url or 'напрямую'}) -> @{r.json()['result']['username']}")
                return cli
            else:
                print(f"[WARN] {proxy_url}: HTTP {r.status_code} -> {r.text[:120]}")
        except Exception as e:
            print(f"[WARN] {proxy_url}: {type(e).__name__}: {e}")
        await cli.aclose()
    raise RuntimeError("Нет доступа к Telegram API ни по одному из режимов 127.0.0.1:10808.")

async def main():
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        print("[ОШИБКА] Некорректный TELEGRAM_BOT_TOKEN в C:\\Users\\Bayas\\.env!")
        return

    client = await connect_tg()
    try:
        await client.get(f"{TG_API_BASE}/deleteWebhook")
        print("[OK] Бот @MuseArchitect3871052_bot запущен (Ollama architect-local + Gemini/OpenRouter)!")
        offset = 0
        while True:
            try:
                res = await client.get(f"{TG_API_BASE}/getUpdates", params={"offset": offset, "timeout": 25})
                for upd in res.json().get("result", []):
                    offset = upd["update_id"] + 1
                    iq = upd.get("inline_query")
                    if iq and iq.get("id"):
                        q_text = (iq.get("query") or "").strip()
                        if q_text:
                            ans = await ask_ai(client, iq["from"]["id"], q_text)
                            results = [{
                                "type": "article",
                                "id": str(upd["update_id"]),
                                "title": f"Архитектор Ω: {q_text[:45]}",
                                "description": ans[:120],
                                "input_message_content": {"message_text": ans[:4000]}
                            }]
                            await client.post(
                                f"{TG_API_BASE}/answerInlineQuery",
                                json={"inline_query_id": iq["id"], "results": results, "cache_time": 10}
                            )
                        continue
                    msg = upd.get("message") or {}
                    chat_id = msg.get("chat", {}).get("id")
                    text = (msg.get("text") or "").strip()
                    if not chat_id or not text:
                        continue
                    low = text.lower()
                    if low.startswith("/reset"):
                        CHAT_HISTORY[chat_id].clear()
                        reply = "Память диалога очищена."
                    elif low.startswith(("/capcut", "/trends")):
                        reply = await load_capcut_387_chat(limit=10, include_dialogues=True)
                    elif low.startswith(("/start", "/menu")):
                        reply = (
                            "⚡ АРХИТЕКТОР 387 → 1052 · ИИ-РЕЖИМ АКТИВЕН\n"
                            "• Движок: Ollama (architect-local) + Google Gemini / OpenRouter\n"
                            "• /capcut — сводка векторов и диалогов (id0184534066)\n"
                            "• /reset — сбросить контекст беседы"
                        )
                    else:
                        await client.post(f"{TG_API_BASE}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                        reply = await ask_ai(client, chat_id, text)

                    for i in range(0, len(reply), 4000):
                        await client.post(f"{TG_API_BASE}/sendMessage", json={"chat_id": chat_id, "text": reply[i:i+4000]})
            except Exception:
                await asyncio.sleep(3)

    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())


