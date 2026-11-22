# Capivara IA

**An autonomous AI agent with a body: a capybara that explores the web, thinks out loud on a chalkboard, and keeps what it learns.**

## The idea

Capivara IA is a capybara living in a small 3D world, driven by an AI brain. On its own, it researches topics on the internet, sketches ideas on a chalkboard, and saves its discoveries as text and drawings. You can watch it work in real time.

## Architecture

The project has three parts:

| Part | Tech | Responsibility |
|------|------|----------------|
| **World** | Godot 4 | Renders the 3D world and animates the capybara. No AI logic lives here. |
| **Brain** | Python | Runs the agent loop: decides what to do next, calls tools (web search, drawing, saving), and talks to the LLM. |
| **Memory** | Markdown + ChromaDB | Keeps everything the capybara has learned, both for humans and for the agent. |

World and Brain talk over a WebSocket using validated JSON messages. The Brain follows a layered architecture (domain → application → infrastructure), so LLM providers and tools can be swapped without touching the agent's rules.

### Memory

Memory has two layers:

- **Discoveries:** human-readable Markdown files in `discoveries/`. Anyone can browse what the capybara has found.
- **Vector index:** a ChromaDB index over those discoveries, used for semantic search.

Before deciding what to do next, the capybara queries its memory using RAG (retrieval-augmented generation), so new research builds on what it already knows.

## Stack

- **World:** Godot 4, GDScript
- **Brain:** Python 3.12, Pydantic, WebSocket
- **LLMs:** Ollama (local), Claude, OpenAI, behind a single interface
- **Memory:** ChromaDB, Markdown
- **Quality:** pytest, ruff, mypy (strict)

## Getting started

### Prerequisites

- [Python 3.12+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download) with the `llama3.1:8b` model:

  ```bash
  ollama pull llama3.1:8b
  ```

### Setup

Create and activate a virtual environment, then install the dependencies (`--group` requires pip 25.1+):

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install --group dev .
Copy-Item brain\.env.example brain\.env
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install --group dev .
cp brain/.env.example brain/.env
```

### Talk to the capybara

Make sure Ollama is running, then (same on all platforms):

```bash
cd brain
python -m src.chat_with_capybara
```

Type `sair` to leave the chat.

### Run the tests

From the project root:

```bash
pytest
ruff check .
mypy brain/src
```

## Status

🚧 Early stage. The project structure and tooling are in place; the agent loop, the 3D world, and memory are under active development.
