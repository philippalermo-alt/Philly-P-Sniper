# PRODUCTION_DEPLOYMENT_CONTRACT.md

## Purpose

This contract governs **ALL production deployments** for this project.
Its sole objective is to **prevent unverified, speculative, or broken deployments**.

No deployment may occur unless every rule below is satisfied and **proven**.

---

## 🔒 Core Principle (Non-Negotiable)

> **Nothing is “fixed” until it is proven running in the target environment.**

Claims without evidence are invalid.

---

## 🚦 Deployment Stages (Mandatory Order)

### STAGE 1 — Local Verification

Must be executed **before any server interaction**.

Required:

* Application runs successfully via Docker **locally**
* Command used must be identical to production entrypoint

Proof required:

* Exact command run
* Full stdout/stderr
* Confirmation that the process exits cleanly (or remains running as expected)

---

### STAGE 2 — Artifact Integrity Check

Before deployment, all required artifacts must exist and be readable.

Examples (non-exhaustive):

* Model files (`.pkl`, `.json`)
* Config files
* Environment variables
* Database migrations

Proof required:

* Explicit confirmation of file presence
* No silent fallbacks allowed

---

### STAGE 3 — Remote Execution (Proof-First)

Deployment is **NOT complete** until the application runs successfully on the server.

Required:

* Execute the production command **manually** on EC2:

  ```bash
  sudo docker exec <container> python3 main.py
  ```
* Or equivalent for the service

Proof required:

* Paste the full output
* Logs must show:

  * Successful initialization
  * No fatal errors
  * Expected runtime behavior

---

### STAGE 4 — Observability Confirmation

The system must demonstrate it is operating normally post-deploy.

Required checks:

* Logs are being written
* Scheduled jobs still run
* No error spam introduced

Proof required:

* Log excerpts
* Confirmation that cron/systemd jobs still execute

---

## ❌ Explicitly Forbidden Behaviors

* Deploying immediately after “fixing” code without running it
* Claiming success based on reasoning or expectation
* Re-deploying repeatedly to “try” fixes
* Silent exception handling that masks failure
* “It should work now” deployments

Any of the above constitutes a **contract violation**.

---

## 🛑 Automatic Stop Conditions

Deployment must STOP if:

* The app fails to start
* A model file fails to load
* A dependency mismatch occurs
* A error cannot be reproduced locally

In these cases:

* Diagnose
* Fix
* Re-run from **Stage 1**

---

## 🧠 Agent Enforcement Rules

When operating under this contract:

* You MUST refuse to deploy without proof
* You MUST request missing verification
* You MUST NOT infer success
* You MUST treat environment mismatches as blockers, not bugs

---

## ✅ Definition of “Deployed”

A deployment is considered **complete** only when:

* The application runs successfully in production
* Logs confirm expected behavior
* No contract rules were bypassed

Anything else is **NOT a deployment**.
