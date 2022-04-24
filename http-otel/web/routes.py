from web import app
from random import randint
from time import sleep
import json
import os
import redis


# OpenTelemetry implementation
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter


## OT implementation 0 (being depracated)
# use opentelemetry-exporter-datadog:https://opentelemetry-python.readthedocs.io/en/latest/examples/datadog_exporter/README.html
# telemetry data are translated within the app and transferred to datadog agent with datadog protocol.

# from opentelemetry.exporter.datadog import (
#     DatadogExportSpanProcessor,
#     DatadogSpanExporter,
# )
# 
# exporter = DatadogSpanExporter(
#     agent_url='http://datadog:8126', service='<service_name>'
# )

# span_processor = DatadogExportSpanProcessor(exporter)


## OT implementation 1
# use opentelemetry-exporter-otlp
# telemetry data are transferred to collector / datadog agent in otlp protocol.

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# important
# one resource per entity
# one tracer provider per resource

env_str = os.getenv('ENV')
service_str = os.getenv('SERVICE')
service_version = os.getenv('VERSION')
redis0_host = os.getenv('REDIS0_HOST')
redis1_host = os.getenv('REDIS1_HOST')
redis0_port = os.getenv('REDIS0_PORT')
redis1_port = os.getenv('REDIS1_PORT')
shared_redis_service_name = os.getenv('SHARED_REDIS_SERVICE_NAME')

# if necessary, db can be added to the identity defition too
def _redis_identity_from_hostport(host: str, port: str) -> str:
    return host + ':' + port

redis0_identity = _redis_identity_from_hostport(redis0_host, redis0_port)
redis1_identity = _redis_identity_from_hostport(redis1_host, redis1_port)

if redis0_identity == redis1_identity:
    app.logger.error('REDIS0 and REDIS1 are identical')
    sys.exit(1) 

redis_service_name_by_identity = {
    redis0_identity: service_str + '-redis', # naming convention
    redis1_identity: shared_redis_service_name
}

## Resources
api_rs = Resource(attributes={
    'service.name': service_str + '-api',
    'deployment.environment': env_str,
    'service.version': service_version
}) # optional: 'service.instance.id'

# Redis instrumentation does not support more than 1 resource / trace provider:
# instrument on the library instead of an instance (client / connection)

# same principal for all the supported instrumentation (redis, requests, etc)
# if only 1 resource (redis host in this case) is used, use resource / trace provider to instrument
# if more than 1 resource (redis host in this case) is used , use hook to set span attributes to override resource attributes
redis_rs = Resource(attributes={
    'service.name': service_str + '-redis',
    'deployment.environment': env_str,
    'service.instance.id': redis0_host,
})

## trace providers

# for applition itself. populated from OTEL_RESOURCE_ATTRIBUTES
# alternatively, it can be created with Resource.create + environment variables.
api_tracer_provider = TracerProvider(resource=api_rs)
redis_tracer_provider = TracerProvider(resource=redis_rs)


app.logger.info(f'OTEL_EXPORTER_OTLP_ENDPOINT={os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")}')
app.logger.info(f'OTEL_EXPORTER_OTLP_TRACES_ENDPOINT={os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")}')
app.logger.info(f'OTEL_SERVICE_NAME={os.getenv("OTEL_SERVICE_NAME")}')
app.logger.info(f'OTEL_RESOURCE_ATTRIBUTES={os.getenv("OTEL_RESOURCE_ATTRIBUTES")}')


otlp_exporter = OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"), insecure=True)

span_processor = BatchSpanProcessor(otlp_exporter)

api_tracer_provider.add_span_processor(span_processor)
redis_tracer_provider.add_span_processor(span_processor)

# for debugging purpose.
span_processor1 = BatchSpanProcessor(ConsoleSpanExporter())
api_tracer_provider.add_span_processor(span_processor1)
redis_tracer_provider.add_span_processor(span_processor1)

# use the api tracer provider as the global one
trace.set_tracer_provider(api_tracer_provider)


# initialize redis instrument.
# use request_hook / response_hook if necessary

# args and kwargs in hook signature: passed from execute_command method:
# https://redis-py.readthedocs.io/en/stable/_modules/redis/client.html

def override(span, instance):
    if span and span.is_recording():
        # span attributes can override resource attributes.

        # instance type: redis.client.Redis

        # if redis db need to be part of "service.name"'s identity:
        # db = instance.get_connection_kwargs()['db']
        identity = _redis_identity_from_hostport(instance.get_connection_kwargs()['host'], instance.get_connection_kwargs()['port'])

        if identity in redis_service_name_by_identity:
            span.set_attribute('service.name', redis_service_name_by_identity[identity])
            # override environment, version if needed.
        else:
            app.logger.warning(f'method="override" msg="unknown identity" identity={identity}')

def req_hook(span, instance, args, kwargs):
    override(span, instance)

def res_hook(span, instance, response):
    override(span, instance)

RedisInstrumentor().instrument(tracer_provider=redis_tracer_provider, request_hook=req_hook, response_hook=res_hook)

FlaskInstrumentor().instrument_app(app) # tracer_provider=api_tracer_provider

# initialize Redis

app.logger.info(f'connecting to Redis0. host={redis0_host} port={redis0_port}')
redis0_client = redis.StrictRedis(host=redis0_host, port=redis0_port)

app.logger.info(f'connecting to Redis1. host={redis1_host} port={redis1_port}')
redis1_client = redis.StrictRedis(host=redis1_host, port=redis1_port)

@app.route('/')
def index():
    return 'ok'


@app.route('/foo')
def foo():
    return 'okay'


tracer_name = 'opentelemetry.instrumentation.flask'
app.logger.info(f'creating opentelemetry tracer. name={tracer_name}')
tracer = trace.get_tracer(tracer_name)


@app.route('/open')
def open():
    with tracer.start_as_current_span('foo'):
        with tracer.start_as_current_span('bar'):
            app.logger.info('Hello world from OpenTelemetry Python!')
    return 'ok'


def delay_response(up_to_int):
    up_to = max(0, up_to_int)
    delay_ms = randint(0,up_to)
    app.logger.info(f'delay_ms={delay_ms}')
    sleep(delay_ms / 1000) # convert to seconds
    return 'ok'


@app.route('/delay/<up_to_str>')
def delay(up_to_str=0):
    up_to = 0
    try:
        up_to = int(up_to_str)
    except ValueError:
        pass

    return delay_response(up_to)


@app.route('/redis/get/<key>')
def redis_get(key):
    return json.dumps({
        redis0_identity: str(redis0_client.get(key)),
        redis1_identity: str(redis1_client.get(key))
    })
