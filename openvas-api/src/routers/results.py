from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from gmp import GVM_ERRORS, gmp_session

router = APIRouter(tags=["results"])


class Result(BaseModel):
    id: str = Field(description="GVM result UUID")
    name: str = Field(description="Vulnerability or finding name")
    host: str = Field(description="IP address of the affected host")
    port: str = Field(description="Affected port and protocol, e.g. `443/tcp`")
    severity: str = Field(description="CVSS score of this finding")
    description: str = Field(description="Full description of the finding")


@router.get(
    "/results",
    response_model=list[Result],
    summary="List scan results",
    response_description="Individual vulnerability findings, optionally filtered",
    responses=GVM_ERRORS,
)
def list_results(
    task_id: str | None = Query(None, description="Return only results from this task UUID"),
    host: str | None = Query(None, description="Return only results for this host IP"),
    min_severity: float | None = Query(
        None,
        ge=0.0,
        le=10.0,
        description="Minimum CVSS score to include",
    ),
    rows: int = Query(-1, ge=-1, description="Maximum number of results to return (-1 for all)"),
    min_qod: int = Query(0, ge=0, le=100, description="Minimum Quality of Detection percentage"),
) -> list[Result]:
    """Return individual vulnerability findings across all completed scans.

    All query parameters are optional and combinable. For example, to list
    all critical findings (`min_severity=9.0`) on a specific host, provide
    both `host` and `min_severity`.
    """
    filter_parts = [f"rows={rows}", f"min_qod={min_qod}"]
    if task_id:
        filter_parts.append(f"task_id={task_id}")
    if host:
        filter_parts.append(f"host={host}")
    if min_severity is not None:
        filter_parts.append(f"severity>{min_severity - 0.001:.3f}")

    with gmp_session() as gmp:
        response = gmp.get_results(filter_string=" ".join(filter_parts))

    return [
        Result(
            id=r.get("id", ""),
            name=r.findtext("name", ""),
            host=r.findtext("host", ""),
            port=r.findtext("port", ""),
            severity=r.findtext("severity", "-"),
            description=r.findtext("description", ""),
        )
        for r in response.findall("result")
    ]
