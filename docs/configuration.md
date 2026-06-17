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

After the first deploy, rotate the default Greenbone admin credentials using Greenbone's supported
administration workflow.

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

## Upstream Documentation

Read the upstream documentation for application behavior and lifecycle operations:

- [Greenbone Community Containers](https://greenbone.github.io/docs/latest/22.4/container/)
- [Greenbone Community Edition Documentation](https://greenbone.github.io/docs/latest/)
