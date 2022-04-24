# otel-datadog-apm-py

Comparing DataDog APM integration in python using ddtrace and OpenTelemetry.


## Pre-requisite

 - `docker`
 - `docker-compose`
 - a valid datadog api key

## Usage

### Start

`DD_API_KEY=<valid_api_key> make run`

### Http request

`make curl`: issues an Http request a running http server.

Default server is `py-http-otel`.

Default path is `/redis/get/${KEY}`.

To override the key for redis: `KEY=<my_key> make curl`.

To change to a different route: `ROUTE=/foo make curl`.

Supported routes:
 - `/`
 - `/open`
 - `/foo`
 - `/delay/<up_to_str>`
 - `/redis/get/<key>`


A couple commands used for testing:
 - `WEB=py-http-dd ROUTE=/foo make curl`
 - `WEB=py-http-otel ROUTE=/foo make curl`
 - `WEB=py-http-dd ROUTE=/open make curl`
 - `WEB=py-http-otel ROUTE=/open make curl`
 - `WEB=py-http-dd ROUTE=/delay/10 make curl`
 - `WEB=py-http-otel ROUTE=/delay/200 make curl`
 - `COMPONENT=redis0 KEY=foo VALUE=bar make set`
 - `COMPONENT=redis1 KEY=foo VALUE=bar make set`
 - `WEB=py-http-dd ROUTE=/redis/get/foo make curl`
 - `WEB=py-http-otel ROUTE=/redis/get/foo make curl`

### Stop

`make stop`

