# ORION – Personal AI Assistant

<p align="center">

  **Your personal AI assistant for Windows**

  An intelligent assistant designed to interact with your computer, execute desktop commands and provide an AI-powered conversational experience.

</p>

---

## About the Project

**ORION** is a personal AI assistant developed in Python, inspired by the concept of J.A.R.V.I.S.

The main goal of the project is to create an intelligent assistant that can understand natural language, communicate with the user and interact with the Windows operating system.

ORION combines a local Large Language Model (LLM) with a Python backend to process requests and execute supported commands.

This project is actively under development.

## Features

- **AI Conversation** – communicate with ORION using natural language.
- **Desktop Automation** – execute supported commands on Windows.
- **Application Launching** – open installed applications.
- **Website Navigation** – open websites using natural language commands.
- **YouTube Search** – search for videos directly through ORION.
- **Persistent Memory** – maintain conversation context using local memory files.
- **Web Interface** – interact with ORION through a browser-based chat interface.
- **Local AI Processing** – use Ollama to run a local language model.

## Technologies

| Technology | Purpose |
|---|---|
| Python 3.13 | Main programming language |
| FastAPI | Backend framework |
| Ollama | Local AI model runtime |
| Qwen 2.5 3B | Language model |
| HTML | Web interface |
| JavaScript | Frontend interactions |
| Git & GitHub | Version control |

## Project Structure

```text
ORION/
│
├── python/
│   ├── app/
│   │   ├── brain.py
│   │   ├── commands.py
│   │   └── main.py
│   │
│   ├── web/
│   │   └── index.html
│   │
│   └── main.py
│
├── Start_ORION.bat
├── .gitignore
└── README.md
```

## Requirements

Before running ORION, make sure you have:

- Windows 10 or Windows 11
- Python 3.13 (64-bit)
- Ollama installed
- Qwen 2.5 3B model downloaded

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/VIKTOR40HA/ORION.git
```

**2. Navigate to the project directory**

```bash
cd ORION
```

**3. Create a virtual environment**

```bash
python -m venv .venv313
```

**4. Activate the virtual environment**

```bash
.venv313\Scripts\activate
```

**5. Install the required dependencies**

Install the Python packages required by the project.

**6. Download the AI model**

Make sure Ollama is running and execute:

```bash
ollama pull qwen2.5:3b
```

## Running ORION

Start the FastAPI backend from the project root:

```powershell
.\.venv313\Scripts\python.exe -m uvicorn app.main:app --app-dir python --host 127.0.0.1 --port 8000
```

Open the web interface in your browser:

```text
http://127.0.0.1:8000/chat-ui
```

Make sure Ollama is running before starting ORION.

## Development

ORION is an ongoing personal development project.

Future development goals include:

- Improved natural language understanding.
- More advanced Windows automation.
- Better long-term memory management.
- Voice interaction.
- Remote access from multiple devices.
- Integration with additional services and tools.
- Improved user interface and experience.

## Author

**Viktor Bechev**

First-year Software Engineering student at Plovdiv University "Paisii Hilendarski".

GitHub: [@VIKTOR40HA](https://github.com/VIKTOR40HA)

---

*ORION – A personal AI assistant, built from the ground up.*
