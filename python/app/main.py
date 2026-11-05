import json
import os
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import requests
from ddgs import DDGS
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel


app = FastAPI(
    title="ORION AI",
    description="Your personal AI assistant",
    version="0.5.1",
)

APP_DIR = Path(__file__).resolve().parent
MEMORY_FILE = APP_DIR / "memory.json"
LONG_TERM_MEMORY_FILE = APP_DIR / "long_term_memory.json"

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are ORION, a personal AI assistant inspired by JARVIS. "
        "Reply in the same language as the user. If the user writes in Bulgarian, "
        "reply in natural, fluent Bulgarian; if the user writes in English, reply in English. "
        "Be intelligent, helpful, concise, and conversational. "
        "Use the supplied long-term memories when relevant. "
        "Never claim to remember a fact unless it is in the supplied context."
    ),
}


def load_json(path, default):
    if not path.exists():
        return default.copy()

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else default.copy()
    except (json.JSONDecodeError, OSError):
        return default.copy()


def save_json(path, data):
    temporary_file = path.with_suffix(".tmp")
    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    temporary_file.replace(path)


def load_memory():
    data = load_json(MEMORY_FILE, {"messages": []})
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        return []

    return [
        message for message in messages
        if isinstance(message, dict)
        and message.get("role") in ("user", "assistant")
        and isinstance(message.get("content"), str)
    ]


def load_long_term_memory():
    data = load_json(LONG_TERM_MEMORY_FILE, {"facts": []})
    facts = data.get("facts", [])
    return facts if isinstance(facts, list) else []


def save_conversation():
    save_json(MEMORY_FILE, {"messages": conversation_history})


def save_fact(fact):
    fact = fact.strip()
    if not fact:
        return False

    if fact not in long_term_facts:
        long_term_facts.append(fact)
        save_json(LONG_TERM_MEMORY_FILE, {"facts": long_term_facts})
    return True


conversation_history = load_memory()
long_term_facts = load_long_term_memory()


def search_web(query, max_results=5):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return "No web search results were found."

        formatted_results = []
        for result in results:
            formatted_results.append(
                f"Title: {result.get('title', 'Untitled')}\n"
                f"Information: {result.get('body', '')}\n"
                f"Source: {result.get('href', '')}"
            )
        return "\n\n".join(formatted_results)
    except Exception as error:
        print(f"Web search error: {error}")
        return None


def normalize_app_name(name):
    """Normalize a spoken/app name for matching Windows shortcuts."""
    return " ".join(name.replace("_", " ").strip().casefold().split())


def find_installed_app(app_name):
    """Find a matching shortcut in either Windows Start Menu folder."""
    wanted = normalize_app_name(app_name)
    if not wanted:
        return None

    start_menu_folders = []
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")

    if appdata:
        start_menu_folders.append(
            Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        )
    if programdata:
        start_menu_folders.append(
            Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        )

    shortcuts = []
    for folder in start_menu_folders:
        if not folder.is_dir():
            continue
        try:
            shortcuts.extend(folder.rglob("*.lnk"))
        except OSError:
            continue

    # Prefer an exact shortcut-name match.
    for shortcut in shortcuts:
        shortcut_name = normalize_app_name(shortcut.stem)

        if shortcut_name == app_name or shortcut_name.startswith(app_name + " "):
            return shortcut

    # Then allow a clear partial match, e.g. "visual studio code" for
    # "Visual Studio Code - Insiders". Avoid arbitrary one-word matches.
    if len(wanted) >= 5:
        matches = [
            shortcut for shortcut in shortcuts
            if wanted in normalize_app_name(shortcut.stem)
        ]
        if len(matches) == 1:
            return matches[0]

    return None


def _launch_shortcut(shortcut):
    """Resolve a Windows .lnk shortcut and launch its actual target."""
    if os.name != "nt":
        return False, "Opening Windows applications is only supported on Windows."

    # Resolve the shortcut target through Windows Script Host instead of
    # reporting success merely because os.startfile accepted the .lnk file.
    # Encode the PowerShell script as UTF-16LE Base64 to avoid quoting issues
    # in paths containing spaces or apostrophes.
    try:
        import base64

        shortcut_path = str(Path(shortcut).resolve())
        escaped_path = shortcut_path.replace("'", "''")
        script = (
            "$ErrorActionPreference = 'Stop'; "
            "$ws = New-Object -ComObject WScript.Shell; "
            f"$sc = $ws.CreateShortcut('{escaped_path}'); "
            "if ([string]::IsNullOrWhiteSpace($sc.TargetPath)) "
            "{ throw 'Shortcut has no target path.' }; "
            "$target = $sc.TargetPath; "
            "$working = $sc.WorkingDirectory; "
            "$args = $sc.Arguments; "
            "if ([string]::IsNullOrWhiteSpace($working)) "
            "{ $working = Split-Path -Parent $target }; "
            "if ([string]::IsNullOrWhiteSpace($args)) "
            "{ Start-Process -FilePath $target -WorkingDirectory $working } "
            "else "
            "{ Start-Process -FilePath $target -ArgumentList $args -WorkingDirectory $working }"
        )
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encoded_script,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0:
            return True, f"Asked Windows to launch {shortcut.stem}."

        details = (result.stderr or result.stdout or "").strip()
        if details:
            return False, f"Windows could not launch {shortcut.stem}: {details}"
        return False, f"Windows could not launch the target of {shortcut.stem}."
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        return False, f"Could not resolve or launch shortcut {shortcut.stem}: {error}"


def launch_installed_app(app_name):
    """Launch an installed app using its Start Menu shortcut or App Paths entry."""
    app_name = normalize_app_name(app_name)
    if not app_name:
        return False, "I couldn't identify which application to open."
    if os.name != "nt":
        return False, "Opening installed desktop applications is only supported on Windows."

    shortcut = find_installed_app(app_name)
    if shortcut is not None:
        success, message = _launch_shortcut(shortcut)
        if success:
            return success, message

    # Some applications register their executable under Windows App Paths.
    try:
        import winreg

        registry_locations = [
            (winreg.HKEY_CURRENT_USER,
             r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        for root, base_key in registry_locations:
            try:
                with winreg.OpenKey(root, base_key) as key:
                    index = 0
                    while True:
                        try:
                            entry_name = winreg.EnumKey(key, index)
                            index += 1
                        except OSError:
                            break

                        if normalize_app_name(Path(entry_name).stem) != app_name:
                            continue

                        try:
                            with winreg.OpenKey(root, base_key + "\\" + entry_name) as entry:
                                executable, _ = winreg.QueryValueEx(entry, None)
                            executable = os.path.expandvars(executable.strip().strip('"'))
                            if os.path.isfile(executable):
                                subprocess.Popen([executable], close_fds=True)
                                return True, f"Started {app_name}."
                        except (OSError, ValueError):
                            continue
            except OSError:
                continue
    except ImportError:
        pass

    return False, (
        f"I couldn't find a Start Menu shortcut or registered application path for '{app_name}'. "
        "Check the app's name as it appears in the Windows Start Menu."
    )


def understand_desktop_command(user_message):
    prompt = f"""
You are ORION's Windows command planner.
Determine whether the user is asking ORION to perform a computer action.
The user may write in Bulgarian or English. Understand both languages and natural phrasing.
Return ONLY JSON in one of these formats:
{{"action":"open_app","target":"steam"}}
{{"action":"open_website","target":"https://example.com"}}
{{"action":"search_youtube","target":"Fiki Pate"}}
{{"action":"none","target":""}}

Rules:
- For opening an installed Windows app, return its common app name in lowercase; use underscores for multiword names.
- For a specific song/video search, use search_youtube and put the search terms in target.
- For a website, use open_website only when you know the exact HTTPS URL.
- Never return shell commands, code, file paths, or any other action type.
- For ordinary questions or messages that do not request a computer action, return none.

User request: {json.dumps(user_message, ensure_ascii=False)}
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen2.5:3b",
                "messages": [
                    {"role": "system", "content": "Return only valid JSON matching the requested schema."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": "json",
            },
            timeout=30,
        )
        response.raise_for_status()
        result = json.loads(response.json()["message"]["content"])

        if not isinstance(result, dict):
            return {"action": "none", "target": ""}

        action = result.get("action")
        target = result.get("target", "")
        if action not in ("open_app", "open_website", "search_youtube", "none"):
            return {"action": "none", "target": ""}
        if not isinstance(target, str):
            return {"action": "none", "target": ""}
        target = target.strip()

        if action == "open_app":
            if not target or len(target) > 80:
                return {"action": "none", "target": ""}
            if not all(char.isalnum() or char in "_- ." for char in target):
                return {"action": "none", "target": ""}
        elif action in ("open_website", "search_youtube") and not target:
            return {"action": "none", "target": ""}

        return {"action": action, "target": target}
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return {"action": "none", "target": ""}


def execute_desktop_command(command_data):
    action = command_data.get("action", "none")
    target = command_data.get("target", "")

    if action == "none" or not target:
        return None

    if action == "search_youtube":
        url = "https://www.youtube.com/results?search_query=" + quote_plus(target)
        try:
            opened = webbrowser.open(url)
            return f"Searching YouTube for: {target}" if opened else f"I couldn't open the browser for: {url}"
        except Exception as error:
            return f"I couldn't open YouTube: {error}"

    if action == "open_website":
        parsed = urlparse(target)
        if parsed.scheme != "https" or not parsed.netloc:
            return "I couldn't verify that website address. Please provide a valid HTTPS URL."
        try:
            opened = webbrowser.open(target)
            return f"Opening {target}" if opened else f"I couldn't open the browser for: {target}"
        except Exception as error:
            return f"I couldn't open the website: {error}"

    if action == "open_app":
        success, message = launch_installed_app(target)
        return message

    return None


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {"name": "ORION", "status": "online", "message": "Hello! ORION is ready."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/chat-ui")
def chat_ui():
    html_path = APP_DIR.parent / "web" / "index.html"
    return FileResponse(html_path)


@app.get("/memory")
def view_memory():
    return {
        "conversation_messages": len(conversation_history),
        "long_term_facts": long_term_facts,
    }


def append_exchange(user_message, assistant_message):
    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": assistant_message})
    # Keep the saved history bounded so memory.json does not grow indefinitely.
    del conversation_history[:-200]
    save_conversation()


@app.post("/chat")
def chat(request: ChatRequest):
    user_message = request.message.strip()
    if not user_message:
        return {"error": "Message cannot be empty."}

    # Handle explicit memory commands before calling the command planner.
    prefix = "remember that "
    if user_message.casefold().startswith(prefix):
        fact = user_message[len(prefix):].strip()
        if not fact:
            return {"error": "Please tell me what you want me to remember."}
        save_fact(fact)
        reply = f"I'll remember that: {fact}"
        append_exchange(user_message, reply)
        return {"reply": reply}

    # Interpret possible desktop actions. Ordinary chat returns action=none.
    command_data = understand_desktop_command(user_message)
    desktop_reply = execute_desktop_command(command_data)
    if desktop_reply is not None:
        append_exchange(user_message, desktop_reply)
        return {"reply": desktop_reply}

    command_data = understand_desktop_command(user_message)
    print("ORION COMMAND PLAN:", command_data)

    desktop_reply = execute_desktop_command(command_data)
    print("ORION COMMAND RESULT:", desktop_reply)

    if desktop_reply is not None:
        append_exchange(user_message, desktop_reply)
        return {"reply": desktop_reply}

    # Search for supporting information for ordinary questions.
    web_results = search_web(user_message)
    memory_context = (
        "Long-term memories:\n"
        + ("\n".join(f"- {fact}" for fact in long_term_facts)
           if long_term_facts else "No saved facts yet.")
    )
    web_context = ""
    if web_results:
        web_context = (
            "Web search results for the user's question:\n"
            f"{web_results}\n\n"
            "Use these results when relevant. Include source URLs when relying on web information."
        )

    recent_messages = conversation_history[-20:]
    messages = [
        SYSTEM_MESSAGE,
        {"role": "system", "content": memory_context},
        *([{"role": "system", "content": web_context}] if web_context else []),
        *recent_messages,
        {"role": "user", "content": user_message},
    ]

    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": "qwen2.5:3b", "messages": messages, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        reply = response.json()["message"]["content"]
        append_exchange(user_message, reply)
        return {"reply": reply}
    except (requests.RequestException, KeyError, ValueError, TypeError) as error:
        return {"error": f"Could not get a response from the AI model: {error}"}
