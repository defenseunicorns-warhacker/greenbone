from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from config import DEFAULT_PORT_LIST_ID
from gmp import GVM_ERRORS, gmp_session

router = APIRouter(tags=["targets"])


class CreateTargetRequest(BaseModel):
    name: str = Field(description="Display name for the target")
    hosts: str = Field(
        description="Comma-separated IP addresses or CIDR ranges, e.g. `192.168.1.0/24,10.0.0.1`"
    )
    port_list_id: str = Field(
        default=DEFAULT_PORT_LIST_ID,
        description="GVM port list UUID. Defaults to *All IANA assigned TCP* (`33d0cd82-…`).",
    )


class Target(BaseModel):
    id: str = Field(description="GVM target UUID")
    name: str = Field(description="Display name for the target")
    hosts: str = Field(description="Hosts/CIDRs included in this target")


@router.get(
    "/targets",
    response_model=list[Target],
    summary="List scan targets",
    response_description="All targets configured in GVM",
    responses=GVM_ERRORS,
)
def list_targets() -> list[Target]:
    """Return all scan targets defined in GVM.

    Targets represent the hosts or networks that tasks scan against. Use
    `POST /targets` to create a new one before launching a scan.
    """
    with gmp_session() as gmp:
        response = gmp.get_targets()

    return [
        Target(
            id=t.get("id", ""),
            name=t.findtext("name", ""),
            hosts=t.findtext("hosts", ""),
        )
        for t in response.findall("target")
    ]


@router.post(
    "/targets",
    response_model=Target,
    status_code=201,
    summary="Create a scan target",
    response_description="The newly created target",
    responses={
        400: {"description": "hosts field is empty"},
        **GVM_ERRORS,
    },
)
def create_target(body: CreateTargetRequest) -> Target:
    """Create a new scan target in GVM.

    The `hosts` field accepts any combination of individual IPs, CIDR ranges,
    and IP ranges (e.g. `10.0.0.1-10.0.0.50`), separated by commas.

    The returned `id` is used as `target_id` when creating a scan via
    `POST /scans`.
    """
    hosts = [h.strip() for h in body.hosts.split(",") if h.strip()]
    if not hosts:
        raise HTTPException(400, detail="hosts must not be empty")

    with gmp_session() as gmp:
        response = gmp.create_target(
            name=body.name,
            hosts=hosts,
            port_list_id=body.port_list_id,
        )

    target_id = response.get("id")
    if not target_id:
        raise HTTPException(502, detail="GVM did not return a target ID")

    return Target(id=target_id, name=body.name, hosts=body.hosts)
