# AGENT.md — PhillyEdge / Antigravity Operating Rules (READ FIRST)

You are assisting on the PhillyEdge codebase. Your job is to improve correctness, stability, and deploy safety.

---

## The 8 Hard Rules (Non-Negotiable)

1) **No deploy without proof:** You may not deploy unless `main.py` runs successfully inside the container.  
2) **Never claim “fixed” without proof:** You may only claim “fixed” after a verified successful run.  
3) **Reproduce first:** Identify the failure mode and reproduce it before editing code.  
4) **Minimal change only:** Apply the smallest change that tests a clear hypothesis.  
5) **Verify inside Docker:** Validation must run in the same Docker environment used for EC2.  
6) **One deploy per verified fix:** If not verified locally, do not deploy “to try it.”  
7) **Stop guessing after 2 repeats:** If the same error happens twice, escalate to logs/instrumentation.  
8) **Pickle/numpy errors are artifact mismatches:** `numpy._core.numeric` pickle failures are environment/model issues, not code bugs.

---

## Required Proof Command (The Gate)
A deploy is not allowed unless this succeeds:

```bash
sudo docker exec philly_p_api python3 main.py