.PHONY: verify deploy help

help: ## Show this help
	@echo "Philly-P-Sniper Deployment Workflow"
	@echo "-----------------------------------"
	@echo "make verify  - Run local verification (Docker build + main.py)"
	@echo "make deploy  - Run verify + Deploy to EC2 + Remote Proof"

verify: ## Run local verification
	@./scripts/verify_local.sh

deploy: ## Deploy to EC2 (Enforced Workflow)
	@./scripts/deploy_ec2.sh
