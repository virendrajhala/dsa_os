PYTHON ?= python3

.PHONY: validate dashboard web-dashboard next revise stats progress

validate:
	$(PYTHON) scripts/validate_curriculum.py

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

progress:
	$(PYTHON) scripts/update_progress.py $(if $(ARGS),$(ARGS),--help)
