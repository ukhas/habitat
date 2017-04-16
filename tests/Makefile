#!/usr/bin/make
# -*- makefile -*-

NOSETESTS=nosetests
JASMINE=jasmine-node

test_habitat :
	PYTHONPATH=.. $(NOSETESTS) test_habitat

test_web :
	NODE_PATH=../web/js $(JASMINE) test_web

all : test_habitat test_web

.PHONY : test_habitat test_web all
.DEFAULT_GOAL := all
