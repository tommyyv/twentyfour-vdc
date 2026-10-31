# Software & Design Document: Centralized BIOS & Firmware Orchestration System

## 1. Executive Summary
This system automates the pre-deployment preparation of bare-metal servers destined for an air-gapped environment. It orchestrates bulk BIOS firmware updates and configuration via a centralized web dashboard. The architecture prioritizes simplicity, high concurrency (scaling to 80+ clients), and long-term maintainability by utilizing industry-standard, "boring" technologies.

## 2. Architecture & Technology Stack
The system uses a centralized server-client model. The server manages state and orchestration; the clients are "dumb" execution environments.

* **Server Host:** Single Windows Server 2022 (NVMe storage required for I/O).
* **Network:** 1Gbps RJ45 switch. Native Windows DHCP/DNS.
* **Containerization:** Docker & Docker Compose.
* **Reverse Proxy & Static File Server:** **Caddy**. Routes API traffic to the backend and serves large firmware payloads directly to clients.
* **Backend API:** Python, **FastAPI**, Uvicorn.
* **Database:** **PostgreSQL** (Run via Docker). Chosen over SQLite to handle concurrent state writes from 80+ clients without locking issues.
* **Frontend Dashboard:** Python (FastAPI), **Jinja2** (Templating), **HTMX** (Dynamic UI). 100% server-rendered; no Node.js or complex JS build steps.
* **Client Environment:** WinPE (PXE booted via WDS). Non-persistent (RAM-based).
* **Client Scripting:** **PowerShell**. Native to WinPE, used to interact with vendor BIOS tools (Dell, HP, Lenovo).

## 3. Workflow & Server-Side State Machine
Because WinPE is non-persistent, clients do not store local state. The PostgreSQL database is the single source of truth.

1. **PXE Boot:** Client boots WinPE. PowerShell script starts.
2. **Check-in & Polling:** Script enters a polling loop (every 5 seconds), calling `GET /api/clients/{serial}/next-action`.
3. **Phase 1 (Firmware):** Technician assigns a task via Dashboard. Server updates DB to `FW_UPDATING` and returns the firmware payload URL (served by Caddy). Client downloads and flashes firmware. Client reports success. Server updates DB to `REBOOTING_POST_FW`. Client reboots.
4. **Phase 2 (BIOS Config):** Client re-boots WinPE, polls server. Server sees state, returns BIOS config payload. Client executes config. Client reports success. Server updates DB to `COMPLETED`. Client performs final reboot.

## 4. Scalability & Performance Design (80+ Clients)
To ensure the system handles 80 concurrent clients without degradation, the following design constraints are enforced:

* **Database Concurrency:** PostgreSQL with an async driver (`asyncpg`) and a connection pool (size 20) in FastAPI prevents connection exhaustion and write-locks.
* **Payload Offloading:** FastAPI only returns JSON metadata. Large firmware binaries (50MB-200MB) are served directly by **Caddy** via a dedicated `/payloads/` route. This prevents Python from blocking on large file I/O.
* **Network I/O:** NVMe storage on the host ensures Caddy can serve 80 concurrent 100MB downloads without disk queue bottlenecks.
* **PXE Storm Mitigation:** Technicians must stagger client power-ons (e.g., batches of 20) to prevent saturating the WDS TFTP server during the initial WinPE download.

## 5. Frontend Strategy (HTMX + Jinja2)
The dashboard avoids complex frontend frameworks (React/Vue) to ensure long-term maintainability.

* **Server-Side Rendering:** FastAPI renders full HTML pages using Jinja2.
* **Dynamic Updates:** HTMX intercepts button clicks (e.g., "Start Update"), sends an AJAX request, and swaps only the specific HTML table row returned by the server.
* **Result:** Provides a modern Single Page Application (SPA) feel using only Python and HTML. Future maintainers only need to know basic HTML and Python.

## 6. Deployment & Air-Gap Strategy
To transition from the internet-facing dev environment to the isolated prod environment:

1. **Build & Tag:** Docker images are built and strictly tagged in the dev environment (e.g., `backend:v1.2`, not `latest`).
2. **Export:** Images are saved to `.tar` archives (`docker save`).
3. **Transfer:** Archives are physically moved via USB to the air-gapped Windows Server.
4. **Import & Run:** Images are loaded (`docker load`) and started via `docker-compose.yml`. Strict tagging prevents Docker from attempting to pull images from the internet.

## 7. Longevity & Maintainability
* **Hardware Agnosticism:** Vendor-specific BIOS tools (`.exe`, PowerShell modules) are stored in a dedicated WinPE directory. The Python backend only passes the *filename* to the client. Adding new hardware models requires only dropping new files into the WinPE image, not rewriting Python code.
* **Centralized Logging:** PowerShell scripts write verbose logs to RAM and push them to the FastAPI backend upon completion or failure. The dashboard provides a UI to read these logs, turning "Red" status indicators into actionable debugging data.
* **Documentation:** The repository will include `README.md` (Architecture), `DEPLOYMENT.md` (Air-gap transfer steps), and `WINPE_GUIDE.md` (How to update PowerShell scripts/vendor tools).
