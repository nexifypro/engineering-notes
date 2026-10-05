#!/usr/bin/env bash
# Timing helpers used for the article's measurements. Each prints seconds.
set -euo pipefail

# 1) push-to-serving: from "new image tag pushed" to the ALB serving the new APP_VERSION.
#    usage: scripts/measure.sh serving <url> <expected_version>
# 2) scale-out: poll running task/pod count every 5s during the k6 ramp; prints time to reach N.
#    usage: scripts/measure.sh scale ecs <cluster> <service> <N>   |   scripts/measure.sh scale k8s <deployment> <N>
# 3) rollback: time for the previous version to be served again after triggering a rollback.
#    usage: scripts/measure.sh serving <url> <previous_version>

cmd=${1:?}; shift
case "$cmd" in
  serving)
    url=$1; want=$2; start=$(date +%s)
    until curl -sf "$url/healthz" | grep -q "\"version\":\"$want\""; do sleep 2; done
    echo "serving $want after $(( $(date +%s) - start ))s";;
  scale)
    kind=$1; shift; start=$(date +%s)
    if [ "$kind" = ecs ]; then
      cluster=$1; service=$2; n=$3
      count() { aws ecs describe-services --cluster "$cluster" --services "$service" --query 'services[0].runningCount' --output text; }
    else
      dep=$1; n=$2
      count() { kubectl get deploy "$dep" -o jsonpath='{.status.readyReplicas}'; }
    fi
    while [ "$(count)" -lt "$n" ]; do echo "$(( $(date +%s) - start ))s running=$(count)"; sleep 5; done
    echo "reached $n after $(( $(date +%s) - start ))s";;
  *) echo "unknown command"; exit 1;;
esac
