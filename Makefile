PYTHON ?= python3

.PHONY: validate test dashboard web-dashboard next revise stats weakness progress

validate:
	$(PYTHON) scripts/validate_curriculum.py

test:
	$(PYTHON) scripts/test_shared.py

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
