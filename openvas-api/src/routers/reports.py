from xml.etree.ElementTree import Element

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import Response
from gvm.protocols.gmp import Gmp
from lxml import etree
from pydantic import BaseModel, Field

from gmp import GVM_ERRORS, gmp_session

router = APIRouter(tags=["reports"])

_REPORT_PATH = Path(description="GVM report UUID")
_NOT_FOUND = {404: {"description": "Report not found"}}
_ERRORS = {**_NOT_FOUND, **GVM_ERRORS}
_HOST_QUERY = Query(None, description="Filter results to a specific host IP address")


# ---------- shared helper ----------

def _fetch_report(gmp: Gmp, report_id: str) -> Element:
    response = gmp.get_report(report_id=report_id, details=True)
    r = response.find("report")
    if r is None:
        raise HTTPException(404, detail=f"Report {report_id} not found")
    return r


# ---------- models ----------

class Report(BaseModel):
    id: str = Field(description="GVM report UUID")
    task_id: str = Field(description="UUID of the task that generated this report")
    timestamp: str = Field(description="ISO 8601 timestamp of when the scan started")
    severity: str = Field(description="Highest CVSS score found in this report")
    hosts_count: int = Field(description="Number of hosts included in the report")


class ReportHost(BaseModel):
    ip: str = Field(description="IP address of the scanned host")
    start: str = Field(description="Scan start time for this host")
    end: str = Field(description="Scan end time for this host")
    os: str = Field(description="Detected operating system")
    result_count: int = Field(description="Total number of results for this host")
    port_count: int = Field(description="Number of open ports found")


class Port(BaseModel):
    host: str = Field(description="IP address of the host with this open port")
    port: str = Field(description="Port number and protocol, e.g. `443/tcp`")
    severity: str = Field(description="CVSS score associated with this port")
    threat: str = Field(description="Threat level, e.g. `Log`, `Low`, `Medium`, `High`")


class App(BaseModel):
    host: str = Field(description="IP address of the host running this application")
    name: str = Field(description="Detected application name")
    severity: str = Field(description="Highest CVSS score associated with this application")


class OperatingSystem(BaseModel):
    name: str = Field(description="Operating system name or CPE")
    hosts: int = Field(description="Number of hosts running this OS")
    severity: str = Field(description="Highest CVSS score associated with this OS")


class CVE(BaseModel):
    host: str = Field(description="IP address of the affected host")
    name: str = Field(description="CVE identifier, e.g. `CVE-2021-44228`")
    severity: str = Field(description="CVSS score of this CVE")


class ClosedCVE(BaseModel):
    host: str = Field(description="IP address of the host where the CVE was resolved")
    name: str = Field(description="CVE identifier")
    severity: str = Field(description="CVSS score of the resolved CVE")


class TLSCertificate(BaseModel):
    host: str = Field(description="IP address of the host serving this certificate")
    port: str = Field(description="Port on which the certificate was observed")
    issuer: str = Field(description="Certificate issuer distinguished name")
    serial: str = Field(description="Certificate serial number")
    activation_time: str = Field(description="Certificate validity start (ISO 8601)")
    expiration_time: str = Field(description="Certificate expiry (ISO 8601)")


class ErrorMessage(BaseModel):
    host: str = Field(description="IP address of the host that produced the error")
    port: str = Field(description="Port associated with the error")
    description: str = Field(description="Error message text")
    nvt_name: str = Field(description="Name of the NVT that reported the error")


class UserTag(BaseModel):
    id: str = Field(description="GVM tag UUID")
    name: str = Field(description="Tag name")
    value: str = Field(description="Tag value")
    comment: str = Field(description="Tag comment")


# ---------- endpoints ----------

@router.get(
    "/reports",
    response_model=list[Report],
    summary="List scan reports",
    response_description="Summary of all reports available in GVM",
    responses=GVM_ERRORS,
)
def list_reports() -> list[Report]:
    """Return a summary list of all scan reports stored in GVM.

    Each report corresponds to a single run of a scan task. A task that has
    been run multiple times will produce multiple reports. Use
    `GET /reports/{report_id}` to retrieve the full details of a specific
    report.
    """
    with gmp_session() as gmp:
        response = gmp.get_reports()

    reports = []
    for r in response.findall("report"):
        task = r.find("task")
        reports.append(Report(
            id=r.get("id", ""),
            task_id=task.get("id", "") if task is not None else "",
            timestamp=r.findtext("timestamp", ""),
            severity=r.findtext(".//severity/full", "-"),
            hosts_count=int(r.findtext(".//hosts/count", "0") or 0),
        ))
    return reports


@router.get(
    "/reports/{report_id}",
    response_model=Report,
    summary="Get a scan report",
    response_description="Full details of the requested report",
    responses=_ERRORS,
)
def get_report(report_id: str = _REPORT_PATH) -> Report:
    """Return the full details of a single scan report.

    For individual vulnerability findings use `GET /results?report_id=<id>`.
    For open ports, applications, CVEs, and other sections use the
    sub-resource endpoints under `/reports/{report_id}/`.
    """
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    task = r.find("task")
    return Report(
        id=r.get("id", ""),
        task_id=task.get("id", "") if task is not None else "",
        timestamp=r.findtext("timestamp", ""),
        severity=r.findtext(".//severity/full", "-"),
        hosts_count=int(r.findtext(".//hosts/count", "0") or 0),
    )


# Built-in "XML" report format -- the OpenVAS XML that DefectDojo's "OpenVAS Parser" ingests.
_XML_REPORT_FORMAT_ID = "a994b278-1f62-11e1-96ac-406186ea4fc5"


@router.get(
    "/reports/{report_id}/xml",
    summary="Download a report as OpenVAS XML",
    response_description="The report in GVM's built-in XML report format",
    responses={**_ERRORS, 200: {"content": {"application/xml": {}}}},
)
def get_report_xml(report_id: str = _REPORT_PATH) -> Response:
    """Return the raw OpenVAS XML report (GVM's built-in 'XML' report format).

    Intended for tools that ingest the OpenVAS XML report directly -- e.g.
    DefectDojo's 'OpenVAS Parser' via `POST /api/v2/reimport-scan/`. The inner
    `<report>` element is returned (unwrapped from the GMP response envelope).
    """
    with gmp_session() as gmp:
        response = gmp.get_report(
            report_id=report_id,
            report_format_id=_XML_REPORT_FORMAT_ID,
            ignore_pagination=True,
            details=True,
        )
    inner = response.find("report")
    if inner is None:
        raise HTTPException(404, detail=f"Report {report_id} not found")
    return Response(content=etree.tostring(inner), media_type="application/xml")


@router.get(
    "/reports/{report_id}/hosts",
    response_model=list[ReportHost],
    summary="List hosts in a report",
    response_description="All hosts scanned in this report",
    responses=_ERRORS,
)
def get_report_hosts(
    report_id: str = _REPORT_PATH,
    host: str | None = _HOST_QUERY,
) -> list[ReportHost]:
    """Return all hosts that were scanned as part of this report."""
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    return [
        ReportHost(
            ip=h.findtext("ip", ""),
            start=h.findtext("start", ""),
            end=h.findtext("end", ""),
            os=h.findtext("detail[name='best_os_txt']/value", "-"),
            result_count=int(h.findtext("result_count/page", "0") or 0),
            port_count=int(h.findtext("port_count/page", "0") or 0),
        )
        for h in r.findall("host")
        if host is None or h.findtext("ip", "") == host
    ]


@router.get(
    "/reports/{report_id}/ports",
    response_model=list[Port],
    summary="List open ports in a report",
    response_description="All open ports discovered during the scan",
    responses=_ERRORS,
)
def get_report_ports(
    report_id: str = _REPORT_PATH,
    host: str | None = _HOST_QUERY,
) -> list[Port]:
    """Return all open ports discovered in this report.

    Each entry identifies the host, port/protocol, and the associated threat
    level. Ports are sourced from the `<ports>` section of the report XML,
    which is separate from the vulnerability results.
    """
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    return [
        Port(
            host=port.findtext("host", ""),
            port=port.text.strip() if port.text else "",
            severity=port.findtext("severity", "-"),
            threat=port.findtext("threat", "-"),
        )
        for port in r.findall(".//ports/port")
        if host is None or port.findtext("host", "") == host
    ]


@router.get(
    "/reports/{report_id}/apps",
    response_model=list[App],
    summary="List applications in a report",
    response_description="All applications detected during the scan",
    responses=_ERRORS,
)
def get_report_apps(
    report_id: str = _REPORT_PATH,
    host: str | None = _HOST_QUERY,
) -> list[App]:
    """Return all applications detected across scanned hosts in this report."""
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    return [
        App(
            host=app.findtext("host/ip", ""),
            name=app.findtext("app", ""),
            severity=app.findtext("severity", "-"),
        )
        for app in r.findall(".//apps/app")
        if host is None or app.findtext("host/ip", "") == host
    ]


@router.get(
    "/reports/{report_id}/os",
    response_model=list[OperatingSystem],
    summary="List operating systems in a report",
    response_description="All operating systems detected during the scan",
    responses=_ERRORS,
)
def get_report_os(report_id: str = _REPORT_PATH) -> list[OperatingSystem]:
    """Return all operating systems detected across scanned hosts in this report."""
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    return [
        OperatingSystem(
            name=os.findtext("name", ""),
            hosts=int(os.findtext("host_count", "0") or 0),
            severity=os.findtext("severity", "-"),
        )
        for os in r.findall(".//os/os")
    ]


@router.get(
    "/reports/{report_id}/cves",
    response_model=list[CVE],
    summary="List CVEs in a report",
    response_description="All CVEs identified during the scan",
    responses=_ERRORS,
)
def get_report_cves(
    report_id: str = _REPORT_PATH,
    host: str | None = _HOST_QUERY,
) -> list[CVE]:
    """Return all CVEs identified across scanned hosts in this report."""
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    return [
        CVE(
            host=cve.findtext("host/ip", ""),
            name=cve.findtext("cve", ""),
            severity=cve.findtext("severity", "-"),
        )
        for cve in r.findall(".//cves/cve")
        if host is None or cve.findtext("host/ip", "") == host
    ]


@router.get(
    "/reports/{report_id}/closed-cves",
    response_model=list[ClosedCVE],
    summary="List closed CVEs in a report",
    response_description="All CVEs that have been resolved on scanned hosts",
    responses=_ERRORS,
)
def get_report_closed_cves(
    report_id: str = _REPORT_PATH,
    host: str | None = _HOST_QUERY,
) -> list[ClosedCVE]:
    """Return all CVEs that were previously identified but are now resolved."""
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    return [
        ClosedCVE(
            host=cve.findtext("host/ip", ""),
            name=cve.findtext("cve", ""),
            severity=cve.findtext("severity", "-"),
        )
        for cve in r.findall(".//closed_cves/closed_cve")
        if host is None or cve.findtext("host/ip", "") == host
    ]


@router.get(
    "/reports/{report_id}/tls-certificates",
    response_model=list[TLSCertificate],
    summary="List TLS certificates in a report",
    response_description="All TLS certificates observed during the scan",
    responses=_ERRORS,
)
def get_report_tls_certificates(
    report_id: str = _REPORT_PATH,
    host: str | None = _HOST_QUERY,
) -> list[TLSCertificate]:
    """Return all TLS certificates observed on scanned hosts in this report."""
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    return [
        TLSCertificate(
            host=cert.findtext("host/ip", ""),
            port=cert.findtext("port", ""),
            issuer=cert.findtext("issuer", ""),
            serial=cert.findtext("serial", ""),
            activation_time=cert.findtext("activation_time", ""),
            expiration_time=cert.findtext("expiration_time", ""),
        )
        for cert in r.findall(".//ssl_certs/ssl_cert")
        if host is None or cert.findtext("host/ip", "") == host
    ]


@router.get(
    "/reports/{report_id}/errors",
    response_model=list[ErrorMessage],
    summary="List scan errors in a report",
    response_description="All errors encountered during the scan",
    responses=_ERRORS,
)
def get_report_errors(
    report_id: str = _REPORT_PATH,
    host: str | None = _HOST_QUERY,
) -> list[ErrorMessage]:
    """Return all errors encountered while scanning hosts in this report.

    Errors typically indicate unreachable ports, authentication failures,
    or NVT execution problems and do not represent vulnerabilities.
    """
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    return [
        ErrorMessage(
            host=err.findtext("host/ip", ""),
            port=err.findtext("port", ""),
            description=err.findtext("description", ""),
            nvt_name=err.findtext("nvt/name", ""),
        )
        for err in r.findall(".//errors/error")
        if host is None or err.findtext("host/ip", "") == host
    ]


@router.get(
    "/reports/{report_id}/tags",
    response_model=list[UserTag],
    summary="List user tags on a report",
    response_description="All tags applied to this report",
    responses=_ERRORS,
)
def get_report_tags(report_id: str = _REPORT_PATH) -> list[UserTag]:
    """Return all user-defined tags applied to this report."""
    with gmp_session() as gmp:
        r = _fetch_report(gmp, report_id)

    return [
        UserTag(
            id=tag.get("id", ""),
            name=tag.findtext("name", ""),
            value=tag.findtext("value", ""),
            comment=tag.findtext("comment", ""),
        )
        for tag in r.findall(".//user_tags/tag")
    ]
