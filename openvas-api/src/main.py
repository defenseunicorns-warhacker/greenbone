import uvicorn
from fastapi import FastAPI

from routers import hosts, reports, results, scans, targets

app = FastAPI(
    title="OpenVAS API",
    description=(
        "REST API for interacting with Greenbone Vulnerability Manager (GVM) "
        "via the GMP Unix socket. All endpoints require the `gvmd` socket to "
        "be mounted at `GVM_SOCKET_PATH` (default `/run/gvmd/gvmd.sock`)."
    ),
    version="0.1.0",
)

app.include_router(hosts.router)
app.include_router(targets.router)
app.include_router(scans.router)
app.include_router(reports.router)
app.include_router(results.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
