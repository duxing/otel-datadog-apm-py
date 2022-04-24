SHELL := /bin/bash
CUR_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
REPO_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
OS ?= $(shell uname -s)
VERSION ?= $(shell git rev-parse --short HEAD)
