#!/usr/bin/env bash
set -u

ROOT="/Users/girinman/repos/cmux-hackathon-politicast"
SCHEDULER_TICK_SECONDS="${SCHEDULER_TICK_SECONDS:-60}"
CODEX_BIN="${CODEX_BIN:-/opt/homebrew/bin/codex}"
LOG_DIR="$ROOT/_workspace/logs"
RUN_LOG_DIR="$LOG_DIR/paper_task_runs"
STATUS_DIR="$ROOT/_workspace/status"
TASK_STATUS_DIR="$STATUS_DIR/paper_tasks"
LOCK_DIR="$ROOT/_workspace/.paper_task.lock"
WATCH_LOG="$LOG_DIR/paper_tasks_watch.log"

mkdir -p "$LOG_DIR" "$RUN_LOG_DIR" "$STATUS_DIR" "$TASK_STATUS_DIR"

timestamp() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

timestamp_from_epoch() {
  date -u -r "$1" '+%Y-%m-%dT%H:%M:%SZ'
}

task_interval() {
  case "$1" in
    pdf_build) echo "${PDF_BUILD_INTERVAL_SECONDS:-300}" ;;
    results_review) echo "${RESULTS_REVIEW_INTERVAL_SECONDS:-600}" ;;
    ko_sync) echo "${KO_SYNC_INTERVAL_SECONDS:-900}" ;;
    quality_maintenance) echo "${QUALITY_MAINTENANCE_INTERVAL_SECONDS:-2700}" ;;
    project_review) echo "${PROJECT_REVIEW_INTERVAL_SECONDS:-3600}" ;;
    *) echo 3600 ;;
  esac
}

task_timeout() {
  case "$1" in
    pdf_build) echo "${PDF_BUILD_TIMEOUT_SECONDS:-180}" ;;
    results_review) echo "${RESULTS_REVIEW_TIMEOUT_SECONDS:-600}" ;;
    ko_sync) echo "${KO_SYNC_TIMEOUT_SECONDS:-600}" ;;
    quality_maintenance) echo "${QUALITY_MAINTENANCE_TIMEOUT_SECONDS:-900}" ;;
    project_review) echo "${PROJECT_REVIEW_TIMEOUT_SECONDS:-1200}" ;;
    *) echo 600 ;;
  esac
}

task_prompt() {
  case "$1" in
    results_review) echo "$ROOT/_workspace/scripts/paper_task_results_prompt.md" ;;
    ko_sync) echo "$ROOT/_workspace/scripts/paper_task_ko_sync_prompt.md" ;;
    quality_maintenance) echo "$ROOT/_workspace/scripts/paper_task_quality_prompt.md" ;;
    project_review) echo "$ROOT/_workspace/scripts/paper_task_project_review_prompt.md" ;;
    *) echo "" ;;
  esac
}

next_file() {
  echo "$TASK_STATUS_DIR/$1.next_epoch"
}

summary_file() {
  echo "$TASK_STATUS_DIR/$1.last_summary.md"
}

status_file() {
  echo "$TASK_STATUS_DIR/$1.status.json"
}

set_next_due() {
  task="$1"
  interval="$(task_interval "$task")"
  echo "$(($(date '+%s') + interval))" > "$(next_file "$task")"
}

is_due() {
  task="$1"
  file="$(next_file "$task")"
  now="$(date '+%s')"
  [ ! -f "$file" ] && return 0
  due="$(cat "$file" 2>/dev/null || echo 0)"
  [ "$now" -ge "$due" ]
}

write_task_status() {
  task="$1"
  state="$2"
  phase="$3"
  exit_code="${4:-null}"
  run_id="${5:-}"
  run_log="${6:-}"
  started_at="${7:-}"
  finished_at="${8:-}"
  child_pid="${9:-}"

  next_due_at=""
  if [ -f "$(next_file "$task")" ]; then
    next_due_at="$(timestamp_from_epoch "$(cat "$(next_file "$task")")")"
  fi

  cat > "$(status_file "$task")" <<EOF
{
  "task": "$task",
  "state": "$state",
  "phase": "$phase",
  "last_exit_code": $exit_code,
  "run_id": "$run_id",
  "child_pid": "$child_pid",
  "started_at": "$started_at",
  "finished_at": "$finished_at",
  "next_due_at": "$next_due_at",
  "interval_seconds": $(task_interval "$task"),
  "timeout_seconds": $(task_timeout "$task"),
  "last_run_log": "$run_log",
  "last_summary": "$(summary_file "$task")"
}
EOF
}

cleanup_lock() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

kill_child_tree() {
  child_pid="$1"
  kill "$child_pid" 2>/dev/null || true
  pkill -P "$child_pid" 2>/dev/null || true
  sleep 2
  kill -9 "$child_pid" 2>/dev/null || true
  pkill -9 -P "$child_pid" 2>/dev/null || true
}

run_with_timeout() {
  task="$1"
  timeout_seconds="$2"
  shift 2
  "$@" &
  child_pid=$!
  deadline=$(($(date '+%s') + timeout_seconds))
  echo "$child_pid"
  while kill -0 "$child_pid" 2>/dev/null; do
    if [ "$(date '+%s')" -ge "$deadline" ]; then
      kill_child_tree "$child_pid"
      wait "$child_pid" 2>/dev/null || true
      return 124
    fi
    sleep 5
  done
  wait "$child_pid"
}

run_pdf_build() {
  task="pdf_build"
  run_id="$(date -u '+%Y%m%dT%H%M%SZ')"
  run_log="$RUN_LOG_DIR/${run_id}_${task}.log"
  started_at="$(timestamp)"
  write_task_status "$task" "running" "build_pdfs" "null" "$run_id" "$run_log" "$started_at" "" ""
  "$ROOT/_workspace/scripts/build_paper_pdfs.sh" > "$run_log" 2>&1
  status=$?
  finished_at="$(timestamp)"
  {
    echo "Mode: pdf_build"
    echo "Exit code: $status"
    echo "Run log: $run_log"
    echo "Finished at: $finished_at"
  } > "$(summary_file "$task")"
  set_next_due "$task"
  write_task_status "$task" "sleeping" "waiting_next_interval" "$status" "$run_id" "$run_log" "$started_at" "$finished_at" ""
  return "$status"
}

run_codex_task() {
  task="$1"
  prompt="$(task_prompt "$task")"
  timeout_seconds="$(task_timeout "$task")"
  run_id="$(date -u '+%Y%m%dT%H%M%SZ')"
  run_log="$RUN_LOG_DIR/${run_id}_${task}.log"
  summary_tmp="$TASK_STATUS_DIR/${task}.last_summary.tmp"
  started_at="$(timestamp)"

  rm -f "$summary_tmp"
  write_task_status "$task" "running" "codex_task" "null" "$run_id" "$run_log" "$started_at" "" ""

  "$CODEX_BIN" exec \
    --cd "$ROOT" \
    --dangerously-bypass-approvals-and-sandbox \
    --color never \
    --output-last-message "$summary_tmp" \
    < "$prompt" > "$run_log" 2>&1 &

  child_pid=$!
  write_task_status "$task" "running" "codex_task" "null" "$run_id" "$run_log" "$started_at" "" "$child_pid"
  deadline=$(($(date '+%s') + timeout_seconds))
  while kill -0 "$child_pid" 2>/dev/null; do
    if [ "$(date '+%s')" -ge "$deadline" ]; then
      echo "[$(timestamp)] $task timed out after ${timeout_seconds}s" >> "$run_log"
      kill_child_tree "$child_pid"
      wait "$child_pid" 2>/dev/null || true
      status=124
      finished_at="$(timestamp)"
      set_next_due "$task"
      write_task_status "$task" "sleeping" "timed_out_waiting_next_interval" "$status" "$run_id" "$run_log" "$started_at" "$finished_at" ""
      return "$status"
    fi
    sleep 5
  done

  wait "$child_pid"
  status=$?
  finished_at="$(timestamp)"
  if [ -s "$summary_tmp" ]; then
    mv "$summary_tmp" "$(summary_file "$task")"
  else
    {
      echo "No final Codex summary was written."
      echo
      echo "See raw run log: $run_log"
    } > "$(summary_file "$task")"
  fi
  set_next_due "$task"
  write_task_status "$task" "sleeping" "waiting_next_interval" "$status" "$run_id" "$run_log" "$started_at" "$finished_at" ""
  return "$status"
}

run_task() {
  task="$1"
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "[$(timestamp)] lock busy; skip $task" >> "$WATCH_LOG"
    return 0
  fi

  {
    echo "[$(timestamp)] task start: $task"
    cd "$ROOT" || exit 1
    if [ "$task" = "pdf_build" ]; then
      run_pdf_build
    else
      run_codex_task "$task"
    fi
    status=$?
    echo "[$(timestamp)] task exit: $task status=$status"
  } >> "$WATCH_LOG" 2>&1
  cleanup_lock
}

trap cleanup_lock EXIT INT TERM

while true; do
  for task in results_review pdf_build ko_sync quality_maintenance project_review; do
    if is_due "$task"; then
      run_task "$task"
    fi
  done
  sleep "$SCHEDULER_TICK_SECONDS"
done
