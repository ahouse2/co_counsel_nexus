# Rapid Development Command — PRP Analyze Run

The **PRP Analyze Run** template standardises the way reviewers capture findings after executing a Product Requirements Packet (PRP) workflow. Use it to document evidence, anomalies, and recommended follow-ups immediately after a command-driven trial run.

## When to Use
- After any `rapid-development` command that exercises a PRP implementation end-to-end.
- During ACE (Agentic Context Engineering) Critic passes where structured feedback is required.
- Before filing validation issues or updating PRP deliverables, so the context is searchable and auditable.

## How to Use the Template
1. Copy the template block below into your run journal (e.g., under `build_logs/` or the relevant PRP doc).
2. Replace bracketed guidance with concrete observations—do not leave sections blank.
3. Attach artefacts (logs, screenshots, traces) referenced in section 5 and link them inline.
4. If the run uncovers blocking issues, reference the follow-up ticket/PR at the end of section 6.

---

### PRP Analyze Run — Structured Notes

**Run Metadata**
- PRP document(s): <!-- e.g., PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md -->
- Command / script: <!-- e.g., tools/run_command.sh ... -->
- Date & time (UTC): 
- Operator(s): 
- Target environment: <!-- local dev, staging compose, etc. -->

**1. Preparation Checklist**
- [ ] Dependencies validated (list versions)
- [ ] Environment variables confirmed (list critical keys)
- [ ] Data fixtures / corpora ready (identify sources)
- Notes: 

**2. Execution Trace**
- Trigger summary: <!-- Describe the entry point and key flags -->
- Timeline checkpoints: <!-- bullet list with timestamps for major milestones -->
- Automation variances: <!-- deviations from manifest, manual interventions -->

**3. Observed Outcomes**
- Success criteria met? <!-- enumerate yes/no with justification -->
- Key results: <!-- citations, outputs, user-visible behaviours -->
- Metrics captured: <!-- latency, tokens, storage deltas, etc. -->

**4. Issues & Risks**
- Severity-ranked findings: <!-- list, include links to artefacts/logs -->
- Root-cause hypotheses: <!-- optional, if diagnosable -->
- Mitigations applied during run: 

**5. Evidence Links**
- Logs: 
- Screenshots / recordings: 
- Traces / dashboards: 
- Additional references: 

**6. Follow-Up Actions**
- Immediate tasks: <!-- checklist with owners + due dates -->
- Required PRP updates: 
- Escalations / decisions: 

**Sign-off**
- Reviewer acknowledgement: 
- Next scheduled run: 

---

> _Tip_: Store completed analyses alongside related PRP artifacts so future agents can diff behaviour over time.
