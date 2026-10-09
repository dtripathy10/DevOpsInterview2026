# Container/Docker
- Universal Applicatin Packaging & Distribution System
- Basically it has 3 parts - Build, Push & Run


## Application Build

docker build -t python_app_1 ./python_app_1
docker build -t python_app_2 ./python_app_2
docker build -t python_app_3 ./python_app_3
docker build -t python_app_4 ./python_app_4

docker image ls
docker run --rm python_app_1

docker run -it -p 5000:5000 -d python_app_1  
docker run -it -p 5001:5000 -d python_app_2  
docker run -it -p 5002:5000 -d python_app_3  
docker run -it -p 5003:5000 -d python_app_4  

docker containers ls  

docker ps
docker exec -it 7270f5176826 sh 



# list out image
docker image ls

## delete unused image
docker image prune -a

# image tag
docker tag <image name> <new image tag name>
docker tag c62409fd7f2f jappy/awesome_app


# docker remote repo config




