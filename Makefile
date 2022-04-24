SELF_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
include $(SELF_DIR)common.mk

.DEFAULT_GOAL := build

SERVICE=otel-datadog-apm-py
ENV=myenv # todo: replace with env of your choice.

ORIGINAL_DOCKER_COMPOSE=VERSION=$(VERSION) SERVICE=$(SERVICE) ENV=$(ENV) docker-compose
DOCKER_COMPOSE=$(ORIGINAL_DOCKER_COMPOSE)


.PHONY: build
build:
	@$(DOCKER_COMPOSE) build

.PHONY: run
run: DOCKER_COMPOSE=DD_API_KEY=$(DD_API_KEY) $(ORIGINAL_DOCKER_COMPOSE)
run:
	@$(DOCKER_COMPOSE) up --build --remove-orphans

.PHONY: stop
stop:
	@$(DOCKER_COMPOSE) down --remove-orphans --volumes

COMPOSE_PROJECT=otel-datadog-apm-py

.PHONY: curl
curl: WEB?=py-http-otel
curl: C_PORT?=8080
curl: WEB_CONTAINER_ID=$(shell docker ps -q --filter "label=com.docker.compose.project=$(COMPOSE_PROJECT)" --filter "label=com.docker.compose.service=$(WEB)")
curl: HOST_PORT=$(shell docker port $(WEB_CONTAINER_ID) $(C_PORT))
curl: KEY ?= foo
curl: ROUTE ?= /redis/get/$(KEY)
curl:
	@curl -s $(HOST_PORT)$(ROUTE)

.PHONY: ssh
ssh: COMPONENT?=datadog
ssh: CMD?=/bin/bash
ssh: CONTAINER_ID=$(shell docker ps -q --filter "label=com.docker.compose.project=$(COMPOSE_PROJECT)" --filter "label=com.docker.compose.service=$(COMPONENT)")
ssh:
	@docker exec -it $(CONTAINER_ID) $(CMD)

.PHONY: set
set: COMPONENT?=redis0
set: KEY?=foo
set: VALUE?=bar
set: CMD?=/bin/bash
set: REDIS_PORT=6379
set: CONTAINER_ID=$(shell docker ps -q --filter "label=com.docker.compose.project=$(COMPOSE_PROJECT)" --filter "label=com.docker.compose.service=$(COMPONENT)")
set: HOST_PORT=$(lastword $(subst :, ,$(shell docker port $(CONTAINER_ID) $(REDIS_PORT))))
set: KEY_LENGTH=$(shell printf '%s' '$(KEY)' | wc -c | tr -d ' ')
set: VALUE_LENGTH=$(shell printf '%s' '$(VALUE)' | wc -c | tr -d ' ')
set:
	@echo -e '*3\r\n$$3\r\nSET\r\n$$$(KEY_LENGTH)\r\n$(KEY)\r\n$$$(VALUE_LENGTH)\r\n$(VALUE)\r\n' | nc localhost $(HOST_PORT)
