#!/usr/bin/env bash
set -u

ROOT="/Users/girinman/repos/cmux-hackathon-politicast"
LABEL="com.politikast.paper-harness-watch"
TASK_STATUS_DIR="$ROOT/_workspace/status/paper_tasks"
WATCH_LOG="$ROOT/_workspace/logs/paper_tasks_watch.log"
RUN_LOG_DIR="$ROOT/_workspace/logs/paper_task_runs"

echo "== LaunchAgent =="
launchctl print "gui/$UID/$LABEL" 2>/dev/null \
  | rg 'state|pid|runs|last exit|INTERVAL_SECONDS|CHECK_TIMEOUT_SECONDS' -C 1 \
  || echo "not loaded"

echo
echo "== Processes =="
ps aux | rg '[w]atch_paper_tasks|[c]odex exec --cd /Users/girinman/repos/cmux-hackathon-politicast|[b]uild_paper_pdfs' || echo "no active task process"

echo
echo "== Task Status =="
found_status=0
for task in results_review pdf_build ko_sync quality_maintenance project_review; do
  status_file="$TASK_STATUS_DIR/$task.status.json"
  echo "-- $task --"
  if [ -f "$status_file" ]; then
    found_status=1
    if command -v jq >/dev/null 2>&1; then
      jq . "$status_file"
    else
      cat "$status_file"
    fi
  else
    echo "no status yet"
  fi
done
[ "$found_status" -eq 1 ] || echo "no task status files yet"

echo
echo "== Last Summaries =="
for task in results_review pdf_build ko_sync quality_maintenance project_review; do
  summary_file="$TASK_STATUS_DIR/$task.last_summary.md"
  echo "-- $task --"
  if [ -f "$summary_file" ]; then
    sed -n '1,120p' "$summary_file"
  else
    echo "no summary yet"
  fi
done

echo
echo "== Watch Log Tail =="
tail -n 40 "$WATCH_LOG" 2>/dev/null || echo "missing: $WATCH_LOG"

echo
echo "== Latest Raw Run Log =="
latest_run_log="$(ls -1 "$RUN_LOG_DIR"/*.log 2>/dev/null | sort | tail -n 1)"
if [ -n "$latest_run_log" ]; then
  echo "$latest_run_log"
  tail -n 40 "$latest_run_log"
else
  echo "no raw run logs yet"
fi
