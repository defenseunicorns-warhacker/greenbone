{{- define "greenbone.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "greenbone.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "greenbone.labels" -}}
app.kubernetes.io/name: {{ include "greenbone.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: greenbone
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "greenbone.selectorLabels" -}}
app.kubernetes.io/name: {{ include "greenbone.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "greenbone.image" -}}
{{- printf "%s/%s:%s" $.Values.imageRegistry .repository .tag -}}
{{- end -}}

{{/*
greenbone.seedCommand renders a `command:` list for a feed-data init container.
It copies the image's bundled feed data from `src` into `dst` (default /mnt),
which is the path the corresponding persistent volume is mounted at.

The upstream feed images run as root and their entrypoints touch marker files
and runtime dirs outside the data volume; that fails under the restricted,
non-root SecurityContext enforced here. We override the entrypoint with a plain
copy instead. The source is validated first so a wrong path fails loudly with a
clear message rather than silently leaving an empty volume that surfaces later
as a confusing gvmd error.

Usage: {{- include "greenbone.seedCommand" (dict "src" "/path") | nindent 12 }}
*/}}
{{- define "greenbone.seedCommand" -}}
- /bin/sh
- -c
- |
  set -eu
  SRC="{{ .src }}"
  DST="{{ .dst | default "/mnt" }}"
  if [ ! -d "$SRC" ] || [ -z "$(ls -A "$SRC" 2>/dev/null)" ]; then
    echo "ERROR: expected feed data at ${SRC} but it is missing or empty" >&2
    exit 1
  fi
  echo "Seeding ${SRC} -> ${DST}"
  cp -r "$SRC/." "$DST/"
  echo "Finished seeding ${DST}"
{{- end -}}
