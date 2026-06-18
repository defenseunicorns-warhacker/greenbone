from fastapi import APIRouter
from pydantic import BaseModel, Field

from gmp import GVM_ERRORS, gmp_session

router = APIRouter(tags=["hosts"])


class Host(BaseModel):
    id: str = Field(description="GVM asset UUID")
    ip: str = Field(description="IP address of the host")
    severity: str = Field(description="Highest CVSS severity score observed")
    os: str = Field(description="Best-guess operating system name")


@router.get(
    "/hosts",
    response_model=list[Host],
    summary="List discovered hosts",
    response_description="All hosts present in the GVM asset database",
    responses=GVM_ERRORS,
)
def get_hosts() -> list[Host]:
    """Return every host that GVM has recorded in its asset database.

    Hosts are populated automatically as scans run. An empty list means no
    scans have completed yet, not that the network has no hosts.
    """
    with gmp_session() as gmp:
        response = gmp.get_hosts()

    hosts = []
    for asset in response.findall("asset"):
        os_name = "-"
        for detail in asset.findall(".//detail"):
            if detail.findtext("name") == "best_os_txt":
                os_name = detail.findtext("value", "-")
                break
        hosts.append(Host(
            id=asset.get("id", ""),
            ip=asset.findtext("name", ""),
            severity=asset.findtext(".//severity/value", "-"),
            os=os_name,
        ))
    return hosts
