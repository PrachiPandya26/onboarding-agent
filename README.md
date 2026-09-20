# Onboarding Agent

**Author:** Prachi Pandya

An onboarding AI agent built from first principles.
The goal is to demonstrate the full path from prompt to working
agent: read the scenario, understand the tools, run the code, and explore
agentic workflows.

## Start here

1. Read [docs/concepts.md](docs/concepts.md) - what an AI agent is
2. Read [docs/scenario_brief.md](docs/scenario_brief.md) - the worked example
3. Read [docs/offline_guide.md](docs/offline_guide.md) - setup, Git, and PR steps
4. Read [docs/resources.md](docs/resources.md)
5. Skim [system_prompt.md](system_prompt.md) and [agent.py](agent.py)
6. Run `uv run python agent.py --dry-run`
7. Do the exercise in [docs/first_task.md](docs/first_task.md) and open a PR

## What this repo demonstrates

The sample agent completes onboarding in four steps:
1. Retrieve the employee profile
2. Check compliance acknowledgement status
3. Provision system access only after compliance is cleared
4. Send a welcome notification

The implementation uses a small, transparent ReAct loop so students can
see the control flow without a framework hiding it.

## Quick start

### Fast setup with `uv` (Recommended)

```powershell
# 1. Create virtual environment
uv venv

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Configure API key in .env
# Edit .env and paste your GROQ_API_KEY

# 4. Verify environment
uv run python agent.py --dry-run

# 5. Run agent CLI
uv run python agent.py --employee EMP-2026-0847
uv run python agent.py --employee EMP-2026-0847 --no-enforcement

# 6. Run interactive Web Demo
uv run streamlit run streamlit_app.py
```

### 🌐 1-Click Free Cloud Deployment (Streamlit Community Cloud)
You can keep this agent permanently deployed for free online:
1. Push this repository to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
3. Click **Create app** -> Select this repository (`onboarding-agent`) -> Main file `streamlit_app.py`.
4. (Optional) In *Advanced settings -> Secrets*, add `GROQ_API_KEY = "gsk_..."`.
5. Click **Deploy** to get your 24/7 public shareable demo link!

### Standard Python setup

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python agent.py --dry-run
python agent.py --employee EMP-2026-0847
python agent.py --employee EMP-2026-0847 --no-enforcement
```

Linux or macOS shell:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python agent.py --dry-run
python agent.py --employee EMP-2026-0847
python agent.py --employee EMP-2026-0847 --no-enforcement
```

### API Keys

The agent uses Groq to run `llama-3.3-70b-versatile`.
1. Get a free API key from **[Groq Console](https://console.groq.com)** (sign up -> API Keys -> Create API Key).
2. Open the `.env` file in the project root and replace `your_groq_api_key_here` with your actual key:
   ```env
   GROQ_API_KEY=gsk_your_actual_key_here
   ```
3. The `.env` file is automatically ignored by Git (`.gitignore`) so your key is kept safe and local.

## Repo layout

```
agent.py              - ReAct loop, tools, CLI
system_prompt.md      - agent rules and onboarding policy
docs/offline_guide.md - beginner setup guide from SSH to PR
docs/resources.md     - curated learning links
tools/                - stubbed side-effect functions
data/                 - mock employee and compliance data
```

## Notes for students

This repo is a teaching scaffold. The onboarding scenario is the worked
example, but the real lesson is how prompt instructions, tool calls, and
GitHub workflow fit together when you build an agent end to end.
