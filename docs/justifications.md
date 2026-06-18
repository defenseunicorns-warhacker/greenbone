# Greenbone Community Edition Justifications

This document tracks UDS requirement exceptions and operational caveats for the package.

## Security Policy Exemption

The `ospd-openvas` scanner container requires the following UDS policy exemptions:

- `DropAllCapabilities`
- `RestrictCapabilities`
- `RestrictSeccomp`

The upstream Greenbone compose stack grants `NET_ADMIN` and `NET_RAW` and uses an unconfined
seccomp profile for the OpenVAS scanner. These settings support raw socket operations, packet-level
scanner behavior, and host discovery. The exemption is limited to the Greenbone StatefulSet pod.

Revisit this exemption after deploy validation. If Greenbone documents a lower-privilege scanner
mode that works in Kubernetes, prefer that mode and remove the exemption.

## SSO

The package does not configure UDS SSO. Greenbone Community Edition's published container stack uses
native Greenbone authentication and does not document a supported OIDC or SAML configuration for
Greenbone Security Assistant.

## Monitoring

The package does not create ServiceMonitors. Greenbone Community Edition does not expose a
documented Prometheus metrics endpoint in the upstream container stack.

## Image Pinning

The upstream Community registry uses moving tags such as `latest`, `stable`, and `stable-slim` for
the official container stack. The package keeps those upstream references for the initial package so
the chart matches the documented deployment model.

Before a production release, mirror these images and pin to immutable digests or a validated
internal tag policy.

## Workload Type (StatefulSet vs Deployment)

The Greenbone stack runs as a single `StatefulSet` (`greenbone-community`) with `replicaCount: 1`.
The chart collapses the upstream docker-compose topology into one pod with multiple long-running
containers and a chain of init containers. This is a deliberate choice, not an accident of
scaffolding.

The workload is genuinely stateful: it persists a PostgreSQL cluster, vulnerability feeds
(VT/SCAP/CERT/Notus), gvmd data, GPG keyrings, and GSA web assets across 11 `ReadWriteOnce` PVCs.
The `pg-cluster-init` and `gvmd-data-init` containers seed these volumes on first run and skip
seeding if data already exists, so data survives restarts and redeploys.

`StatefulSet` is preferred over `Deployment` for this workload because of the interaction between
`ReadWriteOnce` volumes and update semantics:

- A `StatefulSet` terminates the old pod fully before starting the new one (at-most-one
  semantics). This is exactly what `ReadWriteOnce` volumes require, since two pods cannot mount the
  same RWO PVC simultaneously.
- A `Deployment` defaults to a `RollingUpdate` strategy that tries to start the new pod before
  terminating the old one. With RWO volumes this deadlocks: the new pod cannot mount PVCs still held
  by the old pod. A `Deployment` would therefore require `strategy: Recreate`.
- `volumeClaimTemplates` auto-creates and binds all 11 PVCs. A `Deployment` would require 11
  hand-written `PersistentVolumeClaim` manifests to achieve the same result.

The per-replica storage rationale that normally motivates a `StatefulSet` does not apply here, since
`replicaCount` is fixed at 1 (inter-container links use `emptyDir` Unix sockets and loopback via
`hostAliases`, not pod DNS). The `StatefulSet` is effectively used as a single-replica workload that
manages its own PVCs and provides RWO-safe in-place updates.

Note that a `StatefulSet` does not expose an `Available` condition (only `Deployment` does), so
readiness must be checked against the pod (for example, `Pod/greenbone-community-0` with
`condition: Ready`) or via `kubectl rollout status`, rather than waiting on a `StatefulSet`
`Available` condition.

## Dependency Packaging

PostgreSQL is split out of the application pod into a **separate `greenbone-db` Zarf package**
(`db/`) running the upstream `pg-gvm` image as its own StatefulSet, reachable over TCP at
`greenbone-db:5432`. The application chart connects gvmd to it by default (`postgres.embedded:
false`); set `postgres.embedded: true` to fall back to the legacy in-pod pg-gvm container. Both
packages deploy into the `greenbone` namespace and share a generated `greenbone-db-credentials`
Secret, so the app's IntraNamespace network policy already permits gvmd → postgres.

The standard UDS PostgreSQL operators (Zalando/CrunchyData) were evaluated and are **not** a drop-in
replacement: gvmd requires the Greenbone-specific **`pg-gvm` C extension** (`libpg-gvm.so` +
`pg-gvm--*.sql`), which is not `trusted` and so needs a superuser to install and must be baked into
the Postgres server image. The official `pg-gvm` image already ships the extension and self-creates
the `gvmd` role/database/extensions and the superuser `dba` role on first boot, which is why this
package uses it directly. Adopting an operator would require building and maintaining a custom
Postgres image carrying `pg-gvm` for the operator's exact PostgreSQL major version.

Redis remains in-pod. The upstream redis-server image listens only on a Unix socket (`port 0`), so
it is coupled to the scanner/manager via shared sockets and is not trivially externalized; evaluate
a Valkey/Redis package only with that socket configuration validated.
