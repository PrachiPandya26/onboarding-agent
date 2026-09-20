SCENARIO BRIEF - Onboarding Agent

CONTEXT
This repo is a beginner-friendly to build an AI agent. The concrete use case is employee onboarding for the Meridian Financial Services engineering team in Hyderabad.

The goal is not just to "make the code run". The goal is to
show how an agent reasons, decides when to call tools, asks for human
confirmation, and respects policy rules while completing a real workflow.

GOAL
Given an employee_id, the agent must complete the four-step onboarding
workflow:

  1. Retrieve the employee profile from HR
  2. Check compliance acknowledgement status
  3. Provision system access only after compliance is CLEARED
  4. Send a welcome notification

TOOLS AVAILABLE
The agent has four tools at its disposal:

  get_employee_profile(employee_id)
    Returns: name, role, level, department, manager_id, employment_type,
             access_profile
    Raises: EmployeeNotFound if no matching record exists

  check_compliance_status(employee_id)
    Returns: code_of_conduct, data_handling_policy, security_guidelines,
             posh_training, overall_status (CLEARED or PENDING)

  provision_access(employee_id, access_profile)
    Provisions GitHub, JIRA, Confluence, and Slack access based on the
    access profile. Returns SUCCESS with the items provisioned.

  send_notification(recipient, channel, subject, body)
    Sends a message via email, slack, or whatsapp. Returns SUCCESS.

CRITICAL ENFORCEMENT RULES
These rules are the difference between a safe agent and an audit finding.

  1. Never call provision_access before check_compliance_status returns
     overall_status: CLEARED. If status is PENDING, the agent must call
     send_notification to remind the employee and then ask_human before
     proceeding.

  2. If any tool call fails with an exception, the agent must retry at
     most 3 times. After 3 failures, escalate to the manager via
     send_notification and stop.

  3. Never provision access to a system that is not listed in the
     employee's access_profile.

  4. Never log or include the employee's email, name, or personal details
     in system logs. Use only the employee_id in logs.

NEW HIRE DETAILS
First test case for the agent:

  employee_id: EMP-2026-0847
  expected name: Priya Sharma
  expected role: Software Engineer (L4)
  expected department: Platform Engineering
  current compliance status: PENDING

EXPECTED AGENT BEHAVIOUR

  1. Retrieve the employee profile.
  2. Check compliance status.
  3. If compliance is PENDING, send a reminder notification.
  4. Ask the human for confirmation.
  5. After confirmation, provision only the systems in access_profile.
  6. Send a welcome notification.
  7. Complete with a short summary.

This scenario is the example to learn how to
build an onboarding AI agent end to end.
