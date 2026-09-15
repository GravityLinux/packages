.PHONY: check status prepare srpm
PYTHON ?= python3
check:
	$(PYTHON) tools/package.py check
status:
	$(PYTHON) tools/package.py status
prepare:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE"; exit 1)
	$(PYTHON) tools/package.py prepare "$(PACKAGE)" $(ARGS)
srpm:
	@test -n "$(PACKAGE)" || (echo "Set PACKAGE"; exit 1)
	$(PYTHON) tools/package.py srpm "$(PACKAGE)" $(ARGS)
