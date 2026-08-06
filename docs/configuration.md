# Greenbone Community Edition Configuration

This package deploys the official Greenbone Community container stack through a local Helm chart.
Use Helm values to tune storage, resources, scanner egress, and image references.

## Storage

Greenbone stores feeds, PostgreSQL data, scanner data, generated certificates, and web assets in
PVCs owned by the `greenbone-community` StatefulSet.

```yaml
persistence:
  accessModes:
    - ReadWriteOnce
  storageClass: ""
  volumes:
    psqlData:
      size: 20Gi
    vtData:
      size: 20Gi
```

The default chart topology runs one replica. Keep `ReadWriteOnce` unless you change the chart
architecture and validate a multi-node deployment.

## Resources

Set resources per long-running service:

```yaml
resources:
  gvmd:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      memory: 4Gi
  ospdOpenvas:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      memory: 4Gi
```

Greenbone feed initialization and scan execution can be resource intensive. Increase `gvmd`,
`ospdOpenvas`, and `openvasd` resources for larger scan targets.

## Network

The UDS integration exposes Greenbone Security Assistant at:

```text
https://greenbone.<UDS_DOMAIN>
```

The package does not allow broad scanner egress by default. Vulnerability scanning requires
connections to user-selected scan targets, so add site-specific UDS network policy overrides for the
target ranges and ports you intend to scan.

Enable broad scanner egress only for controlled development environments:

```yaml
network:
  allowScannerEgress: false
```

## Authentication

Greenbone Community Edition uses its built-in application authentication. This package does not
create a Keycloak client because the upstream Community container stack does not provide a
documented OIDC or SAML integration point for Greenbone Security Assistant.

The gvmd container creates the initial admin account on first boot. Upstream this defaults to the
well-known `admin`/`admin`; this package instead injects credentials from the
`greenbone-community-admin` Secret so the deployment gets a unique, randomly generated password
exposed only inside the cluster. Override the username or supply a fixed password via Helm values:

```yaml
admin:
  user: admin
  password: ""   # empty = generate a random password, preserved across upgrades
```

Read the generated password with:

```bash
kubectl -n greenbone get secret greenbone-community-admin -o jsonpath='{.data.password}' | base64 -d
```

Changing `admin.password` after the first deploy does not rotate the live account (gvmd only
creates the user once). Use Greenbone's `gvmd --user=<name> --new-password=<pw>` workflow to rotate.

## Images

Greenbone publishes Community images in `registry.community.greenbone.net/community`. The upstream
container stack currently uses moving tags such as `stable`, `stable-slim`, and `latest`.

```yaml
imageRegistry: registry.community.greenbone.net/community
images:
  gvmd:
    repository: gvmd
    tag: stable
```

For production-grade reproducibility, replace moving tags with immutable image digests or a
validated internal mirror policy before release.

## Scheduled DefectDojo upload

The chart can run the full scan-and-report pipeline on a schedule, entirely in-cluster.
When `defectdojo.enabled=true` a CronJob (`greenbone-community-defectdojo`) runs the same
end-to-end flow as `uds run test:api-scan` + `scripts/upload-to-defectdojo.py`: it drives
the `openvas-api` to create a target, run a *Full and fast* scan, waits for completion,
fetches the OpenVAS XML report, and POSTs it to DefectDojo's `reimport-scan` endpoint
(auto-creating the product/engagement). It uses only `curl` + a POSIX shell — no Python and
no custom image.

DefectDojo is intentionally **not** part of this bundle. Point `defectdojo.url` at a
reachable instance and provide an API v2 token:

```yaml
defectdojo:
  enabled: true
  schedule: "0 2 * * *"          # daily at 02:00 (cluster timezone)
  url: https://defectdojo.uds.dev
  product: Greenbone
  engagement: OpenVAS Scan
  verifyTls: false               # *.uds.dev uses a dev CA
  token: ""                      # creates a Secret; or use existingSecret/tokenKey
  scan:
    targetHosts: "127.0.0.1"     # set to real targets for a useful scan
```

Provide the token either inline (`defectdojo.token`, which creates a Secret) or by
referencing a Secret you manage:

```yaml
defectdojo:
  existingSecret: my-defectdojo-token
  tokenKey: token
```

The CronJob pod needs egress to DefectDojo; this is allowed via a UDS network policy scoped
to the upload pod (`network.defectdojoUpload.allowEgress`, on by default in the config chart).

Trigger an off-schedule run and follow it (requires `kubectl`):

```bash
uds run defectdojo:run        # creates a Job from the CronJob and streams logs
uds run defectdojo:logs       # logs from the most recent upload run
```

## Upstream Documentation

Read the upstream documentation for application behavior and lifecycle operations:

- [Greenbone Community Containers](https://greenbone.github.io/docs/latest/22.4/container/)
- [Greenbone Community Edition Documentation](https://greenbone.github.io/docs/latest/)
