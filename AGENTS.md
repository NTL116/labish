
## 2. Structural Principles for AI Generation

### A. Strict Integration vs. AI Separation
Do not bundle core business workflows inside the AI layer. AI agents must interact with external interfaces purely by executing specialized wrappers inside `ai/tools/`, which import and execute structured methods from `integrations/sap/`.

python
# apps/api/app/integrations/sap/service_layer.py
class SAPServiceLayerClient:
    Core enterprise infrastructure engine. Independent of AI status."""
    def create_sales_order(self, order_data: dict) -> dict:
        # Direct HTTP communication logic with the SAP Service Layer
        return {"DocEntry": 1234, "Status": "Success"}

# apps/api/app/ai/tools/sap_tools.py
from app.integrations.sap.service_layer import SAPServiceLayerClient

def sap_order_tool(order_data: dict) -> str:
    AI visible tool schema used strictly as an agent interface wrapper."""
    client = SAPServiceLayerClient()
    result = client.create_sales_order(order_data)
    return f"Order successfully pushed to SAP. DocEntry: {result['DocEntry']}"

### B. Event-Driven Workflow Management
Avoid hard-coding direct function calls between the web controllers and async workers. Use an event paradigm inside `app/events/` to broadcast state transitions via Redis.

```python
# apps/api/app/events/orders.py
from sqlmodel import SQLModel
import uuid

class OrderSubmittedEvent(SQLModel):
    event_id: uuid.UUID
    customer_id: uuid.UUID
    order_total: float
```

### C. Unified Single-Source Schemas (`SQLModel`)
To prevent parameter mismatches and hallucinations, the AI engine must use `SQLModel` for data tables, ensuring the exact same class definition models the PostgreSQL table structures and provides input parsing attributes simultaneously.

```python
# apps/api/app/models/user.py
from typing import Optional
from sqlmodel import Field, SQLModel
import uuid

class User(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = True


### D. Asymmetric Local Token Control (RS256 JWT)
Do not use extensive third-party framework layers like `fastapi-users`. Build custom, lightweight token validators inside `core/security.py` using `PyJWT` and `passlib[bcrypt]`. Sign sessions via a private key; verify them locally across endpoints utilizing a public key payload verification mechanism.

---

## 3. Host System Installation Setup

### Step 1: Initialize Host Infrastructure Dependencies
Execute the following native package configuration scripts directly on the host OS platform:
bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib redis-server nodejs npm python3-venv python3-pip nginx

# Install Qdrant vector store locally via official script
curl -L https://github.com | tar -xz
sudo mv qdrant /usr/local/bin/


### Step 2: Establish Python Backend Context
Configure dependencies cleanly within an isolated virtual environment:
```bash
cd apps/api
python3 -m venv venv
source venv/bin/activate

cat << 'EOF' > requirements.txt
fastapi
uvicorn[standard]
sqlmodel
asyncpg
alembic
dramatiq[redis]
redis
pyjwt[crypto]
passlib[bcrypt]
langgraph
qdrant-client
EOF

pip install --upgrade pip
pip install -r requirements.txt


### Step 3: Configure Frontend Engine
Initialize packages inside the web interface context folder:
bash
cd ../web
npm init -y
npm install next react react-dom typescript @types/react @types/node
npm install @hey-api/openapi-ts --save-dev


---

## 4. Production Service Deployment Specs

### Qdrant Vector Daemon (`deployment/systemd/qdrant.service`)
ini
[Unit]
Description=Qdrant Local Vector Search Engine
After=network.target

[Service]
User=nathan
ExecStart=/usr/local/bin/qdrant
Restart=always

[Install]
WantedBy=multi-user.target


### FastAPI Web Server (`deployment/systemd/fastapi.service`)
ini
[Unit]
Description=FastAPI Main Application Process Gateway
After=network.target postgresql.service redis.service qdrant.service

[Service]
User=nathan
WorkingDirectory=/home/nathan/my-application/apps/api
ExecStart=/home/nathan/my-application/apps/api/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target


### Dramatiq Worker Daemon (`deployment/systemd/worker.service`)
ini
[Unit]
Description=Dramatiq Asynchronous System Task Queue Worker
After=network.target redis.service

[Service]
User=nathan
WorkingDirectory=/home/nathan/my-application/apps/api
ExecStart=/home/nathan/my-application/apps/api/venv/bin/dramatiq app.tasks.main
Restart=always

[Install]
WantedBy=multi-user.target


### Next.js Production Engine (`deployment/systemd/nextjs.service`)
ini
[Unit]
Description=Next.js Web Frontend Server Node Process
After=network.target

[Service]
User=nathan
WorkingDirectory=/home/nathan/my-application/apps/web
ExecStart=/usr/bin/npm run start
Restart=always

[Install]
WantedBy=multi-user.target


### NGINX Gateway Configuration (`deployment/nginx.conf`)
nginx
server {
    listen 80;
    server_name my-application.local;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    location /api/ {
        proxy_pass http://127.0.0;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

## 5. AI Engineering Rules & Maintenance Standards

This section contains strict rules that all AI coding agents must follow during feature implementation, debugging, and system maintenance. 

### A. The "Anti-Drift" Code Placement Rules
To maintain clear boundaries across the monorepo, code modifications must adhere to these strict folder rules. Never allow the AI to violate these boundaries:
*   **API Routes (`app/routes/`)** are strictly for HTTP request validation, status codes, and routing. They must never directly run SQL queries or contact external services. They pass clean payloads to `app/tasks/` or simple CRUD operations to the DB.
*   **Core Integrations (`app/integrations/`)** must remain 100% pure Python and deterministic. They do not know about AI agents, prompts, or Next.js cookies. They accept strictly typed python inputs and return strictly typed python structures.
*   **AI Agents (`app/ai/agents/`)** must be written using pure stateful LangGraph structures. All external actions performed by an agent (e.g., pulling data from SAP, sending an alert email) must be executed by invoking a registered tool inside `app/ai/tools/`, which imports the corresponding client from `app/integrations/`.

### B. Naming Conventions & Type Enforcement
To minimize hallucinations and semantic confusion, use rigid naming structures across components:
*   **Database Tables (`app/models/`):** Must use the singular noun form (e.g., `User`, `SalesOrder`). Every model class utilizing `table=True` must explicitly contain an indexed, auto-generating UUID primary key named `id`.
*   **Asynchronous Tasks (`app/tasks/`):** File names must describe the execution context (e.g., `sap_sync.py`, `embedding_generator.py`). Every background function exposed as a worker job must be decorated with `@dramatiq.actor` and use the `_task` suffix (e.g., `def process_sap_order_task(order_id: uuid.UUID):`).
*   **Event Payloads (`app/events/`):** Must use the past-tense passive voice naming style (e.g., `OrderSubmittedEvent`, `InventoryCheckedEvent`) to represent an unchangeable history log entry.

### C. Change Management & Migration Safety Protocol
When updating schemas or modifying API layers, the AI must follow this defensive upgrade checklist to prevent breaking runtime environments:
1.  **Contract-First Updates:** When modifying an endpoint structure, update the `SQLModel` definition inside `app/models/` first.
2.  **Schema Tracking:** Immediately execute `alembic revision --autogenerate -m "description"` inside `apps/api/` to lock down the database migration state before any execution code is altered.
3.  **Frontend Sync:** Re-run `npm run generate-client` inside `apps/web/` immediately after updating backend routes to compile the matching TypeScript files for Next.js. Never hand-code overlapping interface definitions on the frontend.
4.  **Graceful Degradation:** All external network operations inside the integration block must be wrapped inside structured `try/except` exceptions, emitting a standard payload back to the broker, ensuring a failure in an external system like SAP does not crash the core FastAPI or Dramatiq process loop.

### D. Agent Prompt Engineering Standards (`app/shared/`)
*   Never bake raw prompt strings directly into python execution files.
*   All complex agent system instructions, structural system roles, and template context formats must reside in `app/shared/prompts/` as plain text or YAML targets. This ensures prompts can be version-controlled, tested, and fine-tuned independently of the backend logic.

### ⚠️ STRICT ENGINEERING RULE: INSTALLER SYNC & COMPLIANCE BOUNDARY
*   **Source of Truth:** `apps/api/app/setup.py` is the code-managed, absolute master source of truth for machine provisioning — covering both core host utilities (apt-managed system runtimes such as python3, nodejs/npm, postgresql, redis-server, and nginx) and python packages. All dependency validation, environment parsing, and host orchestration (apt system package installs, pip/npm installs, OpenAPI client generation, alembic migrations, systemd unit linking, and `/etc/labish/*.env` handling) must flow through this bootstrapper — never through ad-hoc shell snippets or undocumented manual steps.
*   **Mandatory Sync:** Any future modification to package metadata (`apps/api/pyproject.toml`, `apps/web/package.json`), environment keys (`apps/api/app/core/config.py`), or orchestration files (`deployment/*`) **must** include an evaluation of `apps/api/app/setup.py` and a matching update within the same development cycle. A change is not complete until the bootstrapper reflects it.
*   **Drift Prevention:** If a reviewed change touches any of the files above without touching `setup.py`, the author must explicitly state in the change description why no bootstrapper update was required. Silent divergence between the provisioning engine and the real system layout is a compliance violation.


<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
