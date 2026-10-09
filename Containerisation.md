# Containerisation
## What problem does it solve?
- **Platform-agnostic package management**: Packages application artifacts and their dependencies for distribution. Examples include RPM for Fedora/Red Hat, DEB for Ubuntu, and EXE installers for Windows. However, applications may still depend on OS-level components, such as a specific JDK version for a Java application, which can cause dependency conflicts during deployment.

- **Lightweight**: Containers are more lightweight than virtual machines because they share the host OS kernel rather than running a separate guest OS.

- **Resource control**: Containers allow resource limits to be configured for CPU, memory, and other computing resources.

## Docker
- **Docker**: A containerisation technology used to build, package, and run applications in containers.
- **Docker architecture**: Includes the Docker Engine, Docker daemon, and image registries. Base images provide the foundation for building application-specific images by adding application code and configuration.
- **Reference**: https://docs.docker.com/get-started/docker-overview/

## Key Terminology
- **Container**: An isolated process running an application from a Docker image.
- **Image**: A read-only template containing application binaries, dependencies, and configuration required to run an application.
- **Image Registry**: A central repository for storing and distributing Docker images, similar to an artifact repository such as JFrog Artifactory. It can store both base images and application-specific images.
- **Dockerfile**: A file containing instructions for building a Docker image. https://docs.docker.com/reference/dockerfile/
- **Docker Compose**: A tool for defining and running multi-container applications using a YAML configuration file.

## Important Docker Concept
- Build cache (BuildKit)
- **Multi-stage builds**: A multi-stage build separates the application build environment from the runtime environment. This reduces the final image size by excluding build tools and other unnecessary files.
- Docker image build best practices https://docs.docker.com/build/building/best-practices/

## Interview Question
- https://github.com/Devinterview-io/docker-interview-questions
- CLI Cheat Sheet - https://docs.docker.com/get-started/docker_cheatsheet.pdf

## EntryPoint Pattern in Dockerfile

- https://github.com/jetty/jetty.docker/blob/master/amazoncorretto/12.0/jdk17-alpine/docker-entrypoint.sh

- https://github.com/nodejs/docker-node/blob/main/docker-entrypoint.sh


## Interview Questions

- How do you publish docker build, container execution & event logs to splunk?
- How do you access a web server running on the host netowrk?
- How do you pass secrets to a Docker image build?
- How do you add custom logic during a container run? For example, how do you verify that a database is running properly before starting a web server, and halt the process if it is not?
- How do you access a process running on the host from inside a Docker container? For example, if you have a custom process on the host that can be invoked via a command-line argument, how would you execute or trigger it from within the container?
- How would you reduce image size and build time? (Multi-stage builds, layer caching, .dockerignore, base image choice)
- How do you make builds reproducible, and how do you handle vulnerable base images over time?
- What happens when you docker stop? Why might a container take 10 seconds to stop? (PID 1, SIGTERM handling, graceful shutdown)