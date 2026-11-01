# Software Design & Architecture: Centralized BIOS & Firmware Orchestration System
This project automates the preparation phase of bare-metal hardware systems by orchestrating BIOS firmware
updates and configurations using a centralized web dashboard; dedicated repositories are managed and maintained and
distributed from the server.

## Infrastructure
Uses a centralized server-client architecture. Server manages state and orchestration. Headless clients request and
receive responses (payloads, state, etc).

- Server: bare-metal running Windows Server 2022
- Services: DHCP, DNS, WDS, WSL running Ubuntu
- Containerization (within WSL): Docker

## Technology Stack
- Reverse Proxy & Static File Server: Caddy
- Frontend (single page application): Python (FastAPI), Jinja2, HTMX. Server-side rendered HTML templates/pages using
Jinja2. Dynamic handlers/updates (button clicks, etc) using HTMX.
- Backend (api): Python, FastAPI, Uvicorn
- Database: PostgreSQL
- Client-side: PowerShell; WinPE (PXE boot via WDS); non-persistent (RAM only)

## Workflow
State-driven pipeline. Clients are non-persistent (no local state). Server-side state machine and database integration
are the source of truth.

- Orchestration (server-side): Technician assigns a task to a client on the dashboard. Server receives the
request, updates the client's state in the database, returns a response. State requests update the client's state in the
database.
- Execution (client-side): Clients receives the response from the server. Executes the action. Reports new state to the
server.

Use case 1: Client needs a BIOS firmware update and configuration
1. Client connects and boots WinPE via PXE boot. PowerShell startup script executes.
2. Checks-in and polling for instructions. (GET /api/v1/clients/{serial-tag}/action)
3. Phase 1 (Firmware Check/Flash): Task assigned the 'full payload task' to a client. Submits the request. The server
receives the request, queries for the client's serial tag, updates the client's state in the database, responds back a
firmware payload path (served by Caddy). Client reports an 'in-progress' state to the server. Client downloads and
flashes the firmware. Reboots.
4. Phase 2 (BIOS Configuration): Client re-enters WinPE, checks firmware version, checks-in with the server, send over
its current BIOS firmware version. Server receives, updates the client's state in the database, and responds back a BIOS
configuration payload (served by Caddy). Client reports an 'in-progress' state to the server. Client downloads and
executes the BIOS configuration. Client reports a 'completed' state to the server. Reboots.

## Bottlenecks -> Mitigations
- Concurrent database read/writes assisted by asynchronous database driver (asyncpg) to limit write-locks and
continuous connection hits.
- Payloads are served by Caddy, redirecting the requests to a dedicated route. Includes BIOS firmware binaries and BIOS
configurations. Limits API traffic to the backend (FastAPI).
- Network congestion can be reduced by using a faster uplink to the server (1-Gbps vs 10-GBps)
- PXE boot storms can be reduced and desaturated by staggering client power-ons

## Air-gapped Deployment
Preparing and packaging development environment for isolated, air-gapped production environment.

1. Build & tag Docker images, tagging the release version (e.g., 'backend:v0.1.0')
2. Tarball images ('docker save')
3. Transfer packaged source code
4. Import & extract tarball
5. Load & run images ('docker load')
