FROM envoyproxy/envoy:v1.30.8

# Copy your local configuration file into the container
COPY envoy.yaml /etc/envoy/envoy.yaml

# Grant read permissions to the config file
RUN chmod go+r /etc/envoy/envoy.yaml
