{{- define "full-stack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "full-stack.fullname" -}}
{{- $name := default .Chart.Name .Values.fullnameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "full-stack.labels" -}}
app.kubernetes.io/name: {{ include "full-stack.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "full-stack.selectorLabels" -}}
app.kubernetes.io/name: {{ include "full-stack.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
