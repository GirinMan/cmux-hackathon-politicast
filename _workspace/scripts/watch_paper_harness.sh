#!/usr/bin/env bash
set -u

ROOT="/Users/girinman/repos/cmux-hackathon-politicast"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-900}"
LOG_DIR="$ROOT/_workspace/logs"
RUN_LOG_DIR="$LOG_DIR/paper_harness_runs"
STATUS_DIR="$ROOT/_workspace/status"
STATUS_FILE="$STATUS_DIR/paper_harness_watch_status.json"
LAST_SUMMARY_FILE="$STATUS_DIR/paper_harness_last_summary.md"
LOCK_DIR="$ROOT/_workspace/.paper_harness_check.lock"
PROMPT="$ROOT/_workspace/scripts/paper_harness_check_prompt.md"
CODEX_BIN="${CODEX_BIN:-/opt/homebrew/bin/codex}"
STALE_LOCK_SECONDS="${STALE_LOCK_SECONDS:-7200}"
CHECK_TIMEOUT_SECONDS="${CHECK_TIMEOUT_SECONDS:-600}"

mkdir -p "$LOG_DIR" "$RUN_LOG_DIR" "$STATUS_DIR"

timestamp() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

timestamp_from_epoch() {
  date -u -r "$1" '+%Y-%m-%dT%H:%M:%SZ'
}

lock_age_seconds() {
  now="$(date '+%s')"
  lock_mtime="$(stat -f '%m' "$LOCK_DIR" 2>/dev/null || echo "$now")"
  echo $((now - lock_mtime))
}

cleanup_lock() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

write_status() {
  state="$1"
  phase="$2"
  exit_code="${3:-null}"
  run_id="${4:-}"
  run_log="${5:-}"
  started_at="${6:-}"
  finished_at="${7:-}"
  next_epoch="${8:-}"
  child_pid="${9:-}"

  next_due_at=""
  if [ -n "$next_epoch" ]; then
    next_due_at="$(timestamp_from_epoch "$next_epoch")"
  fi

  cat > "$STATUS_FILE" <<EOF
{
  "state": "$state",
  "phase": "$phase",
  "last_exit_code": $exit_code,
  "run_id": "$run_id",
  "child_pid": "$child_pid",
  "started_at": "$started_at",
  "finished_at": "$finished_at",
  "next_due_at": "$next_due_at",
  "interval_seconds": $INTERVAL_SECONDS,
  "check_timeout_seconds": $CHECK_TIMEOUT_SECONDS,
  "watch_log": "$LOG_DIR/paper_harness_watch.log",
  "last_run_log": "$run_log",
  "last_summary": "$LAST_SUMMARY_FILE"
}
EOF
}

run_codex_check() {
  run_id="$(date -u '+%Y%m%dT%H%M%SZ')"
  run_log="$RUN_LOG_DIR/$run_id.log"
  summary_tmp="$STATUS_DIR/paper_harness_last_summary.tmp"
  started_at="$(timestamp)"
  rm -f "$summary_tmp"

  write_status "running" "codex_check" "null" "$run_id" "$run_log" "$started_at" "" "" ""

  "$CODEX_BIN" exec \
    --cd "$ROOT" \
    --dangerously-bypass-approvals-and-sandbox \
    --color never \
    --output-last-message "$summary_tmp" \
    < "$PROMPT" > "$run_log" 2>&1 &

  child_pid=$!
  write_status "running" "codex_check" "null" "$run_id" "$run_log" "$started_at" "" "" "$child_pid"
  deadline=$(($(date '+%s') + CHECK_TIMEOUT_SECONDS))
  while kill -0 "$child_pid" 2>/dev/null; do
    if [ "$(date '+%s')" -ge "$deadline" ]; then
      echo "[$(timestamp)] paper/harness consistency check timed out after ${CHECK_TIMEOUT_SECONDS}s"
      write_status "timed_out" "timeout" "124" "$run_id" "$run_log" "$started_at" "$(timestamp)" "" "$child_pid"
      kill "$child_pid" 2>/dev/null || true
      pkill -P "$child_pid" 2>/dev/null || true
      sleep 2
      kill -9 "$child_pid" 2>/dev/null || true
      pkill -9 -P "$child_pid" 2>/dev/null || true
      wait "$child_pid" 2>/dev/null || true
      return 124
    fi
    sleep 5
  done

  wait "$child_pid"
  status=$?
  finished_at="$(timestamp)"
  next_epoch=$(($(date '+%s') + INTERVAL_SECONDS))
  if [ -s "$summary_tmp" ]; then
    mv "$summary_tmp" "$LAST_SUMMARY_FILE"
  else
    {
      echo "No final Codex summary was written."
      echo
      echo "See raw run log: $run_log"
    } > "$LAST_SUMMARY_FILE"
  fi
  write_status "sleeping" "waiting_next_interval" "$status" "$run_id" "$run_log" "$started_at" "$finished_at" "$next_epoch" ""
  return "$status"
}

trap cleanup_lock EXIT INT TERM

while true; do
  ts="$(timestamp)"
  if [ -d "$LOCK_DIR" ] && [ "$(lock_age_seconds)" -gt "$STALE_LOCK_SECONDS" ]; then
    echo "[$ts] removing stale paper/harness consistency lock" >> "$LOG_DIR/paper_harness_watch.log"
    cleanup_lock
  fi

  if mkdir "$LOCK_DIR" 2>/dev/null; then
    {
      echo "[$ts] paper/harness consistency check start"
      cd "$ROOT" || exit 1
      run_codex_check
      status=$?
      echo "[$(timestamp)] latest run log: $(ls -1 "$RUN_LOG_DIR"/*.log 2>/dev/null | sort | tail -n 1)"
      echo "[$(timestamp)] latest summary: $LAST_SUMMARY_FILE"
      echo "[$(timestamp)] paper/harness consistency check exit=$status"
    } >> "$LOG_DIR/paper_harness_watch.log" 2>&1
    cleanup_lock
  else
    echo "[$ts] previous paper/harness consistency check still running; skip" >> "$LOG_DIR/paper_harness_watch.log"
    write_status "skipped" "previous_check_running" "null" "" "" "" "$(timestamp)" "" ""
  fi
  next_epoch=$(($(date '+%s') + INTERVAL_SECONDS))
  if [ -f "$STATUS_FILE" ]; then
    :
  else
    write_status "sleeping" "waiting_next_interval" "null" "" "" "" "$(timestamp)" "$next_epoch" ""
  fi
  sleep "$INTERVAL_SECONDS"
done
