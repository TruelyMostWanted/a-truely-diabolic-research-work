import json
import re
from typing import Any, Dict, List, Optional

RESPONSE_RE = re.compile(r'"response"\s*:\s*"(?P<resp>(?:\\.|[^"\\])*)"', re.UNICODE)

def _safe_json_loads(line: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(line)
    except Exception:
        return None

def stitch_assistant_text(content: Any) -> str:
    parts: List[str] = []

    if isinstance(content, str):
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            data = _safe_json_loads(line)
            if data and isinstance(data, dict):
                # Falls OpenAI-kompatibel:
                message = data.get("message", {})
                if isinstance(message, dict) and "content" in message:
                    parts.append(str(message["content"]))
                    continue
                # Falls Direktantwort:
                if "response" in data:
                    parts.append(str(data["response"]))
                    continue
            # Fallback: regex
            for m in RESPONSE_RE.finditer(line):
                frag = m.group("resp").encode("utf-8").decode("unicode_escape")
                parts.append(frag)

    elif isinstance(content, dict) and "text" in content and isinstance(content["text"], str):
        return stitch_assistant_text(content["text"])  # Rekursiv

    return "".join(parts)

def maybe_collapse_blank_lines(s: str) -> str:
    return re.sub(r'\n{3,}', '\n\n', s)

def main():
    with open("chat.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    chat = data.get("chat", [])
    dialog: List[str] = []

    i = 0
    while i < len(chat):
        entry = chat[i]
        if entry.get("role") == "user":
            user_text = entry.get("content", "").strip()
            user_text = maybe_collapse_blank_lines(user_text)

            # Finde direkt folgende Assistant-Antwort (wenn vorhanden)
            assistant_text = ""
            if i + 1 < len(chat) and chat[i + 1].get("role") == "assistant":
                assistant_text = stitch_assistant_text(chat[i + 1].get("content"))
                assistant_text = assistant_text.strip()
                assistant_text = maybe_collapse_blank_lines(assistant_text)
                i += 1  # überspringe Assistant im nächsten Loop

            # Formatierter Block
            block = (
                "────────────────────────────\n"
                "USER:\n" + user_text + "\n\n" +
                "ASSISTANT:\n" + assistant_text + "\n"
            )
            dialog.append(block)
        i += 1

    output_text = "\n".join(dialog)
    with open("chat.txt", "w", encoding="utf-8") as f_out:
        f_out.write(output_text if output_text.endswith("\n") else output_text + "\n")

if __name__ == "__main__":
    main()
