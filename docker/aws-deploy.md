# SafeHire: Docker → ECR → ECS Express Mode → CloudFront

End state: browser hits **one CloudFront URL**; **`/*`** → Next.js service, **`/api/*`** → FastAPI service. Images live in **ECR**; **GitHub Actions** pushes on `main`; your compute tier pulls **`latest`** (or a pinned digest).

---

## AWS App Runner notice (legacy)

**Starting April 30, 2026, AWS App Runner is not accepting new customers.** Existing App Runner services remain supported for security and availability, but AWS recommends **Amazon ECS Express Mode** for new container deployments. See [ECS Express Mode overview](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html) and AWS migration guidance from App Runner.

This guide uses **ECS Express Mode** as the default path. If you already run on App Runner, keep **§8–§11** the same idea: use each service’s **HTTPS URL** as a CloudFront origin.

---

## 1. Dockerize FastAPI backend

Already in **`backend/Dockerfile`**: Python 3.12 slim, `requirements.txt`, `uvicorn app.main:app` on port **8000**, healthcheck **`GET /health`**.

```bash
docker build -t safehire-backend ./backend
```

---

## 2. Dockerize Next.js frontend

Already in **`frontend/Dockerfile`**: multi-stage build, **`output: "standalone"`** in `next.config.ts`, **`node server.js`** on port **3000**.

Build args (inlined at build time):

- **`NEXT_PUBLIC_API_URL`** — must be the browser-visible API base, ending with **`/api`** for CloudFront routing (e.g. `https://d111111abcdef8.cloudfront.net/api`).
- **`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`** (+ optional sign-in/up URL args).

Runtime on the **frontend** task/service: **`CLERK_SECRET_KEY`**.

```bash
docker build -t safehire-frontend \
  --build-arg NEXT_PUBLIC_API_URL=https://YOUR_CLOUDFRONT.cloudfront.net/api \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_... \
  ./frontend
```

---

## 3. Test locally with Docker Compose

From repo root:

```bash
docker compose build
docker compose up
```

| Service   | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost:3000        |
| Backend   | http://localhost:8000        |

Checks:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/workers
```

Default compose sets **`NEXT_PUBLIC_API_URL=http://localhost:8000/api`** for the web image.

First-time Chroma index (inside backend container):

```bash
docker compose exec backend python -m app.rag.ingest
```

---

## 4. Create ECR repositories

```bash
export AWS_REGION=us-east-1   # or your region

aws ecr create-repository --repository-name safehire-backend --region "$AWS_REGION"
aws ecr create-repository --repository-name safehire-frontend --region "$AWS_REGION"
```

---

## 5. Push backend and frontend images to ECR

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

docker tag safehire-backend:latest "${REGISTRY}/safehire-backend:latest"
docker tag safehire-frontend:latest "${REGISTRY}/safehire-frontend:latest"

docker push "${REGISTRY}/safehire-backend:latest"
docker push "${REGISTRY}/safehire-frontend:latest"
```

**If `docker tag` fails with** `"/safehire-frontend:latest" is not a valid repository/tag` **:** `${REGISTRY}` was empty. You must run the three `export` lines (`AWS_REGION`, `AWS_ACCOUNT_ID`, `REGISTRY`) in the **same shell** as `docker tag` / `docker push`, and `aws sts get-caller-identity` must succeed (CLI configured).

---

## 6. Deploy backend with Amazon ECS Express Mode

Express Mode provisions **Fargate**, **Application Load Balancer**, HTTPS URL, and health checks from a single workflow. Console: **Amazon ECS** → create an **Express** / **Express Mode** service (wording may vary slightly by region).

| Setting            | Value                                      |
|--------------------|--------------------------------------------|
| Container image    | `${REGISTRY}/safehire-backend:latest`      |
| Container port     | **8000**                                   |
| Health check path  | **`/health`**                              |

**Environment variables** (examples — map to console or `primary-container.environment` in API):

| Name             | Notes                                      |
|------------------|--------------------------------------------|
| `OPENAI_API_KEY` | From Secrets Manager / SSM if preferred    |
| `CORS_ORIGINS`   | Set **after** CloudFront exists — see §11   |
| `LANGSMITH_*`    | Optional tracing                           |

You need an **ECS task execution role** (pull from ECR, logs) and **Express infrastructure role** as prompted by the console; AWS can create managed roles.

**CLI** (illustrative — confirm flags against current `aws ecs create-express-gateway-service` docs):

```bash
aws ecs create-express-gateway-service \
  --region "$AWS_REGION" \
  --service-name safehire-backend \
  --execution-role-arn arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole \
  --infrastructure-role-arn arn:aws:iam::ACCOUNT:role/ecsInfrastructureRoleForExpressServices \
  --health-check-path /health \
  --primary-container "{\"image\":\"${REGISTRY}/safehire-backend:latest\",\"containerPort\":8000}"
```

Docs: [Express service overview](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html).

Copy the **public HTTPS URL** for the backend service (ALB hostname).

Smoke test:

```bash
curl -s "https://YOUR_BACKEND_EXPRESS_URL/health"
curl -s "https://YOUR_BACKEND_EXPRESS_URL/api/workers"
```

---

## 7. Deploy frontend with ECS Express Mode

Create a **second** Express service:

| Setting            | Value                                      |
|--------------------|--------------------------------------------|
| Image              | `${REGISTRY}/safehire-frontend:latest`     |
| Container port     | **3000**                                   |
| Health check path  | **`/`**                                    |

**Environment variable**:

| Name               | Notes                                |
|--------------------|--------------------------------------|
| `CLERK_SECRET_KEY` | Required for Clerk server middleware |

**Important:** For production, rebuild the frontend image with **`NEXT_PUBLIC_API_URL=https://YOUR_CLOUDFRONT_DOMAIN.cloudfront.net/api`** after the distribution exists (§12). For an early smoke test only, you may temporarily use **`https://YOUR_BACKEND_EXPRESS_URL/api`** as the build arg, then rebuild.

Copy the **frontend** Express HTTPS URL.

---

## 8. Put CloudFront in front of both services

**CloudFront → Create distribution**

### Origin A — frontend (Next.js)

- **Origin domain**: HTTPS hostname of your **frontend Express / ALB** URL (not the CloudFront domain).
- **Protocol**: HTTPS only.

### Origin B — backend (FastAPI)

- **Origin domain**: HTTPS hostname of your **backend Express / ALB** URL.

---

## 9. Route `/api/*` to backend

Add a **behavior** (more specific paths **before** default):

| Path pattern | Origin          | Cache policy        |
|--------------|-----------------|---------------------|
| `/api/*`     | Backend origin  | **CachingDisabled** |

Allowed methods: include **GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE** as needed.

Origin request policy: e.g. **AllViewerExceptHostHeader** so the viewer `Host` header does not break routing to the ALB.

---

## 10. Route `/*` to frontend

**Default behavior** (`*`):

| Setting           | Value                          |
|-------------------|--------------------------------|
| Origin            | Frontend origin                |
| Viewer protocol   | Redirect HTTP to HTTPS         |
| Cache policy      | Start with **CachingDisabled** for dynamic Next.js |

---

## 11. Configure CORS

FastAPI reads **`CORS_ORIGINS`**: comma-separated browser origins (no trailing slash).

Example:

```text
CORS_ORIGINS=https://d111111abcdef8.cloudfront.net,https://app.yourdomain.com
```

If unset, the API allows **`*`** (dev only — **set explicit origins in production**).

Update the **backend** ECS task/service environment and **deploy** a new revision after changing variables.

---

## 12. GitHub Actions — build and push images

Workflow: **`.github/workflows/deploy.yml`** (push to **`main`** or **workflow_dispatch**).

**Repository secret**

| Name                  | Value                                      |
|-----------------------|--------------------------------------------|
| `AWS_ROLE_TO_ASSUME`  | IAM role ARN for OIDC (`sts:AssumeRole`)   |

**Repository variables**

| Name                               | Example                                      |
|------------------------------------|----------------------------------------------|
| `NEXT_PUBLIC_API_URL`              | `https://YOUR_DIST.cloudfront.net/api`       |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`| Your Clerk publishable key                   |

Extend the role/policy if you want CI to call **`aws ecs update-express-gateway-service`** after push (optional).

IAM trust policy (minimal — tighten `sub` to your repo):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com" },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/SafeHire-AI-Risk-Investigator:*"
        }
      }
    }
  ]
}
```

Attach ECR push permissions for `safehire-backend` / `safehire-frontend`.

---

## 13. Rolling out new images (ECS Express Mode)

After CI pushes **`latest`** to ECR:

**Console:** ECS → your Express service → **Update** → set container image to the new URI/tag (or same `:latest` after push).

**CLI:** use **`aws ecs update-express-gateway-service`** with the service ARN and updated `primary-container` image (see [AWS CLI reference](https://docs.aws.amazon.com/cli/latest/reference/ecs/update-express-gateway-service.html)).

Optional: add a workflow job that updates both services using OIDC + ECS permissions.

*(Legacy App Runner users: enable **Automatic deployment** on each service so ECR pushes trigger redeploys.)*

---

## 14. Test CloudFront URL

```bash
curl -s "https://CF.cloudfront.net/api/health"
curl -s "https://CF.cloudfront.net/api/workers" | head -c 400
```

Browser: **`https://CF.cloudfront.net`** → Clerk → dashboard → investigate / ask.

If **`/api/*`** fails, verify behavior order (**`/api/*`** before **`*`**), HTTPS origins, and that the backend origin responds over HTTPS directly.

---

## Quick reference

| Concern              | Where                                                |
|----------------------|------------------------------------------------------|
| New AWS containers   | **ECS Express Mode** (not new App Runner customers from 2026-04-30) |
| Duplicate API paths  | **`/workers`** and **`/api/workers`** both work locally |
| CloudFront canonical | **`NEXT_PUBLIC_API_URL=https://…cloudfront.net/api`** |
| Chroma persistence   | Mount **EFS** at `/app/app/rag/.chroma` and `.embedding_models` on the API task |
| Rebuild frontend     | Whenever **`NEXT_PUBLIC_*`** or CloudFront URL changes |
