PYTHON=.venv/bin/python

all: PYTHON

PYTHON: setup.py
	virtualenv -p python3 --no-site-packages .venv
	$(PYTHON) setup.py develop

test:
	@ofxstatement convert -t mbank.cz m.csv  mbank-cz.ofx
