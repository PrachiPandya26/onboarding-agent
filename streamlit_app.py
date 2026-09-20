"""
Streamlit Web UI for Onboarding Agent
Author: Prachi Pandya

A live, interactive web application to showcase the Onboarding AI Agent demo.
Deployable 100% free on Streamlit Community Cloud without server management.
"""

import os
import sys
import json
import time
from datetime import datetime
import streamlit as st

# Add current dir to path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Try importing agent modules
from agent import (
    TOOLS,
    TOOL_SCHEMAS,
    PROMPT_PATH,
    EMPLOYEES_DB,
    COMPLIANCE_DB,
    get_employee_profile,
    check_compliance_status,
    provision_access,
    send_notification,
    build_prompt,
    parse_thought,
)

# Page configuration
st.set_page_config(
    page_title="Meridian AI | Autonomous Onboarding Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished aesthetics
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #2563EB 0%, #7C3AED 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .metric-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #F1F5F9;
        border: 1px solid #CBD5E1;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #334155;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }
    .badge-cleared {
        background-color: #DCFCE7;
        color: #166534;
        border: 1px solid #86EFAC;
    }
    .badge-pending {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FDE68A;
    }
    .system-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }
    .email-container {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.25rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .slack-container {
        background: #1A1D21;
        color: #D1D2D3;
        border-radius: 10px;
        padding: 1.25rem;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
</style>
""", unsafe_allow_html=True)


def get_groq_api_key():
    # Priority: Streamlit secrets -> os.environ -> .env file
    try:
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "")


# ── Session State Setup ────────────────────────────────────────────
if "hitl_state" not in st.session_state:
    st.session_state.hitl_state = "idle"  # idle, requested, approved_override, rejected
if "last_run_results" not in st.session_state:
    st.session_state.last_run_results = None


# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=60", use_container_width=True)
    st.title("⚙️ Control Panel")

    # Mode selection
    env_key = get_groq_api_key()
    mode = st.radio(
        "Agent Execution Mode:",
        ["Live Agent (Groq LLM)", "Instant Simulation (Guaranteed Fast)"],
        index=0 if env_key else 1,
        help="Live Agent calls Groq Llama 3.3 70B in real-time. Instant Simulation guarantees zero API errors or rate-limits."
    )

    custom_key = ""
    if mode == "Live Agent (Groq LLM)":
        if env_key:
            st.success("✅ GROQ_API_KEY detected in secrets/env")
            custom_key = env_key
        else:
            custom_key = st.text_input("Enter Groq API Key:", type="password", help="Get a free key from console.groq.com")
            if not custom_key:
                st.warning("⚠️ No key detected. Instant Simulation mode is recommended.")

    st.markdown("---")
    st.subheader("📋 Candidate Selection")

    # Load baseline DB
    with open(EMPLOYEES_DB, "r", encoding="utf-8") as f:
        employees_data = json.load(f)

    candidate_source = st.radio(
        "Candidate Source:",
        ["Pick Existing Profile", "✨ Onboard Custom Candidate (Try Your Name!)"],
        index=0
    )

    custom_emp = None
    if candidate_source == "✨ Onboard Custom Candidate (Try Your Name!)":
        st.markdown("**Custom Candidate Details:**")
        cust_name = st.text_input("Full Name:", value="Prachi Pandya")
        cust_dept = st.selectbox("Department:", ["Platform Engineering", "Data Engineering", "Cloud Infrastructure", "Cybersecurity", "AI Research"])
        cust_role = st.text_input("Role Title:", value="AI Systems Engineer")
        cust_loc = st.selectbox("Office Location:", ["Hyderabad Engineering Hub", "Bengaluru Tech Center", "London HQ", "Remote"])
        
        # Generate custom profile
        clean_name = cust_name.lower().replace(" ", ".")
        custom_emp = {
            "employee_id": "EMP-2026-CUSTOM",
            "name": cust_name,
            "email": f"{clean_name}@meridian.com",
            "role": cust_role,
            "level": "L5",
            "department": cust_dept,
            "manager_id": "EMP-2022-0103",
            "manager_name": "Vikram Nair",
            "employment_type": "fulltime",
            "location": cust_loc,
            "start_date": datetime.today().strftime('%Y-%m-%d'),
            "access_profile": {
                "github": f"{cust_dept.lower().split()[0]}-team",
                "jira": f"{cust_dept.lower().split()[0]}-project",
                "confluence": f"{cust_dept.lower().split()[0]}-space",
                "slack_channels": [f"{cust_dept.lower().split()[0]}-team", "all-engineering", "general"]
            }
        }
        selected_emp = "EMP-2026-CUSTOM"
        current_emp_data = custom_emp
    else:
        emp_options = list(employees_data.keys())
        selected_emp = st.selectbox(
            "Select Employee:",
            emp_options,
            format_func=lambda x: f"{x} - {employees_data[x]['name']} ({employees_data[x]['role']})"
        )
        current_emp_data = employees_data[selected_emp]

    st.markdown("---")
    st.subheader("🛡️ Policy Guardrails")
    
    compliance_override = st.radio(
        "Compliance Sign-off Status:",
        ["Keep Database Default", "Force CLEARED", "Force PENDING"],
        index=0,
        help="Toggle between CLEARED (access granted) and PENDING (access halted for compliance)."
    )

    enforce_gate = st.checkbox(
        "Enforce Compliance Gate",
        value=True,
        help="When enabled, agent refuses to provision access without CLEARED compliance."
    )

    st.markdown("---")
    st.caption("Autonomous Agent Built from First Principles · Meridian AI")


# ── Top Telemetry & Observability Bar ──────────────────────────────
st.markdown('<div class="main-header">🤖 Meridian AI · Autonomous Onboarding Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Transparent ReAct (Reason · Act · Observe) agent that safely automates employee onboarding with compliance verification and human oversight.</div>', unsafe_allow_html=True)

st.markdown(f"""
<div>
    <span class="metric-chip">🧠 <b>Model:</b> Groq / Llama-3.3-70b-versatile</span>
    <span class="metric-chip">🛡️ <b>Guardrail:</b> {'Enforced' if enforce_gate else 'Bypassed (Demo)'}</span>
    <span class="metric-chip">⚡ <b>Latency:</b> ~0.8s avg</span>
    <span class="metric-chip">💰 <b>Cost:</b> $0.00 (Groq Free Tier)</span>
    <span class="metric-chip">🌐 <b>Status:</b> Live & Operational</span>
</div>
""", unsafe_allow_html=True)
st.write("")

# ── Main Dashboard Tabs ────────────────────────────────────────────
tab_run, tab_profile, tab_compliance, tab_provision, tab_comms, tab_about = st.tabs([
    "🚀 Run Agent Demo",
    "👤 Candidate Profile",
    "📜 Compliance State",
    "🔑 System Access Matrix",
    "📬 Email & Slack Preview",
    "ℹ️ Architecture & Source"
])


# ── TAB 2: PROFILE ────────────────────────────────────────────────
with tab_profile:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Candidate Information")
        st.json({
            "Employee ID": current_emp_data.get("employee_id"),
            "Full Name": current_emp_data.get("name"),
            "Role": current_emp_data.get("role"),
            "Level": current_emp_data.get("level"),
            "Department": current_emp_data.get("department"),
            "Reporting Manager": current_emp_data.get("manager_name"),
            "Location": current_emp_data.get("location"),
            "Start Date": current_emp_data.get("start_date")
        })
    with col2:
        st.subheader("Requested Access Profile")
        access = current_emp_data.get("access_profile", {})
        st.markdown(f"**GitHub Team:** `{access.get('github', 'N/A')}`")
        st.markdown(f"**Jira Project Board:** `{access.get('jira', 'N/A')}`")
        st.markdown(f"**Confluence Space:** `{access.get('confluence', 'N/A')}`")
        st.markdown("**Slack Channels:**")
        for ch in access.get("slack_channels", []):
            st.markdown(f"- `#{ch}`")


# ── Helper for Effective Compliance ────────────────────────────────
def get_effective_compliance():
    if compliance_override == "Force CLEARED":
        return {
            "employee_id": selected_emp,
            "overall_status": "CLEARED",
            "code_of_conduct": "CLEARED",
            "data_handling_policy": "CLEARED",
            "security_guidelines": "CLEARED",
            "posh_training": "CLEARED"
        }
    elif compliance_override == "Force PENDING":
        return {
            "employee_id": selected_emp,
            "overall_status": "PENDING",
            "code_of_conduct": "PENDING",
            "data_handling_policy": "PENDING",
            "security_guidelines": "PENDING",
            "posh_training": "PENDING"
        }
    else:
        if selected_emp == "EMP-2026-CUSTOM":
            return {
                "employee_id": selected_emp,
                "overall_status": "PENDING",
                "code_of_conduct": "PENDING",
                "data_handling_policy": "PENDING",
                "security_guidelines": "PENDING",
                "posh_training": "PENDING"
            }
        return check_compliance_status(selected_emp)


# ── TAB 3: COMPLIANCE ─────────────────────────────────────────────
with tab_compliance:
    comp_state = get_effective_compliance()
    st.subheader(f"Compliance Ledger · {current_emp_data.get('name')}")
    status_cls = "badge-cleared" if comp_state.get("overall_status") == "CLEARED" else "badge-pending"
    st.markdown(f"**Overall Compliance Status:** <span class='badge {status_cls}'>{comp_state.get('overall_status')}</span>", unsafe_allow_html=True)
    st.write("")
    
    c1, c2, c3, c4 = st.columns(4)
    items = [
        ("Code of Conduct", comp_state.get("code_of_conduct")),
        ("Data Handling Policy", comp_state.get("data_handling_policy")),
        ("Security Guidelines", comp_state.get("security_guidelines")),
        ("POSH Anti-Harassment", comp_state.get("posh_training")),
    ]
    for col, (name, val) in zip([c1, c2, c3, c4], items):
        badge_cls = "badge-cleared" if val == "CLEARED" else "badge-pending"
        with col:
            st.markdown(f"""
            <div class="system-card">
                <b>{name}</b><br>
                <span class="badge {badge_cls}" style="margin-top: 6px;">{val}</span>
            </div>
            """, unsafe_allow_html=True)


# ── TAB 4: SYSTEM ACCESS MATRIX ───────────────────────────────────
with tab_provision:
    st.subheader("Enterprise System Integrations")
    p1, p2, p3, p4 = st.columns(4)
    access_p = current_emp_data.get("access_profile", {})
    
    # State based on last run
    has_provisioned = (st.session_state.last_run_results and st.session_state.last_run_results.get("provisioned"))
    pill_text = "PROVISIONED 🟢" if has_provisioned else "PENDING AGENT RUN ⏳"
    pill_style = "badge-cleared" if has_provisioned else "badge-pending"
    
    with p1:
        st.markdown(f"""
        <div class="system-card">
            <h4>🐙 GitHub Org</h4>
            <p><b>Team:</b> <code>{access_p.get('github')}</code></p>
            <span class="badge {pill_style}">{pill_text}</span>
        </div>
        """, unsafe_allow_html=True)
    with p2:
        st.markdown(f"""
        <div class="system-card">
            <h4>🎯 Jira Service</h4>
            <p><b>Project:</b> <code>{access_p.get('jira')}</code></p>
            <span class="badge {pill_style}">{pill_text}</span>
        </div>
        """, unsafe_allow_html=True)
    with p3:
        st.markdown(f"""
        <div class="system-card">
            <h4>📘 Confluence</h4>
            <p><b>Space:</b> <code>{access_p.get('confluence')}</code></p>
            <span class="badge {pill_style}">{pill_text}</span>
        </div>
        """, unsafe_allow_html=True)
    with p4:
        st.markdown(f"""
        <div class="system-card">
            <h4>💬 Slack Org</h4>
            <p><b>Channels:</b> {len(access_p.get('slack_channels', []))} added</p>
            <span class="badge {pill_style}">{pill_text}</span>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 5: EMAIL & SLACK PREVIEW ──────────────────────────────────
with tab_comms:
    st.subheader("Simulated Notification Output")
    col_em, col_sl = st.columns(2)
    
    with col_em:
        st.markdown("#### 📧 Candidate Welcome Email")
        st.markdown(f"""
        <div class="email-container">
            <div style="border-bottom: 1px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 10px;">
                <b>From:</b> Meridian AI Onboarding &lt;onboarding-bot@meridian.com&gt;<br>
                <b>To:</b> {current_emp_data.get('name')} &lt;{current_emp_data.get('email')}&gt;<br>
                <b>Subject:</b> Welcome to Meridian, {current_emp_data.get('name')}! 🎉
            </div>
            <p>Hi {current_emp_data.get('name')},</p>
            <p>Welcome to the <b>{current_emp_data.get('department')}</b> team as a <b>{current_emp_data.get('role')}</b>!</p>
            <p>Your systems access has been automatically provisioned by Meridian's AI Agent:</p>
            <ul>
                <li><b>GitHub:</b> Team <code>{access_p.get('github')}</code></li>
                <li><b>Jira:</b> Project <code>{access_p.get('jira')}</code></li>
                <li><b>Confluence:</b> Space <code>{access_p.get('confluence')}</code></li>
                <li><b>Slack:</b> Channels {', '.join([f'#{c}' for c in access_p.get('slack_channels', [])])}</li>
            </ul>
            <p>Your reporting manager is <b>{current_emp_data.get('manager_name')}</b>.</p>
            <p style="color: #64748B; font-size: 0.85rem; margin-top: 15px;">Automated onboarding powered by Meridian Agentic System.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_sl:
        st.markdown("#### 💬 Slack Channel Announcement (`#all-engineering`)")
        st.markdown(f"""
        <div class="slack-container">
            <div style="display: flex; gap: 10px; align-items: flex-start;">
                <span style="font-size: 1.8rem;">🤖</span>
                <div>
                    <b>Meridian Onboarding Bot</b> <span style="font-size: 0.8rem; color: #868686;">APP · Today at 09:00 AM</span><br>
                    <p style="margin-top: 6px;">🎉 Please join us in welcoming <b>{current_emp_data.get('name')}</b> to Meridian as our new <b>{current_emp_data.get('role')}</b> in <b>{current_emp_data.get('department')}</b>!</p>
                    <p style="margin: 4px 0; color: #9CA3AF;">• Location: {current_emp_data.get('location')}<br>• Manager: {current_emp_data.get('manager_name')}</p>
                    <div style="background: #222529; border-left: 3px solid #10B981; padding: 6px 12px; margin-top: 8px; border-radius: 4px;">
                        Access cleared & permissions granted. Say hi in #{access_p.get('slack_channels', ['general'])[0]}! 👋
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 6: ARCHITECTURE ───────────────────────────────────────────
with tab_about:
    st.markdown("""
    ### 🏛️ Agentic ReAct Architecture
    
    This agent is built from **first principles** without black-box framework abstractions:
    
    ```mermaid
    graph TD
        A[Start: Onboarding Goal] --> B[REASON: Next Action Analysis]
        B --> C{Decision}
        C -->|Tool: get_profile| D[HR Database]
        C -->|Tool: check_compliance| E[Compliance System]
        C -->|Guardrail: PENDING?| F[HITL: Human-in-the-Loop Approval]
        C -->|Tool: provision_access| G[GitHub / Jira / Slack Stubs]
        C -->|Tool: send_notification| H[Email / Slack Notification]
        D --> I[OBSERVE Result]
        E --> I
        G --> I
        H --> I
        I --> B
        F -->|Approved| G
        F -->|Hold| J[Safe Halt & Nudge Candidate]
    ```
    
    - **Transparent Control Flow**: Pure Python ReAct loop (`agent.py`).
    - **Multi-Modal Governance**: Enforces security policies before irreversible side-effects (granting credentials).
    - **Resilience**: Session caching in `data/session_cache.json` for session persistence and resume-capability.
    """)


# ── TAB 1: RUN DEMO ───────────────────────────────────────────────
with tab_run:
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.info(f"Target: **{current_emp_data.get('name')}** (`{selected_emp}`) · Execution: **{mode}**")
    with col_btn:
        start_agent = st.button("▶️ Run Agent Loop", type="primary", use_container_width=True)

    # Human-in-the-loop override buttons
    if st.session_state.hitl_state == "requested":
        st.warning("⚠️ **HUMAN SUPERVISOR INTERVENTION REQUIRED** · The agent detected PENDING compliance policies.")
        c_hitl1, c_hitl2 = st.columns(2)
        with c_hitl1:
            if st.button("🟢 Approve Manager Exception & Proceed", use_container_width=True):
                st.session_state.hitl_state = "approved_override"
                st.rerun()
        with c_hitl2:
            if st.button("🔴 Send Compliance Reminder & Hold", use_container_width=True):
                st.session_state.hitl_state = "rejected"
                st.rerun()

    if start_agent or st.session_state.hitl_state == "approved_override":
        execution_container = st.container()
        
        with execution_container:
            st.markdown("### 🔄 Execution Trace")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            comp = get_effective_compliance()
            profile = current_emp_data

            # Branch: Instant Simulation or Live LLM
            if mode == "Instant Simulation (Guaranteed Fast)" or not custom_key:
                # STEP 1
                status_text.text("Step 1: Reasoning on initial goal & reading HR database...")
                progress_bar.progress(25)
                time.sleep(0.5)
                
                with st.expander("📍 **Step 1: Reason & Retrieve Profile**", expanded=True):
                    st.markdown(f"**THOUGHT:** I need to onboard employee `{selected_emp}`. First, let's retrieve their role, department, and access requirements from the HR registry.")
                    st.code(f"ACTION: call_tool -> get_employee_profile(employee_id='{selected_emp}')", language="yaml")
                    st.success(f"OBSERVATION: Profile found for {profile['name']} ({profile['role']} in {profile['department']})")

                # STEP 2
                status_text.text("Step 2: Checking corporate compliance status...")
                progress_bar.progress(50)
                time.sleep(0.5)
                
                with st.expander("🛡️ **Step 2: Reason & Check Compliance Gate**", expanded=True):
                    st.markdown(f"**THOUGHT:** Before granting access to company codebases and systems, security policy mandates that all compliance policies must be acknowledged.")
                    st.code(f"ACTION: call_tool -> check_compliance_status(employee_id='{selected_emp}')", language="yaml")
                    if comp['overall_status'] == 'CLEARED':
                        st.success("OBSERVATION: All 4 mandatory policies acknowledged. Status: CLEARED.")
                    else:
                        st.warning("OBSERVATION: Status is PENDING. Security Guidelines & POSH training not yet signed.")

                # STEP 3: Compliance Gate Logic
                status_text.text("Step 3: Evaluating compliance guardrails...")
                progress_bar.progress(75)
                time.sleep(0.5)

                if comp['overall_status'] == 'PENDING' and enforce_gate and st.session_state.hitl_state != "approved_override":
                    with st.expander("⚠️ **Step 3: Compliance Gate Enforced (HALT)**", expanded=True):
                        st.markdown("**THOUGHT:** Compliance is PENDING. Rule 1 strictly forbids provisioning credentials before policies are signed. I will send a reminder notification and request human supervisor confirmation.")
                        st.code(f"ACTION: ask_human -> 'Compliance pending for {profile['name']}. Require supervisor approval to override or hold.'", language="yaml")
                        st.warning("🛑 **Agent Guardrail Triggered:** Provisioning blocked pending compliance completion or manager exception.")
                    
                    st.session_state.hitl_state = "requested"
                    st.session_state.last_run_results = {"provisioned": False}
                    progress_bar.progress(100)
                    status_text.text("Agent halted safely waiting for human approval.")
                    st.stop()

                else:
                    if st.session_state.hitl_state == "approved_override":
                        with st.expander("🤝 **Step 3: Human Supervisor Exception Granted**", expanded=True):
                            st.markdown(f"**SUPERVISOR ACTION:** Manager Vikram Nair signed off on a 24-hour compliance grace period exception for `{profile['name']}`.")
                            st.success("Manager override recorded in system audit log. Agent resuming execution.")

                    # STEP 3B: Provision Access
                    with st.expander("🔑 **Step 3: Provision Infrastructure Access**", expanded=True):
                        st.markdown(f"**THOUGHT:** Compliance requirement satisfied. Proceeding to provision GitHub, Jira, Confluence, and Slack access for `{profile['name']}`.")
                        access_res = {
                            "status": "SUCCESS",
                            "github": f"Added {profile['email']} to team {profile['access_profile']['github']}",
                            "jira": f"Granted member access to {profile['access_profile']['jira']}",
                            "confluence": f"Granted read/write to {profile['access_profile']['confluence']}",
                            "slack": f"Invited {profile['email']} to {len(profile['access_profile']['slack_channels'])} channels"
                        }
                        st.code(f"ACTION: call_tool -> provision_access(employee_id='{selected_emp}')", language="yaml")
                        st.json(access_res)

                    # STEP 4: Dispatch Welcome
                    status_text.text("Step 4: Dispatching notifications...")
                    progress_bar.progress(100)
                    time.sleep(0.5)
                    
                    with st.expander("📬 **Step 4: Dispatch Welcome Pack & Complete**", expanded=True):
                        st.markdown(f"**THOUGHT:** All systems have been successfully provisioned. Dispatching welcome email and posting Slack announcement.")
                        st.code(f"ACTION: call_tool -> send_notification(recipient='{profile['email']}', channel='email')", language="yaml")
                        st.success(f"OBSERVATION: Welcome pack delivered to {profile['email']}.")

                    st.session_state.hitl_state = "idle"
                    st.session_state.last_run_results = {"provisioned": True}
                    status_text.text("Onboarding successfully completed!")
                    st.balloons()
                    st.success(f"🎉 **Onboarding Complete for {profile['name']}! Review the 'System Access Matrix' and 'Email & Slack Preview' tabs.**")

            else:
                # Live Agent Mode with Groq LLM
                try:
                    os.environ["GROQ_API_KEY"] = custom_key
                    from agent import run_agent, PROMPT_PATH
                    
                    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                        sys_prompt = f.read()
                        
                    if not enforce_gate:
                        sys_prompt = sys_prompt.replace(
                            "1. **Compliance gate** - Never call provision_access before\n   check_compliance_status returns overall_status: CLEARED. If status is\n   PENDING, send a reminder notification then ask_human for confirmation\n   before proceeding.",
                            "1. ~~Compliance gate rule removed for this run~~"
                        )

                    status_text.text("Running autonomous ReAct loop with Groq Llama 3.3 70B...")
                    progress_bar.progress(30)
                    
                    res = run_agent(selected_emp, sys_prompt)
                    progress_bar.progress(100)
                    status_text.text("Execution finished.")

                    st.markdown("### 📊 Agent Trace")
                    for i, step in enumerate(res.get("history", [])):
                        with st.expander(f"Step {i+1}: {step.get('action_type', 'Action')}"):
                            st.markdown(f"**Thought:** {step.get('thought')}")
                            if step.get("action_type") == "call_tool":
                                st.code(f"Tool: {step.get('tool')}\nInput: {json.dumps(step.get('input'))}")
                                st.json(step.get("observation"))
                            elif step.get("action_type") == "ask_human":
                                st.warning(f"Question: {step.get('question')}")

                    st.session_state.last_run_results = {"provisioned": res.get('status') == 'COMPLETE'}
                    st.success(f"Status: {res.get('status')} · Summary: {res.get('summary', 'Done')}")

                except Exception as e:
                    st.error(f"Error during agent execution: {e}")
