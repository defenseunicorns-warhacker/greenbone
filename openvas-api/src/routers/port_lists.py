from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from gmp import GVM_ERRORS, gmp_session

router = APIRouter(tags=["port lists"])

_NOT_FOUND = {404: {"description": "Port list not found"}}
_ERRORS = {**_NOT_FOUND, **GVM_ERRORS}


class PortList(BaseModel):
    id: str = Field(description="GVM port list UUID")
    name: str = Field(description="Display name of the port list")
    port_count: int = Field(description="Total number of ports in the list")


@router.get(
    "/port-lists",
    response_model=list[PortList],
    summary="List port lists",
    response_description="All port lists available in GVM",
    responses=GVM_ERRORS,
)
def list_port_lists() -> list[PortList]:
    """Return all port lists defined in GVM.

    The `id` of a port list is passed as `port_list_id` when creating a target
    via `POST /targets`.
    """
    with gmp_session() as gmp:
        response = gmp.get_port_lists()

    return [
        PortList(
            id=pl.get("id", ""),
            name=pl.findtext("name", ""),
            port_count=int(pl.findtext("port_count/all", "0") or 0),
        )
        for pl in response.findall("port_list")
    ]


@router.get(
    "/port-lists/{port_list_id}",
    response_model=PortList,
    summary="Get a port list",
    response_description="Details of the requested port list",
    responses=_ERRORS,
)
def get_port_list(
    port_list_id: str = Path(description="GVM port list UUID"),
) -> PortList:
    """Return a single port list by UUID."""
    with gmp_session() as gmp:
        response = gmp.get_port_list(port_list_id=port_list_id)

    pl = response.find("port_list")
    if pl is None:
        raise HTTPException(404, detail=f"Port list {port_list_id} not found")

    return PortList(
        id=pl.get("id", ""),
        name=pl.findtext("name", ""),
        port_count=int(pl.findtext("port_count/all", "0") or 0),
    )
