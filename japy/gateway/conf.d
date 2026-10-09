server {
    listen       8980;

    #access_log  /var/log/nginx/host.access.log  main;

    location /app2/ {
        proxy_pass  "http://app2.python.dev/";
    }

    location /app3/ {
        proxy_pass  "http://app3.python.dev/";
    }

    location /app4/ {
        proxy_pass  "http://app4.python.dev/";
    }

    location /app5/ {
        proxy_pass  "http://app5.node.dev/";
    }
}
