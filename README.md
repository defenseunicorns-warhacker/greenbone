# Greenbone Community Edition UDS Package

This package deploys the Greenbone Community Edition container stack into UDS. It follows the
official Greenbone Community Containers topology and translates the Docker Compose services into a
local Helm chart for Kubernetes deployment.

Greenbone Community Edition is the community distribution of Greenbone Vulnerability Management,
also known as OpenVAS. The package exposes the Greenbone Security Assistant web interface through
UDS Core.

> [!IMPORTANT]
> Greenbone's own container guide states that the Community Containers are intended for testing,
> evaluation, and learning rather than production setups. Treat this package as an initial UDS
> enablement package that needs cluster validation, image pinning strategy review, and operational
> hardening before production use.

## Package Layout

The package uses the standard UDS package layout:

- `chart/`: UDS integration chart containing the `Package` custom resource.
- `charts/greenbone/`: Local Helm chart for the Greenbone Community container stack.
- `common/zarf.yaml`: Shared Zarf component definitions.
- `values/`: Helm override files used by Zarf.
- `db/`: Separate `greenbone-db` Zarf package — the PostgreSQL (`pg-gvm`) database the
  application connects to by default. See `docs/justifications.md` (Dependency Packaging).
- `bundle/`: Local test bundle definition (deploys `greenbone-db` then `greenbone-community`).
- `docs/`: Configuration and justification documentation.

## Upstream References

- [Greenbone Community Containers](https://greenbone.github.io/docs/latest/22.4/container/)
- [Greenbone Community Edition Documentation](https://greenbone.github.io/docs/latest/)
- [Greenbone Community Containers Registry Notice](https://forum.greenbone.net/t/greenbone-container-registry-scheduled-maintenance-and-service-change-on-monday-april-13th-2026/22229)

## Development

Build the package:

```bash
uds zarf package create --flavor upstream --skip-sbom --confirm
```

Create the local test bundle:

```bash
uds create bundle/ --confirm
```

Deploy the bundle into a UDS Core development cluster:

```bash
uds deploy bundle/uds-bundle-greenbone-community-*.tar.zst --confirm
```
