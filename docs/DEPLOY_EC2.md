# EC2 Deployment Workflow (Enforced)

**Policy**: No code touches Production without passing `make verify`. No deployment is "Success" without passing Remote Proof (`docker exec`).

## 1. Prerequisites
- `secrets/philly_key.pem` present (permission 600).
- Docker installed locally (desktop).
- Docker installed remotely.

## 2. Standard Workflow
From the project root:

```bash
# Step 1: Local Verification
# Builds container, runs main.py dry-run locally.
# MUST PASS.
make verify

# Step 2: Deploy to EC2
# Auto-runs verify first.
# Syncs code, rebuilds remote container, restarts.
# Auto-runs remote proof.
make deploy
```

## 3. Stop Rules
1. **FAIL LOCAL**: If `make verify` fails, DO NOT DEPLOY. debug locally.
2. **FAIL REMOTE**: If deployment succeeds but `Remote Proof` fails, ROLLBACK or HOTFIX immediately. The system is in a bad state.

## 4. Manual Commands (Emergency Only)
If `make` is unavailable:

**Verify Local**:
```bash
./scripts/verify_local.sh
```

**Deploy**:
```bash
./scripts/deploy_ec2.sh
```
