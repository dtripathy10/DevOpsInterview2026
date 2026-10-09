# Install grafana

docker run -d --name=grafana -p 3000:3000 grafana/grafana


# Install Prometheus

docker run -d --name prometheus -p 9090:9090 prom/prometheus

docker run -d --name prometheus -p 9090:9090 -v C:\Users\dtrip\study_material\prometheus.yml:/etc/prometheus/prometheus.yml:ro prom/prometheus
