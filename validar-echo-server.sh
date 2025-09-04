#!/bin/bash

TESTING_MESSAGE="Validating message"
NETWORK_NAME="tp0_testing_net"
CONTAINER_NAME="server"
SERVER_PORT=12345

response=$(docker run -i --rm --network=$NETWORK_NAME alpine:latest sh -c "echo '$TESTING_MESSAGE' | nc -w 5 $CONTAINER_NAME $SERVER_PORT" | tr -d '\r\n')

if [ "$response" = "$TESTING_MESSAGE" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi
