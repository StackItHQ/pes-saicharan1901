import pika

try:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    print("RabbitMQ is connected!")
    connection.close()
except pika.exceptions.AMQPConnectionError:
    print("Failed to connect to RabbitMQ.")
