PYTHON=.venv/bin/python

all: PYTHON

PYTHON: setup.py
	virtualenv -p python3 --no-site-packages .venv
	$(PYTHON) setup.py develop

test:
	@ofxstatement convert -t mbank.sk mKonto_01627828_900501_150612.csv  mbank-sk.ofx
