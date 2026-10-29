<p align="center">
  <a href="https://mindcradle.online">
    <img src="frontend/public/mindcradle-logo.svg" alt="MindCradle Logo" width="320" />
  </a>
</p>

<p align="center">
  <strong>Enterprise-Grade Mental Wellness Platform Powered by Autonomous Relational Intelligence</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production-brightgreen?style=flat-square" alt="Production Status" />
  <img src="https://img.shields.io/badge/AWS-ALB%20%7C%20EC2%20%7C%20Route53-orange?style=flat-square&logo=amazon-aws" alt="AWS Infrastructure" />
  <img src="https://img.shields.io/badge/Monitoring-CloudWatch%20%7C%20SNS-FF4F00?style=flat-square&logo=amazon-cloudwatch" alt="CloudWatch & SNS Monitoring" />
  <img src="https://img.shields.io/badge/Auth-Amazon%20Cognito-blue?style=flat-square&logo=jsonwebtokens" alt="Amazon Cognito" />
  <img src="https://img.shields.io/badge/Database-Supabase%20pgvector-emerald?style=flat-square&logo=supabase" alt="Supabase Database" />
  <img src="https://img.shields.io/badge/Container-Docker%20Hub-2496ED?style=flat-square&logo=docker" alt="Docker Hub" />
</p>

---

## Overview

MindCradle is a mental wellness platform designed to facilitate longitudinal emotional reflection, habit formation, and stress modulation. Powered by a custom **Compounding Intelligence Engine (CIE)** and a relational companion named **ARIA**, MindCradle constructs a private, client-isolated **Personal Knowledge Graph (PKG)** to map emotional triggers, resilience trajectories, and seasonal shifts over time.

---

## CI/CD Pipeline Architecture (Local to AWS)

The continuous integration and continuous deployment (CI/CD) pipeline automates code validation, container compilation, image scanning, and zero-downtime deployment from local environments to production AWS infrastructure.

### Figure 1: CI/CD Pipeline & Automated Release Flow

<p align="center">
  <img src="docs/assets/ci-cd-architecture.svg" alt="MindCradle CI/CD Pipeline & Automated Release Flow" width="100%" />
</p>

```mermaid
flowchart LR
    subgraph S1["1. Local Development"]
        LocalCode["Developer Workspace"]
        GitCommit["git push origin <branch>"]
        LocalCode --> GitCommit
    end

    subgraph S2["2. Pull Request CI (ci.yml)"]
        direction TB
        RuffCheck["Ruff Linter (backend/app)"]
        PytestRun["Pytest Suite (test_*.py)"]
        ViteBuild["Vite Build & prerender.py"]
        SecretScan["Gitleaks Secret Detection"]
        TrivyFS["Trivy Filesystem Vulnerability Scan"]
    end

    subgraph S3["3. Production Release CD (build.yml)"]
        direction TB
        MergeMain["Push / Merge to main"]
        BuildBackend["docker build (mindcradle-backend)"]
        BuildFrontend["docker build (mindcradle-frontend)"]
        TrivyImages["Trivy Container Security Scan"]
    end

    subgraph S4["4. Central Container Registry"]
        HubPush["Docker Hub (docker.io)"]
        TagBackend["xuvm19/mindcradle-backend:latest"]
        TagFrontend["xuvm19/mindcradle-frontend:latest"]
    end

    subgraph S5["5. Production AWS EC2 Rollout"]
        direction TB
        SSHTrigger["appleboy/ssh-action (Port 22, EC2_SSH_KEY)"]
        DockerPull["docker compose -f docker-compose.prod.yml pull"]
        ComposeUp["docker compose up -d --remove-orphans"]
        ImagePrune["docker image prune -af --filter until=24h"]
        HealthCurl["Live Health Verification: GET /api/health (200 OK)"]
    end

    subgraph S6["6. Continuous Telemetry & Incident Alerting"]
        direction TB
        CWAgent["CloudWatch Unified Agent (RAM, Disk, Docker Logs)"]
        ALBTelemetry["ALB Metrics (5XX Errors, Latency, Target Group)"]
        Canary["Synthetics Canary (Heartbeat: /api/health)"]
        CWAlarms["CloudWatch Alarms (Static & Anomaly Detection)"]
        SNSTopic["Amazon SNS Topic (mindcradle-production-alerts)"]
        OnCall["Engineering Alerts (Email, PagerDuty, Slack)"]
        Dashboard["CloudWatch Dashboard (MindCradle-Production-Overview)"]
    end

    GitCommit -->|Open Pull Request| S2
    S2 -->|All checks pass & merged| MergeMain
    MergeMain --> BuildBackend & BuildFrontend
    BuildBackend & BuildFrontend --> TrivyImages
    TrivyImages --> HubPush
    HubPush --> TagBackend & TagFrontend
    TagBackend & TagFrontend --> SSHTrigger
    SSHTrigger --> DockerPull
    DockerPull --> ComposeUp
    ComposeUp --> ImagePrune
    ImagePrune --> HealthCurl
    HealthCurl -->|Verify Release & Hand Off| S6
    CWAgent & ALBTelemetry & Canary --> CWAlarms & Dashboard
    CWAlarms -->|Threshold Breach| SNSTopic
    SNSTopic -->|Instant Notification| OnCall
```

### Detailed CI/CD Pipeline & Continuous Operations Specification

1. **Stage 1 — Local Development**:
   - Engineers develop frontend (React 19, Tailwind) and backend (FastAPI, Python 3.11) components locally.
   - Pre-commit hooks via Husky execute linters and formatting checks prior to commit.

2. **Stage 2 — Pull Request Validation (`ci.yml`)**:
   - Automated checks trigger on PR creation: Ruff linting, Pytest test suites, Vite compilation with `prerender.py` static generation.
   - Security auditing runs Gitleaks for secret detection and Trivy for filesystem dependencies.

3. **Stage 3 & 4 — Production Build & Registry Staging (`build.yml`)**:
   - Merges to `main` compile multi-stage production Docker containers via Buildx with embedded Cognito client configuration.
   - Trivy performs vulnerability scanning on image layers before pushing to Docker Hub (`xuvm19/mindcradle-backend` and `xuvm19/mindcradle-frontend`).

4. **Stage 5 — Production EC2 Rollout**:
   - GitHub Actions invokes `appleboy/ssh-action` over secure SSH to EC2 host `mindcradle-prod` (`i-0b532745ffac5d935`).
   - Executes zero-downtime rolling pull and restart (`docker compose pull && docker compose up -d --remove-orphans`).
   - Automates post-deploy health polling against `https://mindcradle.online/api/health` (15 retries, 5s delay) requiring HTTP 200 OK before marking deployment successful.

5. **Stage 6 — Continuous Telemetry, CloudWatch Monitoring & Amazon SNS Incident Alerting**:
   - **Unified Host & Container Observability**: The `amazon-cloudwatch-agent` runs as a system daemon under IAM role `MindCradle-EC2-CloudWatch-Role`. It collects memory (`mem_used_percent`) and storage (`disk_used_percent`) every 60 seconds into custom namespace `MindCradle/System`, while tailing Docker container logs (`/var/lib/docker/containers/*/*-json.log`) into `/mindcradle/prod/docker`.
   - **Edge & Target Group Telemetry**: The Application Load Balancer (`mindcradle-alb`) and Target Group (`mindcradle-tg`) stream request volume, latency p95 (`TargetResponseTime`), and error codes (`HTTPCode_Target_5XX_Count`).
   - **CloudWatch Synthetics Canary**: An automated uptime monitor continuously exercises `https://mindcradle.online/api/health` from external AWS locations every 5 minutes.
   - **Multi-Vector CloudWatch Alarms**:
     - `MindCradle-ALB-Unhealthy-Host`: Triggers if target group unhealthy host count $\ge 1$.
     - `MindCradle-High-5XX-Errors`: Triggers if ALB 5XX error count $\ge 5$ across a 5-minute window.
     - `MindCradle-EC2-High-Memory`: Triggers if host memory usage exceeds 85%.
     - `MindCradle-EC2-Disk-Space-Low`: Triggers if host filesystem storage usage exceeds 85%.
     - `MindCradle-EC2-System-Check-Failed`: Triggers if underlying AWS EC2 hardware checks fail.
   - **Amazon SNS Incident Alerting**: All alarms publish state changes directly to the `mindcradle-production-alerts` SNS topic, which broadcasts immediate notifications to subscribed engineers via Email, Slack, or webhook endpoints.
   - **Single-Pane Operations Dashboard**: The `MindCradle-Production-Overview` CloudWatch dashboard aggregates alarm health status bars, CPU/RAM utilization curves, latency percentiles, and live FastAPI error streams.

---


## Web Application Infrastructure & Network Flow

MindCradle is deployed as an enterprise-grade, multi-tier containerized architecture in AWS `us-east-1`. Ingress traffic is managed by an Application Load Balancer across multiple Availability Zones with ACM TLS 1.3 encryption, native Amazon Cognito authentication hooks, and an isolated EC2 Docker bridge network.

### Figure 2: AWS Cloud Network Flow & Infrastructure Topology

<p align="center">
  <img src="docs/assets/aws-network-architecture.svg" alt="MindCradle AWS Production Network Flow & Infrastructure Topology" width="100%" />
</p>

```mermaid
flowchart TD
    UserClient(["User Web Client / Browser"])

    subgraph AWS_Edge["AWS Edge & DNS Ingress"]
        R53["AWS Route 53 (mindcradle.online & www.mindcradle.online)"]
        ACM["AWS Certificate Manager (Wildcard SSL / TLS 1.3)"]
    end

    subgraph AWS_ALB["AWS Application Load Balancer (mindcradle-alb)"]
        direction TB
        Subnets["Multi-AZ Subnet Mapping: us-east-1a, us-east-1b, us-east-1c"]
        HTTPListener["Port 80 Listener (Default Action: 301 Redirect to HTTPS Port 443)"]
        HTTPSListener["Port 443 Listener (Attached ACM SSL Certificate)"]
        
        subgraph ALB_Routing_Rules["Listener Rules & Authentication"]
            CognitoRule["Authenticate with Amazon Cognito (OIDC Action)"]
            ForwardAction["Forward Action: mindcradle-tg Target Group"]
        end
    end

    subgraph AWS_Cognito["AWS Identity & Access Management"]
        UserPool["Cognito User Pool (mindcradle-user-pool)"]
        HostedUI["Cognito Hosted UI (OAuth 2.0 Auth Code Grant)"]
        OIDCHeaders["Inject Headers: x-amzn-oidc-data, x-amzn-oidc-identity, x-amzn-oidc-accesstoken"]
        UserPool --- HostedUI
        HostedUI --> OIDCHeaders
    end

    subgraph AWS_TG["AWS Target Group (mindcradle-tg)"]
        direction TB
        TGConfig["Protocol: HTTP | Port: 8080 | Type: Instance"]
        HealthCheck["Health Check Path: /api/health (Interval: 30s, Healthy Threshold: 3)"]
        TargetInstance["Registered Target: i-0b532745ffac5d935 (mindcradle-prod) in us-east-1c [Healthy]"]
        TGConfig --- HealthCheck --- TargetInstance
    end

    subgraph AWS_EC2["AWS EC2 Host (Ubuntu 24.04 LTS | Instance: i-0b532745ffac5d935 in us-east-1c)"]
        HostPort["EC2 Host Inbound Port 8080 (Security Group: Allow traffic from ALB only)"]
        
        subgraph DockerNetwork["Internal Bridge Network (app-network)"]
            direction TB
            FrontendContainer["Frontend Container (mindcradle-frontend :8080)
            - Nginx Unprivileged Alpine
            - Serves React 19 Static Bundles + Pre-rendered SEO HTML
            - Reverse Proxy: /api/* -> http://backend:8080"]

            BackendContainer["Backend Container (mindcradle-backend :8080)
            - Python 3.11 + FastAPI ASGI (Uvicorn)
            - Decodes x-amzn-oidc-data & validates Bearer JWTs
            - Rate Limiting, CORS, CSRF Protection
            - Atomic Just-In-Time (JIT) Sync via RPC"]
        end
    end

    subgraph CloudServices["External Cloud, Persistence & AI Tier"]
        direction TB
        SupabaseDB[("Supabase Managed Database
        - PostgreSQL 15+
        - pgvector Semantic Embeddings Index
        - Row Level Security (RLS)
        - Realtime WebSocket Channels")]

        OpenRouterAPI["OpenRouter AI Gateway
        - Model: google/gemini-3.5-flash-lite (ARIA Companion)
        - Model: openai/text-embedding-3-small (Embeddings)"]

        CreemAPI["Creem Payment Infrastructure
        - Subscriptions & Checkout Sessions
        - Webhook Signature Verification"]

        MixpanelTelemetry["Mixpanel Product Analytics
        - Privacy-Gated Telemetry & Event Tracking"]
    end

    subgraph AWS_Monitoring["AWS Observability & Incident Response"]
        direction TB
        CWAgent["CloudWatch Unified Agent (EC2 Daemon)
        - Memory & Disk: MindCradle/System (60s)
        - Docker Logs: /mindcradle/prod/docker"]
        CWAlarms["CloudWatch Alarms (ALB 5xx, Memory, Disk, TG Health)"]
        SNSTopic["Amazon SNS Topic (mindcradle-production-alerts)"]
        CWDashboard["CloudWatch Dashboard (MindCradle-Production-Overview)"]
        CWAgent --> CWAlarms & CWDashboard
        CWAlarms -->|Threshold Breach| SNSTopic
    end

    UserClient -->|HTTPS Request :443| R53
    R53 --> ACM
    ACM --> HTTPSListener
    UserClient -.->|HTTP Request :80| HTTPListener
    HTTPListener -->|301 Redirect| HTTPSListener
    HTTPSListener --> CognitoRule
    CognitoRule <-->|OIDC Auth Flow| AWS_Cognito
    CognitoRule --> ForwardAction
    ForwardAction --> AWS_TG
    AWS_TG -->|Route Traffic :8080| HostPort
    AWS_TG -.->|Periodic Health Checks| HealthCheck
    HostPort --> FrontendContainer
    FrontendContainer -->|Serve UI Assets & HTML| UserClient
    FrontendContainer -->|Proxy /api Requests| BackendContainer
    BackendContainer <-->|JIT Profile Sync & Realtime WS| SupabaseDB
    BackendContainer <-->|AI Reflections & Vector Search| OpenRouterAPI
    BackendContainer <-->|Payment Verification & Webhooks| CreemAPI
    UserClient <-->|Consented User Events| MixpanelTelemetry
    AWS_EC2 -.->|System & Container Logs| CWAgent
    AWS_ALB -.->|Request & 5xx Metrics| CWAlarms
    AWS_TG -.->|Host Health Metrics| CWAlarms
```

### Detailed AWS Network Routing Specification

1. **DNS Resolution & Edge Ingress**:
   - The user visits `https://mindcradle.online`.
   - **AWS Route 53** resolves the domain via an ALIAS A-record directly to the dual-stack DNS endpoint of the Application Load Balancer.
   - **AWS Certificate Manager (ACM)** validates the wildcard domain certificate and terminates TLS 1.3 encryption at the edge.

2. **Load Balancer & Multi-AZ Mapping**:
   - The ALB is configured with subnets spanning three availability zones: `us-east-1a`, `us-east-1b`, and `us-east-1c`.
   - Port 80 listener intercepts non-secure requests and returns a 301 permanent redirect to port 443 with HTTPS protocol preserved.

3. **Cognito Zero-Code & Token Authentication**:
   - The port 443 listener integrates natively with **Amazon Cognito User Pool** (`mindcradle-user-pool`).
   - Unauthenticated visitors are redirected to the Cognito Hosted UI or authenticate through the client SPA application.
   - Upon successful verification, the ALB injects the user's validated cryptographic identity into HTTP headers:
     - `x-amzn-oidc-data`: Base64url-encoded JSON claims payload containing user identity, email, and attributes.
     - `x-amzn-oidc-identity`: Unique Amazon Cognito user identity sub.
     - `x-amzn-oidc-accesstoken`: Raw Cognito OAuth 2.0 access token.

4. **Target Group Routing & Health Checks**:
   - Validated traffic is routed to target group `mindcradle-tg` on port 8080.
   - The target group continuously verifies instance health by requesting `/api/health` every 30 seconds.
   - The target instance `i-0b532745ffac5d935` (`mindcradle-prod`) is hosted in `us-east-1c` and maintains a `Healthy` status.

5. **Host Isolation & Docker Bridge Routing**:
   - The EC2 security group only allows inbound TCP traffic on port 8080 originating from the ALB security group, blocking direct public access.
   - Inside the host, Docker Compose exposes port 8080 through the Nginx frontend container.
   - Nginx serves pre-rendered static assets directly to clients with cache headers, and reverse-proxies `/api/*` traffic over the internal Docker network `app-network` to `http://backend:8080`.
   - FastAPI parses `x-amzn-oidc-data` or verifies Bearer tokens, runs atomic Just-In-Time synchronization against Supabase, and connects to OpenRouter for AI inference.

6. **Observability, Metric Ingestion & Incident Alerting**:
   - The **Amazon CloudWatch Unified Agent** (`amazon-cloudwatch-agent`) runs as an in-guest daemon under IAM role `MindCradle-EC2-CloudWatch-Role`.
   - OS-level telemetry (`mem_used_percent`, `disk_used_percent`) is ingested every 60 seconds into custom namespace `MindCradle/System`, while container output (`/var/lib/docker/containers/*/*-json.log`) and `/var/log/syslog` stream to CloudWatch Log Groups.
   - ALB and Target Group metrics (`UnHealthyHostCount`, `HTTPCode_Target_5XX_Count`, `TargetResponseTime`) track edge and ingress health.
   - Five static and anomaly alarms monitor uptime and infrastructure thresholds. Any metric breach automatically publishes to the **Amazon SNS** topic `mindcradle-production-alerts` for instant notification routing.
   - Engineering teams operate with the unified **CloudWatch Dashboard** (`MindCradle-Production-Overview`) providing real-time visibility across all layers.

---

## Core Engineering Features

- **Compounding Intelligence Engine (CIE)**: Dynamically extracts user themes, linguistic markers, and recurring coping mechanisms, building a persistent personal knowledge base.
- **ARIA Relational AI Companion**: Operates with longitudinal memory instead of isolated session contexts, detecting cognitive shifts, validating feelings, and offering non-clinical guidance.
- **Hybrid Semantic Search**: Combines traditional keyword matching with pgvector embeddings to retrieve entries, journal reflections, and past mood states via natural language queries.
- **Just-In-Time (JIT) Identity Sync**: Decodes and cryptographically validates incoming Cognito RS256 JWTs or ALB OIDC headers and atomically synchronizes identity records into Supabase `user_profiles`.
- **Pre-Rendered Static Generation**: Custom build script executes after Vite compilation to generate prerendered HTML for all public marketing, documentation, and blog routes to maximize search indexing speed.

---

## Local Development & Setup

### Prerequisites

- **Docker & Docker Compose**: Version 24+
- **Node.js**: Version 20.x or higher
- **Python**: Version 3.11.x
- **Supabase Account**: With active PostgreSQL database

### 1. Database Setup

1. Open your Supabase project dashboard.
2. Navigate to the **SQL Editor**.
3. Execute the migration scripts sequentially from `backend/supabase/migrations/` (from `001_initial_schema.sql` through `030_add_cognito_support_and_realtime.sql`).

### 2. Backend Configuration

1. Move to the backend folder:
   ```bash
   cd backend
   ```
2. Initialize and activate Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment parameters:
   ```bash
   cp .env.example .env
   ```
5. Start development API service:
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

### 3. Frontend Configuration

1. Move to the frontend folder:
   ```bash
   cd ../frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Copy local environment variables:
   ```bash
   cp .env.example .env.local
   ```
4. Start the Vite development server:
   ```bash
   npm run dev
   ```

### 4. Running Full Stack via Production Compose

To replicate the production environment locally:
```bash
docker compose -f docker-compose.prod.yml up --build
```
The application will be accessible at `http://localhost:3000`.

---

## Production Deployment & Secrets Matrix

The following secrets must be configured in the GitHub repository settings (`Settings -> Secrets and variables -> Actions`) to enable automated CI/CD deployment:

| Secret Name | Description | Example / Format |
|---|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub organization or username | `xuvm19` |
| `DOCKERHUB_TOKEN` | Docker Hub Personal Access Token (Read & Write permissions) | `dckr_pat_...` |
| `EC2_HOST` | Public IP or Elastic IP of the AWS EC2 instance | `54.xxx.xxx.xxx` |
| `EC2_USER` | Remote SSH login user | `ubuntu` |
| `EC2_SSH_KEY` | Private SSH key (PEM format) associated with the EC2 instance key pair | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

---

## Security & Verification Standards

- **Zero Hardcoded Secrets**: All credentials and sensitive API tokens are decoupled into environment variables.
- **Static Analysis & Security Scans**: Continuous integration scans all pull requests with Gitleaks for leaked tokens and Trivy for filesystem and container vulnerabilities.
- **Strict Headers**: Production responses enforce Content Security Policy (CSP), HTTP Strict Transport Security (HSTS with preload), `X-Frame-Options: DENY`, and `X-Content-Type-Options: nosniff`.
- **Stateless Authentication**: Access tokens are signed JWTs with short expiry periods; refresh tokens are stored in secure, `HttpOnly`, `SameSite=Strict` cookies.

---

## Repository Structure

```text
.
|-- .github/
|   `-- workflows/
|       |-- ci.yml                   # Pull request validation: Lint, Test, Build, Scan
|       `-- build.yml                # Main push deployment: Buildx, Docker Hub, SSH EC2 Deploy
|-- backend/
|   |-- app/
|   |   |-- core/                    # Security, JWT cryptography, Cognito token exchange, JIT sync
|   |   |-- models/                  # Pydantic validation schemas
|   |   |-- routers/                 # API controllers (auth, ai, journal, mood, rituals, user)
|   |   |-- services/                # Supabase, pgvector embeddings, OpenRouter integration
|   |   |-- config.py                # Environment configuration loader
|   |   `-- main.py                  # FastAPI application entrypoint and middleware
|   |-- supabase/
|   |   `-- migrations/              # SQL database schemas and stored procedures (001-030)
|   |-- Dockerfile                   # Multi-stage production container build for backend
|   `-- requirements.txt             # Python production dependencies
|-- frontend/
|   |-- src/
|   |   |-- app/
|   |   |   |-- components/          # Reusable UI components and modals
|   |   |   `-- pages/               # Application view controllers and route pages
|   |   |-- lib/                     # API client, Auth Context, Realtime WebSocket listener
|   |   `-- styles/                  # Tailwind CSS styling and theme specifications
|   |-- nginx.conf.template          # Production reverse proxy and caching configuration
|   |-- Dockerfile                   # Multi-stage container build with pre-rendered pages
|   `-- package.json                 # Frontend dependencies and npm scripts
|-- docker-compose.prod.yml          # Production multi-container composition
`-- prerender.py                     # Headless static page generation script for SEO
```

---


## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
