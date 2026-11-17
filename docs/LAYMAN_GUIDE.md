# 💠 The Beginner's Guide to Mercurius Agent
### *A Plain-English Manual on How to Install, Configure, Run, and Love Your Autonomous AI Assistant*

Welcome! You do not need a PhD in artificial intelligence or years of DevOps experience to run Mercurius. 

This guide was written for everyday humans: developers, hobbyists, students, and managers. By the end of this 5-minute guide, you will have your own autonomous AI assistant running on your machine, whether you want to use the cloud (via **Abacus AI ChatLLM**) or run it 100% locally and privately for free (via **Ollama**).

---

## 🐍 Good News: Mercurius is Written in Python!

Almost everything inside Mercurius is built with standard, clean **Python 3**:
- The reasoning engine (`mercurius/core/agent.py`)
- The web browser and calculators (`mercurius/tools/`)
- The health doctor (`mercurius/doctor/doctor.py`)
- The token budget guard (`mercurius/llm/budget.py`)
- The terminal CLI and web server (`mercurius/ui/`)

If you know basic Python, you can read, tweak, and modify any part of Mercurius in minutes.

---

## 🛠️ Step 1: Requirements (What You Need Before Starting)

You only need two things on your computer:
1. **Python 3.10 or higher** (Python 3.11 or 3.12 is great).
   - Check if you have it: Open your terminal and type `python3 --version`.
2. **The Mercurius archive** (`mercurius-agent-complete.zip`).

---

## 📦 Step 2: How to Install Mercurius in 30 Seconds

### On Mac or Linux:
Open your Terminal and run:

```bash
# 1. Unpack the zip file
unzip mercurius-agent-complete.zip

# 2. Go into the folder
cd mercurius

# 3. Run the automated installer
./scripts/install.sh
```

### On Windows:
Open PowerShell or Command Prompt:

```powershell
# 1. Extract the zip file (or right-click -> Extract All)
Expand-Archive mercurius-agent-complete.zip -DestinationPath .

# 2. Go into the folder
cd mercurius

# 3. Install dependencies using pip
pip install -e .
```

*That's it! Mercurius is now installed on your system.*

---

## ⚙️ Step 3: How to Configure Mercurius

Mercurius needs an LLM ("Large Language Model") to do its thinking. You have two fantastic options:
- **Option A:** Use **Abacus AI ChatLLM** (Fast, top-tier cloud models like GPT-6 Astra and Claude Sonnet 5.5).
- **Option B:** Use **Ollama** (100% free, runs completely offline on your computer, private).

---

### Configuration Option A: Using Abacus AI ChatLLM (Cloud)

If you have an Abacus AI account, you only need one single key (`ABACUS_API_KEY`).

#### 1. How to set it:
Create or edit the `.env` file in the `mercurius` folder:

```ini
# Open or create .env in the mercurius directory:
LLM_PROVIDER=chatllm
LLM_MODEL=gpt-4o
ABACUS_API_KEY=your_actual_abacus_api_key_here
```

Or just export it in your terminal:
```bash
export ABACUS_API_KEY="your_actual_abacus_api_key_here"
```

---

### Configuration Option B: Using Ollama (100% Free & Local)

If you want to run completely offline without paying for any API keys or sending data to the cloud, use **Ollama**.

#### 1. Download and install Ollama:
Download Ollama from [ollama.com](https://ollama.com) and install it on your Mac, Windows, or Linux.

#### 2. Download a model:
Open your terminal and pull a model (for example, `llama3` or `hermes3`):
```bash
ollama run llama3
```
*(Leave Ollama running in the background; it serves on `http://localhost:11434`)*

#### 3. Configure Mercurius for Ollama:
Edit the `.env` file in your `mercurius` folder to point to Ollama:

```ini
LLM_PROVIDER=ollama
LLM_MODEL=llama3
# (No API key needed for Ollama!)
```

Or export it in your terminal:
```bash
export LLM_PROVIDER="ollama"
export LLM_MODEL="llama3"
```

---

## 🩺 Step 4: The 5-Second Health Check ("The Doctor")

Before doing work, let Mercurius inspect itself to ensure everything is working:

```bash
# Run the doctor:
./scripts/doctor.sh
# or: python3 -m mercurius.doctor
```

You will see a clean green dashboard:
```text
======================================================================
 💠 Mercurius Diagnostic Doctor (System Health Check)
 System Status: ● HEALTHY  |  Health Score: 100/100
 Total Checks: 14 | Passed: 14 | Warnings: 0 | Failed: 0
======================================================================
```
If anything is missing (like a forgotten API key), the Doctor tells you exactly how to fix it in plain English!

---

## 💻 Step 5: How to Use the Terminal (CLI)

The Command Line Interface (CLI) is perfect if you like working directly in your terminal.

### Launching the Interactive Terminal:
```bash
python3 -m mercurius.ui.cli --interactive
```

Now you are talking directly with Mercurius!

```text
mercurius [mercurius_prime]> Hello! What can you help me with today?
```

### Try These Examples:
1. **Math & Logic:**
   ```text
   mercurius [mercurius_prime]> What is the compound interest on $10,000 at 5% over 10 years?
   ```
2. **Web Browsing & Research:**
   ```text
   mercurius [mercurius_prime]> Visit https://en.wikipedia.org/wiki/Artificial_intelligence and tell me who coined the term.
   ```
3. **Coding & Shell Execution:**
   ```text
   mercurius [mercurius_prime]> Write a python script to count all .txt files in the current directory and run it.
   ```

### Handy Slash Commands inside the Terminal:
- `/doctor` — Run the health check anytime.
- `/budget` — Check your token budget and costs.
- `/switch devops_guru` — Switch the agent's personality to a DevOps engineer.
- `/tools` — See all the 21 tools Mercurius knows how to use.
- `/exit` — Quit gracefully.

---

## 🌐 Step 6: How to Use the Web Dashboard (UI)

If you prefer clicking buttons and seeing charts in a web browser, Mercurius has a built-in Mission Control Dashboard!

### 1. Start the Web Server:
In your terminal, run:
```bash
./scripts/start.sh
# or: python3 -m mercurius.ui.server --host 0.0.0.0 --port 8000
```

You will see:
```text
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 2. Open Your Browser:
Go to: **`http://localhost:8000`**

### 3. What You Can Do in the Web Dashboard:
- **Chat Box:** Type any question or task, just like ChatGPT, but Mercurius can browse the web and run tools.
- **System Health Monitor:** See live green badges showing CPU, database, and tool status.
- **Token Budget Progress Bar:** Watch your token usage in real time. If a model reaches its limit, click **"Overwrite"** to unlock it with one click.
- **Live Tool Feed:** Watch Mercurius think in real time (`<thought>`), see which websites it visits, and see cached responses return in 0.1 milliseconds!

---

## 🚀 Step 7: How to Deploy Mercurius for Production

Want to leave Mercurius running 24/7 on a home server, VPS, or cloud instance?

### Option 1: Using Docker (Recommended for Servers)
Mercurius includes a pre-configured Docker Compose file:

```bash
cd deploy
docker-compose up -d
```
That's it! Mercurius is now running inside an isolated container, auto-restarting if your machine reboots.

### Option 2: Running in Background on Linux (systemd)
Create a background service file at `/etc/systemd/system/mercurius.service`:

```ini
[Unit]
Description=Mercurius AI Assistant
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/mercurius
Environment=ABACUS_API_KEY="your_api_key"
ExecStart=/usr/bin/python3 -m mercurius.ui.server --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start it:
```bash
sudo systemctl enable mercurius
sudo systemctl start mercurius
```

---

## ❓ Frequently Asked Questions (FAQ)

**Q: Do I have to pay to use Mercurius?**  
**A:** No! Mercurius is 100% open-source. If you run it with **Ollama**, it is completely free to use offline on your own machine. If you use cloud providers like **Abacus AI**, you only pay standard API token rates.

**Q: Where is my data saved?**  
**A:** Everything is saved locally on your computer inside the `./data/` folder (such as `data/mercurius_memory.sqlite`). Your data never leaves your computer unless you send it to a cloud LLM provider.

**Q: What if Mercurius gets stuck?**  
**A:** Run `/doctor` in the CLI or visit the web dashboard. The Doctor will pinpoint the exact issue (e.g. database locked, missing internet connection, or exhausted token quota).
