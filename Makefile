
SHELL:=/bin/bash
ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PYTHON:=python3

.PHONY: all fresh fulluninstall install dependencies clean

all: dependencies

fresh: clean dependencies

fulluninstall: uninstall clean

install:

testenv: clean_testenv
	docker-compose up --build

clean_testenv:
	docker-compose down

fresh_testenv: clean_testenv testenv

venv:
	if [ ! -d $(ROOT_DIR)/env ]; then $(PYTHON) -m venv $(ROOT_DIR)/env; fi

dependencies: venv
	source $(ROOT_DIR)/env/bin/activate; yes w | python -m pip install -r $(ROOT_DIR)/requirements.txt

upgrade_dependencies: venv
	source $(ROOT_DIR)/env/bin/activate; ./bin/update_dependencies.sh $(ROOT_DIR)/requirements.txt

clean:
	rm -rf $(ROOT_DIR)/env;
	rm -rf $(ROOT_DIR)/nebula/*.pyc;
