PYTHON ?= python3

NODE ?= node

.PHONY: validate test test-web dashboard web-dashboard next revise stats weakness progress check-solution refresh-frequency

validate:
	$(PYTHON) scripts/validate_curriculum.py

test:
	$(PYTHON) scripts/test_shared.py
	$(PYTHON) scripts/test_update_progress.py
	$(PYTHON) scripts/test_validate_curriculum.py
	$(PYTHON) scripts/test_run_checks.py
	$(PYTHON) scripts/test_weakness_lab.py
	$(PYTHON) scripts/test_dashboard_feed.py
	$(PYTHON) scripts/test_plan_feed.py
	$(PYTHON) scripts/test_curriculum_order.py
	$(MAKE) test-web

# Dashboard JS suite, headless. Same tests tests.html runs in the browser.
test-web:
	@command -v $(NODE) >/dev/null 2>&1 || { \
	  echo "ERROR: '$(NODE)' not found - the dashboard JS suite needs Node."; \
	  echo "Install Node, or run 'make NODE=/path/to/node test'."; exit 1; }
	$(NODE) web_dashboard/js/tests/node.js

dashboard:
	$(PYTHON) scripts/dashboard.py

web-dashboard:
	$(PYTHON) scripts/serve_dashboard.py

next:
	$(PYTHON) scripts/next_problem.py --format text

revise:
	$(PYTHON) scripts/revision_report.py --today-only

stats:
	$(PYTHON) scripts/revision_report.py

weakness:
	$(PYTHON) scripts/weakness_lab.py $(if $(ARGS),$(ARGS),)

progress:
	$(PYTHON) scripts/update_progress.py $(if $(ARGS),$(ARGS),--help)

check-solution:
	$(PYTHON) scripts/run_checks.py $(PROBLEM)

refresh-frequency:
	$(PYTHON) scripts/fetch_interview_frequency.py
