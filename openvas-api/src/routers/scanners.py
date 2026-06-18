from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from gmp import GVM_ERRORS, gmp_session

router = APIRouter(tags=["scanners"])

_NOT_FOUND = {404: {"description": "Scanner not found"}}
_ERRORS = {**_NOT_FOUND, **GVM_ERRORS}


class Scanner(BaseModel):
    id: str = Field(description="GVM scanner UUID")
    name: str = Field(description="Display name of the scanner")


@router.get(
    "/scanners",
    response_model=list[Scanner],
    summary="List scanners",
    response_description="All scanners available in GVM",
    responses=GVM_ERRORS,
)
def list_scanners() -> list[Scanner]:
    """Return all scanners defined in GVM.

    The `id` of a scanner is passed as `scanner_id` when creating a scan
    via `POST /scans`.
    """
    with gmp_session() as gmp:
        response = gmp.get_scanners()

    return [
        Scanner(
            id=s.get("id", ""),
            name=s.findtext("name", ""),
        )
        for s in response.findall("scanner")
    ]


@router.get(
    "/scanners/{scanner_id}",
    response_model=Scanner,
    summary="Get a scanner",
    response_description="Details of the requested scanner",
    responses=_ERRORS,
)
def get_scanner(
    scanner_id: str = Path(description="GVM scanner UUID"),
) -> Scanner:
    """Return a single scanner by UUID."""
    with gmp_session() as gmp:
        response = gmp.get_scanner(scanner_id=scanner_id)

    s = response.find("scanner")
    if s is None:
        raise HTTPException(404, detail=f"Scanner {scanner_id} not found")

    return Scanner(
        id=s.get("id", ""),
        name=s.findtext("name", ""),
    )
