FROM envoyproxy/envoy:v1.16-latest

COPY entrypoint.sh /
RUN chmod 500 /entrypoint.sh
RUN apt-get update && apt-get install curl -y

ENTRYPOINT ["/entrypoint.sh"]