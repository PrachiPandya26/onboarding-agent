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
    page_title="Meridian AI | Onboarding Agent Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #3B82F6 0%, #8B5CF6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    .badge-cleared {
        background-color: #DCFCE7;
        color: #166534;
    }
    .badge-pending {
        background-color: #FEF3C7;
        color: #92400E;
    }
    .step-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .thought-text {
        font-style: italic;
        color: #475569;
        border-left: 3px solid #6366F1;
        padding-left: 0.75rem;
        margin: 0.5rem 0;
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


# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=60", use_container_width=True)
    st.title("⚙️ Demo Controls")
    
    # Mode selection
    env_key = get_groq_api_key()
    mode = st.radio(
        "Agent Execution Mode:",
        ["Live Agent (Groq LLM)", "Instant Simulation (No Key Required)"],
        index=0 if env_key else 1,
        help="Choose Live Agent to call Groq Llama 3.3 70B, or Instant Simulation for guaranteed fast walkthrough."
    )

    custom_key = ""
    if mode == "Live Agent (Groq LLM)":
        if env_key:
            st.success("✅ GROQ_API_KEY configured")
            custom_key = env_key
        else:
            custom_key = st.text_input("Enter Groq API Key:", type="password", help="Get free key at console.groq.com")
            if not custom_key:
                st.warning("⚠️ No key detected. Running in Instant Simulation mode is recommended.")

    st.markdown("---")
    st.subheader("📋 Candidate Selection")

    # Load employee list
    with open(EMPLOYEES_DB, "r", encoding="utf-8") as f:
        employees_data = json.load(f)

    emp_options = list(employees_data.keys())
    selected_emp = st.selectbox(
        "Select Employee to Onboard:",
        emp_options,
        format_func=lambda x: f"{x} - {employees_data[x]['name']} ({employees_data[x]['role']})"
    )

    st.markdown("---")
    st.subheader("🛡️ Policy & Guardrails")
    
    compliance_override = st.radio(
        "Simulate Compliance Status:",
        ["Keep Database Default", "Force CLEARED", "Force PENDING"],
        index=0,
        help="Test how the agent safely halts when policies are pending versus when they are cleared."
    )

    enforce_gate = st.checkbox(
        "Enforce Compliance Gate",
        value=True,
        help="When enabled, the agent refuses to provision access until compliance is CLEARED."
    )

    st.markdown("---")
    st.caption("Onboarding Agent · Created with ❤️ by Prachi Pandya")


# ── Main Content ───────────────────────────────────────────────────
st.markdown('<div class="main-header">🤖 Meridian AI · Autonomous Onboarding Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">A transparent ReAct (Reason · Act · Observe) agent that safely automates employee onboarding with compliance verification.</div>', unsafe_allow_html=True)

tab_run, tab_profile, tab_compliance, tab_about = st.tabs([
    "🚀 Run Agent Demo",
    "👤 Employee Profile",
    "📜 Compliance State",
    "ℹ️ Architecture & Source"
])

current_emp_data = employees_data.get(selected_emp, {})

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
            "Work Location": current_emp_data.get("location"),
            "Start Date": current_emp_data.get("start_date")
        })
    with col2:
        st.subheader("Target Access Profile")
        access = current_emp_data.get("access_profile", {})
        st.markdown(f"**GitHub Org Team:** `{access.get('github', 'N/A')}`")
        st.markdown(f"**Jira Project:** `{access.get('jira', 'N/A')}`")
        st.markdown(f"**Confluence Space:** `{access.get('confluence', 'N/A')}`")
        st.markdown("**Slack Channels:**")
        for ch in access.get("slack_channels", []):
            st.markdown(f"- `#{ch}`")

# ── TAB 3: COMPLIANCE ─────────────────────────────────────────────
with tab_compliance:
    with open(COMPLIANCE_DB, "r", encoding="utf-8") as f:
        comp_data = json.load(f)
    comp_state = comp_data.get(selected_emp, {
        "overall_status": "PENDING",
        "code_of_conduct": "PENDING",
        "data_handling_policy": "PENDING",
        "security_guidelines": "PENDING",
        "posh_training": "PENDING"
    })
    
    st.subheader(f"Compliance Record for {current_emp_data.get('name', selected_emp)}")
    status_color = "badge-cleared" if comp_state.get("overall_status") == "CLEARED" else "badge-pending"
    st.markdown(f"**Overall Status:** <span class='badge {status_color}'>{comp_state.get('overall_status')}</span>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    items = [
        ("Code of Conduct", comp_state.get("code_of_conduct")),
        ("Data Handling", comp_state.get("data_handling_policy")),
        ("Security Guidelines", comp_state.get("security_guidelines")),
        ("POSH Training", comp_state.get("posh_training")),
    ]
    for col, (name, val) in zip([c1, c2, c3, c4], items):
        badge_cls = "badge-cleared" if val == "CLEARED" else "badge-pending"
        with col:
            st.markdown(f"**{name}**<br><span class='badge {badge_cls}'>{val}</span>", unsafe_allow_html=True)

# ── TAB 4: ARCHITECTURE ───────────────────────────────────────────
with tab_about:
    st.markdown("""
    ### How the ReAct Loop Works
    
    The agent implements an explicit **ReAct** loop:
    
    ```
    Goal -> Reason (Thought) -> Act (Tool Call) -> Observe (Tool Result) -> Loop until Complete
    ```
    
    1. **Tool 1: `get_employee_profile`** - Reads employee metadata and access permissions.
    2. **Tool 2: `check_compliance_status`** - Verifies whether corporate compliance policies are signed.
    3. **Enforcement Gate** - If compliance is `PENDING`, the agent halts, notifies the user, and will NOT provision credentials.
    4. **Tool 3: `provision_access`** - Provisions GitHub, Jira, Confluence, and Slack only once cleared.
    5. **Tool 4: `send_notification`** - Sends welcome notification or compliance reminders.
    """)


# ── TAB 1: RUN DEMO ───────────────────────────────────────────────
with tab_run:
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.info(f"Target: **{current_emp_data.get('name')}** ({selected_emp}) · Mode: **{mode}**")
    with col_btn:
        start_agent = st.button("▶️ Run Agent Loop", type="primary", use_container_width=True)

    if start_agent:
        execution_container = st.container()
        
        with execution_container:
            st.markdown("### 🔄 Execution Trace")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulated compliance status helper
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
                    return check_compliance_status(selected_emp)

            # Execution logic
            if mode == "Instant Simulation (No Key Required)" or not custom_key:
                # Step 1: Get profile
                status_text.text("Step 1: Reading employee profile...")
                progress_bar.progress(25)
                time.sleep(0.6)
                
                profile = get_employee_profile(selected_emp)
                with st.expander("📍 **Step 1: Reason & Retrieve Profile**", expanded=True):
                    st.markdown("**THOUGHT:** I need to onboard employee `{selected_emp}`. First, let's retrieve their role, department, and access requirements.")
                    st.code(f"ACTION: call_tool -> get_employee_profile(employee_id='{selected_emp}')", language="yaml")
                    st.success(f"OBSERVATION: Profile found for {profile['name']} ({profile['role']} - {profile['department']})")

                # Step 2: Check compliance
                status_text.text("Step 2: Checking compliance acknowledgements...")
                progress_bar.progress(50)
                time.sleep(0.6)
                
                comp = get_effective_compliance()
                with st.expander("🛡️ **Step 2: Reason & Check Compliance**", expanded=True):
                    st.markdown(f"**THOUGHT:** Before granting access to corporate infrastructure, company policy mandates checking compliance sign-off.")
                    st.code(f"ACTION: call_tool -> check_compliance_status(employee_id='{selected_emp}')", language="yaml")
                    if comp['overall_status'] == 'CLEARED':
                        st.success(f"OBSERVATION: Compliance status is CLEARED.")
                    else:
                        st.warning(f"OBSERVATION: Compliance status is PENDING. Code of conduct and security training not yet completed.")

                # Step 3: Branching on compliance gate
                status_text.text("Step 3: Evaluating compliance gate...")
                progress_bar.progress(75)
                time.sleep(0.6)

                if comp['overall_status'] == 'PENDING' and enforce_gate:
                    with st.expander("⚠️ **Step 3: Compliance Gate Enforced (HALT)**", expanded=True):
                        st.markdown("**THOUGHT:** Compliance is PENDING. Guardrail rule 1 strictly forbids provisioning access without compliance sign-off. I will send a reminder notification and ask human supervisor.")
                        st.code(f"ACTION: call_tool -> send_notification(recipient='{profile['email']}', channel='email', subject='Compliance Required Before Onboarding')", language="yaml")
                        st.info("📨 Compliance reminder sent to candidate.")
                        st.markdown("**HUMAN IN THE LOOP:** Execution halted safely pending compliance clearance.")
                    
                    progress_bar.progress(100)
                    status_text.text("Execution halted safely.")
                    st.warning(f"🛑 **Agent Guardrail Triggered:** System access for {profile['name']} was blocked because compliance policies are pending.")
                
                else:
                    # Provision access
                    with st.expander("🔑 **Step 3: Provision Systems Access**", expanded=True):
                        st.markdown("**THOUGHT:** Compliance verified. Now safe to provision requested GitHub, Jira, Confluence, and Slack access.")
                        access_res = provision_access(selected_emp, profile.get('access_profile', {}))
                        st.code(f"ACTION: call_tool -> provision_access(employee_id='{selected_emp}')", language="yaml")
                        st.success(f"OBSERVATION: {json.dumps(access_res, indent=2)}")

                    # Step 4: Send welcome notification
                    status_text.text("Step 4: Sending welcome notification...")
                    progress_bar.progress(100)
                    time.sleep(0.6)
                    
                    with st.expander("📬 **Step 4: Dispatch Welcome Email & Complete**", expanded=True):
                        st.markdown("**THOUGHT:** Systems have been provisioned. Final step is to send a welcome notification to the employee.")
                        email_res = send_notification(
                            recipient=profile['email'],
                            channel='email',
                            subject=f"Welcome to Meridian, {profile['name']}!",
                            body=f"Hi {profile['name']}, your accounts have been provisioned. Manager: {profile['manager_name']}."
                        )
                        st.code(f"ACTION: call_tool -> send_notification", language="yaml")
                        st.success(f"OBSERVATION: {email_res}")

                    status_text.text("Onboarding complete!")
                    st.balloons()
                    st.success(f"🎉 **Onboarding Successfully Completed for {profile['name']}!**")

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

                    st.markdown("### 📊 Agent History")
                    for i, step in enumerate(res.get("history", [])):
                        with st.expander(f"Step {i+1}: {step.get('action_type', 'Action')}"):
                            st.markdown(f"**Thought:** {step.get('thought')}")
                            if step.get("action_type") == "call_tool":
                                st.code(f"Tool: {step.get('tool')}\nInput: {json.dumps(step.get('input'))}")
                                st.json(step.get("observation"))
                            elif step.get("action_type") == "ask_human":
                                st.warning(f"Question asked to human: {step.get('question')}")

                    st.success(f"Status: {res.get('status')} · Summary: {res.get('summary', 'Done')}")

                except Exception as e:
                    st.error(f"Error during agent execution: {e}")
