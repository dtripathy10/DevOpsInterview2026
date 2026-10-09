docker build -f Dockerfile.dev -t flask-dev .

docker run --rm --name flask-dev -p 5000:5000 -v "C:/Users/dtrip/DevOpsInterview2026/pylearn:/app" flask-dev
