import pytest
import rabbitpy


QUEUE = 'test-queue'
EXCHANGE = 'test-exchange'
ROUTING_KEY = 'test-rk'
URL = 'amqp://guest:guest@localhost:5672/%2F'


@pytest.fixture(scope="module")
def connection(request):
    conn = rabbitpy.Connection(url= URL)
    def rabbitmq_conn_teardown():
        conn.close()
    request.addfinalizer(rabbitmq_conn_teardown)
    return conn


@pytest.fixture(scope="function")
def setup_channel(connection, request):
    channel = connection.channel()
    def channel_teardown():
        channel.close()
        rabbitpy.delete_queue(queue_name=QUEUE)
    request.addfinalizer(channel_teardown)

    exchange = rabbitpy.Exchange(channel, EXCHANGE)
    exchange.declare()

    queue = rabbitpy.Queue(channel, QUEUE)
    queue.declare()

    queue.bind(EXCHANGE, ROUTING_KEY)
    return channel


def test_rabbitmq_ping_pong(setup_channel):
    channel = setup_channel
    ACK = 'control message'

    def publish_message(arg):
        message = rabbitpy.Message(channel, arg)
        message.publish(EXCHANGE, ROUTING_KEY)

    publish_message(ACK)
    message = next(rabbitpy.Queue(channel, QUEUE).consume())
    assert message.body.decode() == ACK
    message.ack()


@pytest.mark.xfail
def test_rabbitmq_connection_is_not_available():
    with pytest.raises(RuntimeError) as exc_info:
        rabbitpy.Connection(url=URL)
    assert exc_info.value.args[0] == "Timeout waiting for opening the socket"