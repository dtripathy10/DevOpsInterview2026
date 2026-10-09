docker build -t my-envoy:v4 .

docker run -d --name envoy-proxy -v C:\Users\dtrip\study_material\envoy-logs:/var/log/envoy -p 9901:9901 -p 10000:10000 my-envoy:v4

docker stop envoy-proxy