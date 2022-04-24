from web import app
from random import randint
from time import sleep
import json
import redis
import os


from ddtrace import Pin
from ddtrace import tracer

service_str = os.getenv('SERVICE')
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

# initialize Redis

app.logger.info(f'connecting to Redis0. host={redis0_host} port={redis0_port}')
redis0_client = redis.StrictRedis(host=redis0_host, port=redis0_port)

app.logger.info(f'connecting to Redis1. host={redis1_host} port={redis1_port}')
redis1_client = redis.StrictRedis(host=redis1_host, port=redis1_port)


redis_service_name_by_identity = {
    redis0_identity: service_str + '-redis', # naming convention
    redis1_identity: 'another-service-redis'
}

# use ddtrace.config.redis["service"] if only 1 instance of redis is used.
# use Pin.override to instrument per service.
# https://ddtrace.readthedocs.io/en/stable/integrations.html#redis
Pin.override(redis0_client, service=redis_service_name_by_identity[redis0_identity])
Pin.override(redis1_client, service=redis_service_name_by_identity[redis1_identity])

@app.route('/')
def index():
    return 'ok'


@app.route('/foo')
def foo():
    return 'okay'


@app.route('/open')
def open():
    with tracer.trace('foo'):
        with tracer.trace('bar'):
            app.logger.info('Hello world!')
    return 'ok'


@tracer.wrap(name='delay')
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
