from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from gmp import GVM_ERRORS, gmp_session

router = APIRouter(tags=["scan configs"])

_NOT_FOUND = {404: {"description": "Scan config not found"}}
_ERRORS = {**_NOT_FOUND, **GVM_ERRORS}


class ScanConfig(BaseModel):
    id: str = Field(description="GVM scan config UUID")
    name: str = Field(description="Display name of the scan config")


@router.get(
    "/scan-configs",
    response_model=list[ScanConfig],
    summary="List scan configs",
    response_description="All scan configs available in GVM",
    responses=GVM_ERRORS,
)
def list_scan_configs() -> list[ScanConfig]:
    """Return all scan configs defined in GVM.

    The `id` of a scan config is passed as `config_id` when creating a scan
    via `POST /scans`.
    """
    with gmp_session() as gmp:
        response = gmp.get_scan_configs()

    return [
        ScanConfig(
            id=sc.get("id", ""),
            name=sc.findtext("name", ""),
        )
        for sc in response.findall("config")
    ]


@router.get(
    "/scan-configs/{config_id}",
    response_model=ScanConfig,
    summary="Get a scan config",
    response_description="Details of the requested scan config",
    responses=_ERRORS,
)
def get_scan_config(
    config_id: str = Path(description="GVM scan config UUID"),
) -> ScanConfig:
    """Return a single scan config by UUID."""
    with gmp_session() as gmp:
        response = gmp.get_scan_config(config_id=config_id)

    sc = response.find("config")
    if sc is None:
        raise HTTPException(404, detail=f"Scan config {config_id} not found")

    return ScanConfig(
        id=sc.get("id", ""),
        name=sc.findtext("name", ""),
    )
