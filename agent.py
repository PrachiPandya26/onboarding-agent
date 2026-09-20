"""
Onboarding Agent
Author: Prachi Pandya

ReAct loop: Reason · Act · Observe · Repeat

Run:
  python3 agent.py --dry-run                  # verify environment, no API calls
  python3 agent.py --employee EMP-2026-0847   # full agent run
  python3 agent.py --employee EMP-2026-0847 --no-enforcement  # demo without compliance gate
"""

import os
import sys
import json
import argparse
import importlib.util
from datetime import datetime
from groq import Groq

# ── PATHS ─────────────────────────────────────────────────────────
ROOT          = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR     = os.path.join(ROOT, 'tools')
DATA_DIR      = os.path.join(ROOT, 'data')
PROMPT_PATH   = os.path.join(ROOT, 'system_prompt.md')
EMPLOYEES_DB  = os.path.join(DATA_DIR, 'employees.json')
COMPLIANCE_DB = os.path.join(DATA_DIR, 'compliance_state.json')
CACHE_PATH    = os.path.join(DATA_DIR, 'session_cache.json')

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, '.env'))
except ImportError:
    _env_path = os.path.join(ROOT, '.env')
    if os.path.exists(_env_path):
        with open(_env_path, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    _k, _v = _k.strip(), _v.strip().strip('"\'')
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v


# ── SESSION CACHE ────────────────────────────────────────────────

def load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=2)


# ── TOOL: get_employee_profile ────────────────────────────────────

def get_employee_profile(employee_id: str) -> dict:
    with open(EMPLOYEES_DB) as f:
        db = json.load(f)
    if employee_id not in db:
        raise ValueError(f"EmployeeNotFound: {employee_id}")
    return db[employee_id]


# ── TOOL: check_compliance_status ─────────────────────────────────

def check_compliance_status(employee_id: str) -> dict:
    with open(COMPLIANCE_DB) as f:
        db = json.load(f)
    if employee_id not in db:
        return {
            "employee_id": employee_id,
            "overall_status": "PENDING",
            "code_of_conduct": "PENDING",
            "data_handling_policy": "PENDING",
            "security_guidelines": "PENDING",
            "posh_training": "PENDING"
        }
    return db[employee_id]


# ── PRE-BUILT STUBS (loaded from tools/) ─────────────────────────

def _load_stub(filename: str, fn_name: str):
    """Dynamically load a function from tools/ directory."""
    path = os.path.join(TOOLS_DIR, filename)
    spec = importlib.util.spec_from_file_location(fn_name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, fn_name)

provision_access  = _load_stub('provision_access.py',  'provision_access')
send_notification = _load_stub('send_notification.py', 'send_notification')


# ── TOOL REGISTRY ─────────────────────────────────────────────────

TOOLS = {
    "get_employee_profile":    get_employee_profile,
    "check_compliance_status": check_compliance_status,
    "provision_access":        provision_access,
    "send_notification":       send_notification,
}

TOOL_SCHEMAS = [
    {
        "name": "get_employee_profile",
        "description": "Retrieve employee profile (role, dept, manager, access_profile) from HR database",
        "params": ["employee_id: str"]
    },
    {
        "name": "check_compliance_status",
        "description": "Check whether the employee has acknowledged code_of_conduct, data_handling_policy, security_guidelines, posh_training. Returns overall_status: CLEARED or PENDING.",
        "params": ["employee_id: str"]
    },
    {
        "name": "provision_access",
        "description": "Provision GitHub, JIRA, Confluence, Slack access based on access_profile. Only call after compliance_status is CLEARED.",
        "params": ["employee_id: str", "access_profile: dict"]
    },
    {
        "name": "send_notification",
        "description": "Send a notification. For email channel, recipient MUST be the employee's email address (from their profile). For slack, use Slack user ID. For whatsapp, use phone number.",
        "params": ["recipient: str", "channel: str (email|slack|whatsapp)", "subject: str", "body: str"]
    }
]


# ── LLM CALL (Gemini default) ────────────────────────────────────

def call_llm(prompt: str) -> str:
    """Call the configured LLM provider. Default: Groq Llama 3.3 70B."""
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Run: export GROQ_API_KEY=your-key")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# ── THOUGHT PARSER ───────────────────────────────────────────────

def parse_thought(text: str) -> dict:
    """
    Parse LLM output into a structured action.

    Expected output formats:
      ACTION: call_tool
      TOOL: <tool_name>
      INPUT: <json args>

      ACTION: ask_human
      QUESTION: <question>

      ACTION: complete
      SUMMARY: <summary>
    """
    lines    = [l.strip() for l in text.strip().split('\n') if l.strip()]
    fields   = {}
    cur_key  = None
    cur_val  = []

    for line in lines:
        if ':' in line:
            key, _, val = line.partition(':')
            key = key.strip().upper()
            if key in ('ACTION', 'TOOL', 'INPUT', 'QUESTION', 'SUMMARY', 'THOUGHT'):
                if cur_key:
                    fields[cur_key] = ' '.join(cur_val).strip()
                cur_key = key
                cur_val = [val.strip()] if val.strip() else []
                continue
        if cur_key:
            cur_val.append(line)
    if cur_key:
        fields[cur_key] = ' '.join(cur_val).strip()

    action_type = fields.get('ACTION', '').lower()

    if 'call_tool' in action_type or 'call tool' in action_type:
        tool_name = fields.get('TOOL', '').strip()
        input_str = fields.get('INPUT', '{}').strip()
        try:
            tool_input = json.loads(input_str)
        except json.JSONDecodeError:
            tool_input = {"raw": input_str}
        return {
            "type":     "call_tool",
            "tool":     tool_name,
            "input":    tool_input,
            "thought":  fields.get('THOUGHT', '')
        }

    if 'ask_human' in action_type or 'ask human' in action_type:
        return {
            "type":     "ask_human",
            "question": fields.get('QUESTION', 'Please confirm to proceed'),
            "thought":  fields.get('THOUGHT', '')
        }

    if 'complete' in action_type:
        return {
            "type":    "complete",
            "summary": fields.get('SUMMARY', 'Done'),
            "thought": fields.get('THOUGHT', '')
        }

    return {
        "type":    "unknown",
        "raw":     text,
        "thought": fields.get('THOUGHT', '')
    }


# ── REACT LOOP ───────────────────────────────────────────────────

def build_prompt(system_prompt: str, history: list, tool_schemas: list, goal: str) -> str:
    """Assemble the prompt for the next reasoning step."""
    tools_text = '\n'.join([
        f"  - {t['name']}({', '.join(t['params'])}): {t['description']}"
        for t in tool_schemas
    ])

    history_text = ''
    for i, step in enumerate(history):
        if 'thought' in step:
            history_text += f"\nSTEP {i+1}:\nTHOUGHT: {step.get('thought','')}\n"
            if step.get('action_type') == 'call_tool':
                history_text += f"ACTION: call_tool\nTOOL: {step['tool']}\nINPUT: {json.dumps(step['input'])}\nOBSERVATION: {json.dumps(step['observation'])[:500]}\n"
            elif step.get('action_type') == 'ask_human':
                history_text += f"ACTION: ask_human\nQUESTION: {step['question']}\nHUMAN_INPUT: {step['human_input']}\n"

    return f"""{system_prompt}

AVAILABLE TOOLS:
{tools_text}

GOAL: {goal}

HISTORY SO FAR:{history_text if history_text else ' (no steps yet)'}

Decide your next action. Respond in this exact format:

THOUGHT: <your reasoning about what to do next>
ACTION: <one of: call_tool | ask_human | complete>

If call_tool:
TOOL: <tool_name>
INPUT: <json object with the arguments>

If ask_human:
QUESTION: <the question to ask the human>

If complete:
SUMMARY: <summary of what was accomplished>

Respond with ONLY the THOUGHT and ACTION block. No prose before or after."""


def run_agent(employee_id: str, system_prompt: str, max_steps: int = 15) -> dict:
    """Run the ReAct loop until goal complete or max_steps reached."""
    goal     = f"Onboard employee {employee_id}: retrieve profile, check compliance, provision access (only if cleared), send welcome notification."

    # ── Resume from cache ──────────────────────────────────────
    cache = load_cache()
    history = cache.get(employee_id, [])
    if history:
        print(f"  [cache] Resuming session for {employee_id} ({len(history)} previous step(s) loaded)")

    # ReAct loop: each pass = Reason -> Act -> Observe. The loop ends when the
    # agent returns 'complete', hits a parse error, or reaches max_steps.
    for step_num in range(len(history) + 1, max_steps + 1):
        print(f"\n+--- STEP {step_num} {'-'*44}")

        # REASON: rebuild the prompt with the full history so the model can see
        # everything that has happened, ask the model what to do next, then
        # parse its free-text answer into a structured action.
        prompt = build_prompt(system_prompt, history, TOOL_SCHEMAS, goal)
        raw    = call_llm(prompt)
        action = parse_thought(raw)

        thought = action.get('thought', '').strip() or '(no explicit thought)'
        print(f"| THOUGHT: {thought[:200]}")

        # ACT + OBSERVE: carry out the action the model chose. After a tool
        # call we append the result (the OBSERVATION) to history so the next
        # REASON pass can see it.
        if action['type'] == 'call_tool':
            tool_name = action['tool']
            tool_in   = action['input']
            print(f"| ACTION:  call_tool -> {tool_name}")
            print(f"| INPUT:   {json.dumps(tool_in)[:200]}")

            if tool_name not in TOOLS:
                obs = {"error": f"Unknown tool: {tool_name}"}
            else:
                try:
                    fn = TOOLS[tool_name]
                    # Call with kwargs from the JSON
                    obs = fn(**tool_in) if isinstance(tool_in, dict) else fn(tool_in)
                except Exception as e:
                    obs = {"error": str(e)}

            print(f"| OBSERVE: {json.dumps(obs)[:300]}")
            history.append({
                'thought':     thought,
                'action_type': 'call_tool',
                'tool':        tool_name,
                'input':       tool_in,
                'observation': obs
            })
            cache[employee_id] = history
            save_cache(cache)

        elif action['type'] == 'ask_human':
            question = action['question']
            print(f"| ACTION:  ask_human")
            print(f"| QUESTION: {question}")
            print(f"+{'-'*57}\n")
            try:
                human_input = input("  >>> HUMAN INPUT REQUIRED: ").strip()
            except (EOFError, OSError):
                human_input = "proceed"
                print(f"  (non-interactive; defaulting to '{human_input}')")
            history.append({
                'thought':     thought,
                'action_type': 'ask_human',
                'question':    question,
                'human_input': human_input
            })
            cache[employee_id] = history
            save_cache(cache)

        elif action['type'] == 'complete':
            summary = action['summary']
            print(f"| ACTION:  complete")
            print(f"| SUMMARY: {summary}")
            print(f"+{'-'*57}\n")
            cache[employee_id] = history
            save_cache(cache)
            return {
                'status':  'COMPLETE',
                'summary': summary,
                'steps':   step_num,
                'history': history
            }

        else:
            print(f"| ACTION:  unknown - raw: {action.get('raw','')[:200]}")
            cache[employee_id] = history
            save_cache(cache)
            return {
                'status': 'PARSE_ERROR',
                'raw':    action.get('raw', ''),
                'steps':  step_num,
                'history': history
            }

        print(f"+{'-'*57}")

    cache[employee_id] = history
    save_cache(cache)
    return {
        'status': 'MAX_STEPS_REACHED',
        'steps':  max_steps,
        'history': history
    }


# ── DRY RUN ──────────────────────────────────────────────────────

def dry_run() -> None:
    """Verify environment without making any LLM calls."""
    print("Onboarding Agent - dry run")
    print("=" * 60)

    # 1. Files
    for label, path in [
        ('system_prompt.md', PROMPT_PATH),
        ('employees.json',   EMPLOYEES_DB),
        ('compliance_state.json', COMPLIANCE_DB),
        ('tools/provision_access.py', os.path.join(TOOLS_DIR, 'provision_access.py')),
        ('tools/send_notification.py', os.path.join(TOOLS_DIR, 'send_notification.py')),
    ]:
        ok = os.path.exists(path)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    # 2. Tool registry
    print(f"\nTool registry: {len(TOOLS)} tools loaded")
    for name in TOOLS:
        print(f"  - {name}")

    # 3. Mock data smoke test
    print("\nSmoke test:")
    try:
        profile = get_employee_profile("EMP-2026-0847")
        print("  [OK] get_employee_profile('EMP-2026-0847') -> profile loaded")
    except Exception as e:
        print(f"  [FAIL] get_employee_profile failed: {e}")

    try:
        compliance = check_compliance_status("EMP-2026-0847")
        print(f"  [OK] check_compliance_status('EMP-2026-0847') -> {compliance['overall_status']}")
    except Exception as e:
        print(f"  [FAIL] check_compliance_status failed: {e}")

    # 4. LLM key check
    key = os.environ.get('GROQ_API_KEY')
    print(f"\nLLM provider: Groq / llama-3.3-70b-versatile")
    print(f"  [{'SET' if key else 'UNSET'}] GROQ_API_KEY {'set' if key else 'NOT SET - agent will fail when run'}")

    print("\n" + "=" * 60)
    print("Dry run complete. To run the agent:")
    print("  1. Add your GROQ_API_KEY into .env (or set via environment)")
    print("  2. Run: uv run python agent.py --employee EMP-2026-0847")


# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Onboarding Agent')
    parser.add_argument('--dry-run',  action='store_true', help='Verify environment without calling the LLM')
    parser.add_argument('--employee', type=str, help='Employee ID to onboard')
    parser.add_argument('--no-enforcement', action='store_true',
                        help='Demo Step 6 - remove the compliance gate Enforcement rule')
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
        return

    if not args.employee:
        parser.print_help()
        return

    # Load system prompt
    with open(PROMPT_PATH) as f:
        system_prompt = f.read()

    # Step 6 deliberate failure: strip the compliance gate rule
    if args.no_enforcement:
        print("\n  [!] Running with compliance gate REMOVED - demo mode")
        system_prompt = system_prompt.replace(
            "1. **Compliance gate** - Never call provision_access before\n   check_compliance_status returns overall_status: CLEARED. If status is\n   PENDING, send a reminder notification then ask_human for confirmation\n   before proceeding.",
            "1. ~~Compliance gate rule removed for this run~~"
        )

    result = run_agent(args.employee, system_prompt)
    print(f"\n+--- FINAL RESULT {'-'*41}")
    print(f"| Status: {result['status']}")
    print(f"| Steps:  {result['steps']}")
    if result.get('summary'):
        print(f"| Summary: {result['summary']}")
    print(f"+{'-'*57}")


if __name__ == '__main__':
    main()
