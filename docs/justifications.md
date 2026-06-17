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

The upstream Greenbone Community stack ships PostgreSQL and Redis-compatible containers as part of
the official container topology. This initial package preserves that topology because Greenbone
coordinates local Unix sockets, filesystem layout, migrations, and service users across the
containers.

For a hardened production package, evaluate replacing the embedded PostgreSQL and Redis-compatible
containers with the UDS PostgreSQL Operator and Valkey packages. That refactor requires validation
against Greenbone's supported database and Redis socket configuration.
