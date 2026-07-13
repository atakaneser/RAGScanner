# Deployment strategy

There is no deployable API, dashboard, worker, Dockerfile, or Compose topology yet. The current
alpha supports local Python installation and package builds only.

The planned topology uses a FastAPI application and worker built from the same open image, bound to
localhost by default. Deployment files will be added only after those applications exist.
Kubernetes, a private registry, and cloud-only services are not planned requirements.
