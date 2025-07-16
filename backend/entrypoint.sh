#!/bin/bash
echo "10.120.128.159 llm-proxy.miracleplus.com" >> /etc/hosts
exec "$@"