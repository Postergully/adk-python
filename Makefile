.DEFAULT_GOAL := help

# Load .env file if it exists
ifneq (,$(wildcard ./.env))
  include .env
  export
endif

PID_DIR := .pids
PYTHON := python3.11
UVICORN := $(PYTHON) -m uvicorn

export P2P_MODE := MOCK
export P2P_SLACK_BOT_TOKEN := xoxb-mock-token
export P2P_SLACK_SIGNING_SECRET := mock-signing-secret

.PHONY: help finny-up finny-down finny-status finny-logs finny-test finny-sandbox finny-adk

help: ## Print all available targets
	@echo "Finny V1 Service Orchestration"
	@echo "=============================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""

finny-up: ## Start all 3 services (netsuite, slack, gateway) in background
	@mkdir -p $(PID_DIR)
	@echo "Starting NetSuite mock on :8081..."
	@$(UVICORN) mock_servers.netsuite_mock.app:app --port 8081 > $(PID_DIR)/netsuite.log 2>&1 & echo $$! > $(PID_DIR)/netsuite.pid
	@echo "  Waiting for NetSuite..."
	@for i in $$(seq 1 15); do \
		if curl -sf http://localhost:8081/health > /dev/null 2>&1; then \
			echo "  NetSuite healthy"; \
			break; \
		fi; \
		if [ $$i -eq 15 ]; then echo "  ERROR: NetSuite failed to start"; exit 1; fi; \
		sleep 1; \
	done
	@echo "Starting Slack mock on :8083..."
	@$(UVICORN) mock_servers.slack_mock.app:app --port 8083 > $(PID_DIR)/slack.log 2>&1 & echo $$! > $(PID_DIR)/slack.pid
	@echo "  Waiting for Slack mock..."
	@for i in $$(seq 1 15); do \
		if curl -sf http://localhost:8083/health > /dev/null 2>&1; then \
			echo "  Slack mock healthy"; \
			break; \
		fi; \
		if [ $$i -eq 15 ]; then echo "  ERROR: Slack mock failed to start"; exit 1; fi; \
		sleep 1; \
	done
	@echo "Starting Gateway on :8080..."
	@$(UVICORN) p2p_agents.finny_v1.gateway.app:fastapi_app --port 8080 > $(PID_DIR)/gateway.log 2>&1 & echo $$! > $(PID_DIR)/gateway.pid
	@echo "  Waiting for Gateway..."
	@for i in $$(seq 1 15); do \
		if curl -sf http://localhost:8080/health > /dev/null 2>&1; then \
			echo "  Gateway healthy"; \
			break; \
		fi; \
		if [ $$i -eq 15 ]; then echo "  ERROR: Gateway failed to start"; exit 1; fi; \
		sleep 1; \
	done
	@echo ""
	@echo "All services running."

finny-down: ## Stop all services and clean up PID files
	@if [ -d $(PID_DIR) ]; then \
		for pidfile in $(PID_DIR)/*.pid; do \
			if [ -f "$$pidfile" ]; then \
				pid=$$(cat "$$pidfile"); \
				name=$$(basename "$$pidfile" .pid); \
				if kill -0 $$pid 2>/dev/null; then \
					kill $$pid && echo "Stopped $$name (PID $$pid)"; \
				else \
					echo "$$name (PID $$pid) already stopped"; \
				fi; \
			fi; \
		done; \
		rm -rf $(PID_DIR); \
		echo "Cleaned up $(PID_DIR)/"; \
	else \
		echo "No services running ($(PID_DIR)/ not found)"; \
	fi

finny-status: ## Check health of each service
	@echo "Service Status"
	@echo "=============="
	@printf "  %-12s " "NetSuite:"; \
	if curl -sf http://localhost:8081/health > /dev/null 2>&1; then echo "UP"; else echo "DOWN"; fi
	@printf "  %-12s " "Slack mock:"; \
	if curl -sf http://localhost:8083/health > /dev/null 2>&1; then echo "UP"; else echo "DOWN"; fi
	@printf "  %-12s " "Gateway:"; \
	if curl -sf http://localhost:8080/health > /dev/null 2>&1; then echo "UP"; else echo "DOWN"; fi

finny-logs: ## Tail logs from all services
	@tail -f $(PID_DIR)/*.log

finny-test: ## Run Finny V1 test suite
	python3.11 -m pytest tests/finny_v1/ -v

finny-sandbox: ## Run the Finny sandbox script
	$(PYTHON) scripts/finny_sandbox.py

finny-adk: ## Launch ADK web UI for Finny V1
	adk web p2p_agents/finny_v1
