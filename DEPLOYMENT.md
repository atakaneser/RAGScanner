# Deployment strategy

The Python distribution includes a loopback FastAPI/dashboard process and a separate durable worker
command. There is no supported Dockerfile, Compose topology, remote bind, or public deployment yet.

The planned container topology will run the existing FastAPI application and worker from the same
open image, bound to localhost by default and sharing SQLite/artifact storage. Deployment files will
be added only after packaging and recovery acceptance.
Kubernetes, a private registry, and cloud-only services are not planned requirements.
