
SHELL:=/bin/bash
ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

.PHONY: all fresh fulluninstall install dependencies clean

all: dependencies

fresh: clean dependencies

fulluninstall: uninstall clean

install:

dependencies:
	if [ ! -d $(ROOT_DIR)/env ]; then pyvenv-3.5 $(ROOT_DIR)/env; fi
	source $(ROOT_DIR)/env/bin/activate; yes w | pip3.5 install -r $(ROOT_DIR)/requirements.txt

clean:
	# Remove existing environment
	if [ -d $(ROOT_DIR)/env ]; then \
		rm -rf $(ROOT_DIR)/env; \
	fi;
	# Remove compiled python files
	if [ -d $(ROOT_DIR)/nebula ]; then \
		rm -f $(ROOT_DIR)/nebula/*.pyc; \
	fi;
