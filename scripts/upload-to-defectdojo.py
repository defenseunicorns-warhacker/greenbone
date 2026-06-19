#!/usr/bin/env python3
# Copyright 2024 Defense Unicorns
# SPDX-License-Identifier: AGPL-3.0-or-later OR LicenseRef-Defense-Unicorns-Commercial
"""Reimport an OpenVAS XML report into DefectDojo.

The report file is produced by the `api-scan` test task (`uds run test:api-scan`),
which writes `openvas-report.xml`. DefectDojo is intentionally *not* part of the UDS
bundle, so this upload is a separate, manual step run against a reachable instance.

Unlike the original gvm-script version, this does not talk to gvmd -- the test already
runs the scan and exports the report -- it only POSTs the file to DefectDojo's
reimport-scan endpoint (auto-creating the product/engagement if they don't exist).

Usage:
    DEFECTDOJO_TOKEN=<token> python scripts/upload-to-defectdojo.py [report.xml]

Environment:
    DEFECTDOJO_TOKEN       (required) DefectDojo API v2 token
    DEFECTDOJO_URL           DefectDojo base URL (default: https://defectdojo.uds.dev)
    DEFECTDOJO_PRODUCT       Product name        (default: Greenbone)
    DEFECTDOJO_PRODUCT_TYPE  Product type name   (default: Greenbone) -- the parent grouping
                             DefectDojo creates the product under when auto-creating context
    DEFECTDOJO_ENGAGEMENT    Engagement name     (default: OpenVAS Scan)
    DEFECTDOJO_VERIFY_TLS    "true" to verify TLS (default: false; *.uds.dev uses a dev CA)
"""
import os
import sys

import requests
import urllib3

SCAN_TYPE = "OpenVAS Parser"


def main() -> int:
    token = os.environ.get("DEFECTDOJO_TOKEN")
    if not token:
        print("error: DEFECTDOJO_TOKEN is required", file=sys.stderr)
        return 2

    report_file = sys.argv[1] if len(sys.argv) > 1 else "openvas-report.xml"
    if not os.path.isfile(report_file):
        print(f"error: report file not found: {report_file}", file=sys.stderr)
        print("hint: run `uds run test:api-scan` first to generate it", file=sys.stderr)
        return 2

    base_url = os.environ.get("DEFECTDOJO_URL", "https://defectdojo.uds.dev").rstrip("/")
    verify_tls = os.environ.get("DEFECTDOJO_VERIFY_TLS", "false").lower() == "true"
    if not verify_tls:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    with open(report_file, "rb") as fh:
        xml_bytes = fh.read()

    resp = requests.post(
        f"{base_url}/api/v2/reimport-scan/",
        headers={"Authorization": f"Token {token}"},
        data={
            "scan_type": SCAN_TYPE,
            "product_name": os.environ.get("DEFECTDOJO_PRODUCT", "Greenbone"),
            "product_type_name": os.environ.get("DEFECTDOJO_PRODUCT_TYPE", "Greenbone"),
            "engagement_name": os.environ.get("DEFECTDOJO_ENGAGEMENT", "OpenVAS Scan"),
            "auto_create_context": "true",
            "active": "true",
            "verified": "false",
            "minimum_severity": "Low",
        },
        files={"file": ("openvas.xml", xml_bytes, "text/xml")},
        timeout=120,
        verify=verify_tls,
    )
    print(f"DefectDojo reimport: HTTP {resp.status_code}")
    print(resp.text)
    resp.raise_for_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
