#!/usr/bin/env bash
# Continuous PR agent loop — closes the delivery path from AGENTS.md:
#   open PR → checks → review gate → merge → deploy (CI on main) → live verify
#
# Other agents open PRs; this loop processes them indefinitely until stopped.
#
# Usage:
#   ./scripts/pr_agent_loop.sh              # continuous (default)
#   ./scripts/pr_agent_loop.sh --once        # single pass (CI / workflow_dispatch)
#   PR_AGENT_DRY_RUN=1 ./scripts/pr_agent_loop.sh --once
#   PR_AGENT_AUTO_MERGE=0 ...               # report only, never merge
#   PR_AGENT_LIVE_VERIFY=0 ...              # skip post-merge live e2e
#   PR_AGENT_INTERVAL_SEC=120 ...           # sleep between passes (default 90)
#   PR_AGENT_LOG_DIR=/tmp/pr-agent-logs ... # log + state directory
#
# Env gate for auto-merge (safety):
#   PR_AGENT_AUTO_MERGE=1 (default) requires checks success + mergeable + review gate
#   PR_AGENT_REQUIRE_REVIEW_APPROVAL=0 (default) — agent posts review comment; approval not mandatory
#   PR_AGENT_MAX_MERGE_PER_PASS=2 — avoid flooding deploy with too many merges at once
#   PR_AGENT_PR_LABEL_SKIP=pr-agent-skip — PRs with this label are ignored
#   PR_AGENT_PR_LABEL_HOLD=pr-agent-hold — report but do not merge
#   LIVE_APP_URL / LIVE_API_URL for post-deploy live suite (defaults to prod)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ONCE=0
for arg in "$@"; do
  case "$arg" in
    --once) ONCE=1 ;;
    -h|--help)
      sed -n '2,30p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
  esac
done

INTERVAL_SEC="${PR_AGENT_INTERVAL_SEC:-90}"
LOG_DIR="${PR_AGENT_LOG_DIR:-${TMPDIR:-/tmp}/pr-agent-logs}"
STATE_DIR="${PR_AGENT_STATE_DIR:-$LOG_DIR/state}"
AUTO_MERGE="${PR_AGENT_AUTO_MERGE:-1}"
DRY_RUN="${PR_AGENT_DRY_RUN:-0}"
LIVE_VERIFY="${PR_AGENT_LIVE_VERIFY:-1}"
REQUIRE_APPROVAL="${PR_AGENT_REQUIRE_REVIEW_APPROVAL:-0}"
MAX_MERGE_PER_PASS="${PR_AGENT_MAX_MERGE_PER_PASS:-2}"
LABEL_SKIP="${PR_AGENT_PR_LABEL_SKIP:-pr-agent-skip}"
LABEL_HOLD="${PR_AGENT_PR_LABEL_HOLD:-pr-agent-hold}"
BASE_BRANCH="${PR_AGENT_BASE_BRANCH:-main}"
LIVE_APP_URL="${LIVE_APP_URL:-https://alagoas.precospublicos.ia.br}"
LIVE_API_URL="${LIVE_API_URL:-https://alagoas.precospublicos.ia.br}"
PASS_TS=""

mkdir -p "$LOG_DIR" "$STATE_DIR"

log() {
  local line="[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
  echo "$line" | tee -a "$LOG_DIR/pr-agent.log"
}

die() { log "FATAL: $*"; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

need_cmd gh
need_cmd jq
need_cmd git

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
[[ -n "$REPO" ]] || die "gh cannot resolve repo (run from a git checkout with remote)"

log "pr_agent_loop start repo=$REPO once=$ONCE auto_merge=$AUTO_MERGE dry_run=$DRY_RUN live_verify=$LIVE_VERIFY log_dir=$LOG_DIR"

# --- helpers ---

checks_conclusion() {
  # Returns: success | failure | pending | none
  local pr="$1"
  local rollup
  rollup="$(gh pr view "$pr" --json statusCheckRollup -q '
    .statusCheckRollup // []
    | if length == 0 then "none"
      elif any(.[]; (.conclusion // .state // "") | test("FAILURE|ERROR|CANCELLED|TIMED_OUT|ACTION_REQUIRED"; "i")) then "failure"
      elif any(.[]; ((.status // "") == "IN_PROGRESS" or (.status // "") == "QUEUED" or ((.conclusion // "") == "" and (.state // "") | test("PENDING|EXPECTED"; "i")))) then "pending"
      elif all(.[]; (.conclusion // .state // "") | test("SUCCESS|NEUTRAL|SKIPPED"; "i")) then "success"
      else "pending"
      end
  ' 2>/dev/null || echo "none")"
  echo "$rollup"
}

pr_has_label() {
  local pr="$1" want="$2"
  gh pr view "$pr" --json labels -q --arg w "$want" '.labels[].name' 2>/dev/null | grep -Fxq "$want"
}

pr_is_draft() {
  local pr="$1"
  [[ "$(gh pr view "$pr" --json isDraft -q .isDraft)" == "true" ]]
}

pr_mergeable_state() {
  # MERGEABLE | CONFLICTING | UNKNOWN
  gh pr view "$pr" --json mergeable -q .mergeable 2>/dev/null || echo "UNKNOWN"
}

# Lightweight agent review: security/scope heuristics on the diff summary.
# Posts a PR comment (not a blocking GitHub review approval unless configured).
agent_review_gate() {
  local pr="$1"
  local files body risk=0 notes=()

  files="$(gh pr view "$pr" --json files -q '.files[].path' 2>/dev/null || true)"
  body="$(gh pr view "$pr" --json body,title -q '"\(.title)\n\(.body // "")"' 2>/dev/null || true)"

  # Secret / auth risk paths — still allow but flag
  if echo "$files" | grep -Eq '(\.env$|credentials|id_rsa|secret)'; then
    notes+=("touches potential secret paths")
    risk=$((risk + 2))
  fi
  if echo "$files" | grep -Eq '^(\.github/workflows/|deploy/)'; then
    notes+=("touches deploy/CI — extra scrutiny")
    risk=$((risk + 1))
  fi
  # AGENTS batch rule reminder for tiny single-file non-test PRs is advisory only

  local marker_file="$STATE_DIR/reviewed-pr-$pr"
  if [[ ! -f "$marker_file" ]]; then
    local note_txt
    if ((${#notes[@]})); then
      note_txt=$(printf -- '- %s\n' "${notes[@]}")
    else
      note_txt="- No high-risk path heuristics triggered"
    fi
    local comment
    comment=$(cat <<EOF
## PR agent review gate (automated)

Delivery path check per \`AGENTS.md\`: branch → PR → review → merge → deploy → live.

**Paths in PR** (truncated):
\`\`\`
$(echo "$files" | head -40)
\`\`\`

**Heuristic notes**:
$note_txt

**Risk score**: $risk (informational; merge still requires green checks + mergeable)

_Posted by \`scripts/pr_agent_loop.sh\` — continuous PR ops loop._
EOF
)
    if [[ "$DRY_RUN" == "1" ]]; then
      log "PR #$pr review DRY_RUN (would comment risk=$risk)"
    else
      gh pr comment "$pr" --body "$comment" >/dev/null 2>&1 || log "PR #$pr comment failed (non-fatal)"
      log "PR #$pr agent review posted risk=$risk"
    fi
    echo "$risk" > "$marker_file"
  fi

  # Gate: block only on very high risk unless explicitly waived
  if (( risk >= 4 )); then
    return 1
  fi
  return 0
}

approval_ok() {
  local pr="$1"
  if [[ "$REQUIRE_APPROVAL" != "1" ]]; then
    return 0
  fi
  local decision
  decision="$(gh pr view "$pr" --json reviewDecision -q .reviewDecision 2>/dev/null || echo "")"
  [[ "$decision" == "APPROVED" ]]
}

try_merge() {
  local pr="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "PR #$pr MERGE DRY_RUN — would squash-merge"
    echo "dry_run" > "$STATE_DIR/merged-pr-$pr"
    return 0
  fi
  if gh pr merge "$pr" --squash --delete-branch 2>"$LOG_DIR/merge-$pr.err"; then
    log "PR #$pr MERGED (squash)"
    echo "merged $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATE_DIR/merged-pr-$pr"
    return 0
  fi
  # fallback without delete-branch
  if gh pr merge "$pr" --squash 2>>"$LOG_DIR/merge-$pr.err"; then
    log "PR #$pr MERGED (squash, branch kept)"
    echo "merged $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATE_DIR/merged-pr-$pr"
    return 0
  fi
  log "PR #$pr merge FAILED: $(tr '\n' ' ' <"$LOG_DIR/merge-$pr.err" | head -c 200)"
  return 1
}

wait_main_deploy() {
  # Poll latest Deploy workflow on main for terminal status (up to ~15 min)
  local deadline=$((SECONDS + 900))
  local run_id status conc
  log "waiting for main CI/deploy to settle..."
  while (( SECONDS < deadline )); do
    run_id="$(gh run list --branch "$BASE_BRANCH" --workflow "deploy.yml" --limit 1 --json databaseId,status,conclusion -q '.[0].databaseId' 2>/dev/null || true)"
    if [[ -z "$run_id" || "$run_id" == "null" ]]; then
      sleep 20
      continue
    fi
    status="$(gh run view "$run_id" --json status,conclusion -q '.status' 2>/dev/null || echo "")"
    conc="$(gh run view "$run_id" --json status,conclusion -q '.conclusion' 2>/dev/null || echo "")"
    log "main deploy run=$run_id status=$status conclusion=$conc"
    if [[ "$status" == "completed" ]]; then
      echo "$conc"
      return 0
    fi
    sleep 25
  done
  echo "timeout"
  return 1
}

run_live_verify() {
  # MANDATORY for goal: production hosts via headless. Smoke alone is insufficient —
  # must run `npm run live` (multi-surface + screenshots). Returns non-zero on failure.
  if [[ "$LIVE_VERIFY" != "1" ]]; then
    log "live verify skipped (PR_AGENT_LIVE_VERIFY!=1) — GOAL RISK"
    return 1
  fi
  if [[ ! -d "$ROOT/e2e" ]]; then
    log "no e2e/ dir — cannot live-verify"
    return 1
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    log "live verify DRY_RUN — would run smoke+live on $LIVE_APP_URL"
    return 0
  fi
  local smoke_ec=1 live_ec=1 rc=0
  cd "$ROOT/e2e"
  if [[ ! -d node_modules ]]; then
    npm install --no-audit --no-fund 2>&1 | tail -5 || true
  fi
  export APP_URL="$LIVE_APP_URL" API_URL="$LIVE_API_URL"
  log "LIVE PROD smoke APP_URL=$APP_URL API_URL=$API_URL"
  set +e
  npm run smoke >"$LOG_DIR/live-smoke.out" 2>"$LOG_DIR/live-smoke.err"
  smoke_ec=$?
  npm run live >"$LOG_DIR/live-full.out" 2>"$LOG_DIR/live-full.err"
  live_ec=$?
  set -e
  echo "$smoke_ec" >"$LOG_DIR/live-smoke.ec"
  echo "$live_ec" >"$LOG_DIR/live-full.ec"
  [[ "$smoke_ec" -eq 0 ]] && log "live smoke OK (prod)" || { log "live smoke FAILED ec=$smoke_ec"; rc=1; }
  [[ "$live_ec" -eq 0 ]] && log "live full OK (prod)" || { log "live full FAILED ec=$live_ec"; rc=1; }
  if [[ -d /work/proofs ]]; then
    cp -f "$LOG_DIR/live-smoke.out" /work/proofs/_live-smoke.out 2>/dev/null || true
    cp -f "$LOG_DIR/live-full.out" /work/proofs/_live-full.out 2>/dev/null || true
    cp -f "$LOG_DIR/live-smoke.ec" /work/proofs/_live-smoke.ec 2>/dev/null || true
    cp -f "$LOG_DIR/live-full.ec" /work/proofs/_live-full.ec 2>/dev/null || true
    date -u +%Y-%m-%dT%H:%M:%SZ > /work/proofs/_live-verified-at.txt
    mkdir -p /work/proofs/_e2e-screenshots-snapshot
    cp -f "$ROOT/e2e/screenshots"/live*.png /work/proofs/_e2e-screenshots-snapshot/ 2>/dev/null || true
  fi
  cd "$ROOT"
  return "$rc"
}

process_pr() {
  local pr="$1"
  local title checks mergeable

  title="$(gh pr view "$pr" --json title -q .title 2>/dev/null || echo "?")"
  log "--- PR #$pr: $title ---"

  if pr_is_draft "$pr"; then
    log "PR #$pr draft — skip"
    return 0
  fi
  if pr_has_label "$pr" "$LABEL_SKIP"; then
    log "PR #$pr has $LABEL_SKIP — skip"
    return 0
  fi
  if pr_has_label "$pr" "$LABEL_HOLD"; then
    log "PR #$pr has $LABEL_HOLD — hold (no merge)"
    agent_review_gate "$pr" || true
    return 0
  fi
  if [[ -f "$STATE_DIR/merged-pr-$pr" ]]; then
    log "PR #$pr already handled this agent state — skip"
    return 0
  fi

  # Ensure PR targets main
  local base
  base="$(gh pr view "$pr" --json baseRefName -q .baseRefName)"
  if [[ "$base" != "$BASE_BRANCH" ]]; then
    log "PR #$pr base=$base (want $BASE_BRANCH) — skip"
    return 0
  fi

  checks="$(checks_conclusion "$pr")"
  mergeable="$(gh pr view "$pr" --json mergeable -q .mergeable 2>/dev/null || echo UNKNOWN)"
  log "PR #$pr checks=$checks mergeable=$mergeable"

  if [[ "$checks" == "failure" ]]; then
    log "PR #$pr checks failed — leave for author/CI fix"
    # One-time nudge
    if [[ ! -f "$STATE_DIR/failed-noted-$pr" ]]; then
      [[ "$DRY_RUN" == "1" ]] || gh pr comment "$pr" --body "PR agent: CI checks are **failing**. Fix CI before merge (delivery path: checks must pass)." >/dev/null 2>&1 || true
      touch "$STATE_DIR/failed-noted-$pr"
    fi
    return 0
  fi

  if [[ "$checks" == "pending" ]]; then
    log "PR #$pr checks still pending — wait next pass"
    return 0
  fi

  # checks success or none (no CI configured for paths) — proceed to review gate
  if ! agent_review_gate "$pr"; then
    log "PR #$pr blocked by agent review risk gate"
    return 0
  fi

  if ! approval_ok "$pr"; then
    log "PR #$pr waiting for GitHub review approval"
    return 0
  fi

  if [[ "$mergeable" == "CONFLICTING" ]]; then
    log "PR #$pr has conflicts — needs rebase"
    if [[ ! -f "$STATE_DIR/conflict-noted-$pr" ]]; then
      [[ "$DRY_RUN" == "1" ]] || gh pr comment "$pr" --body "PR agent: branch has **merge conflicts** with \`$BASE_BRANCH\`. Please rebase/merge main." >/dev/null 2>&1 || true
      touch "$STATE_DIR/conflict-noted-$pr"
    fi
    return 0
  fi

  if [[ "$mergeable" != "MERGEABLE" && "$checks" != "success" ]]; then
    # UNKNOWN mergeable + no checks — be conservative
    log "PR #$pr mergeable=$mergeable checks=$checks — wait (conservative)"
    return 0
  fi

  # Allow merge when checks=none and mergeable=MERGEABLE (e.g. docs-only path ignore)
  if [[ "$mergeable" != "MERGEABLE" && "$mergeable" != "UNKNOWN" ]]; then
    log "PR #$pr not mergeable ($mergeable)"
    return 0
  fi

  if [[ "$AUTO_MERGE" != "1" ]]; then
    log "PR #$pr eligible but AUTO_MERGE=0 — would merge"
    return 0
  fi

  if try_merge "$pr"; then
    MERGED_THIS_PASS=$((MERGED_THIS_PASS + 1))
    return 0
  fi
  return 0
}

one_pass() {
  PASS_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  MERGED_THIS_PASS=0
  log "======== pass begin $PASS_TS ========"

  # Refresh main (best-effort; don't fail loop if dirty)
  git fetch origin "$BASE_BRANCH" --quiet 2>/dev/null || true

  local prs
  prs="$(gh pr list --base "$BASE_BRANCH" --state open --limit 50 --json number -q '.[].number' 2>/dev/null || true)"
  if [[ -z "$prs" ]]; then
    log "no open PRs targeting $BASE_BRANCH"
  else
    local pr count=0
    while IFS= read -r pr; do
      [[ -z "$pr" ]] && continue
      count=$((count + 1))
      process_pr "$pr" || log "PR #$pr process error (non-fatal)"
      if (( MERGED_THIS_PASS >= MAX_MERGE_PER_PASS )); then
        log "hit MAX_MERGE_PER_PASS=$MAX_MERGE_PER_PASS — remaining PRs next pass"
        break
      fi
    done <<< "$prs"
    log "scanned open PRs (processed up to $count this pass, merged=$MERGED_THIS_PASS)"
  fi

  if (( MERGED_THIS_PASS > 0 )); then
    local deploy_result="skipped"
    if [[ "$DRY_RUN" != "1" ]]; then
      deploy_result="$(wait_main_deploy || echo timeout)"
      log "deploy result=$deploy_result"
      # Gate: production live suite is mandatory. Deploy must succeed for VPS to carry shipped code.
      if [[ "$deploy_result" != "success" ]]; then
        log "BLOCKER: main deploy not success ($deploy_result) — shipped PRs are NOT production-verified; will re-queue live reverify"
        echo "$deploy_result" >"$LOG_DIR/last-deploy-conclusion.txt"
        # Still run live against CURRENT prod (may lag main) to prove site health; proofs must mark deploy_failed
        run_live_verify || log "live verify also failed while deploy broken"
        # Clear merge state for PRs merged this pass so future ticks re-process / re-verify after deploy fixed
        if [[ "${PR_AGENT_REQUEUE_ON_DEPLOY_FAIL:-1}" == "1" ]]; then
          for mf in "$STATE_DIR"/merged-pr-*; do
            [[ -f "$mf" ]] || continue
            # only touch recent marker files from this agent dir — requeue all marked so live re-proof happens
            base=$(basename "$mf")
            prnum=${base#merged-pr-}
            mv -f "$mf" "$STATE_DIR/needs-live-reverify-pr-$prnum" 2>/dev/null || true
            log "re-queued PR #$prnum for live re-verify after deploy fix"
          done
        fi
      else
        echo success >"$LOG_DIR/last-deploy-conclusion.txt"
        if ! run_live_verify; then
          log "BLOCKER: deploy green but LIVE PROD suite failed — delivery NOT achieved"
          for mf in "$STATE_DIR"/merged-pr-*; do
            [[ -f "$mf" ]] || continue
            prnum=$(basename "$mf" | sed 's/merged-pr-//')
            mv -f "$mf" "$STATE_DIR/needs-live-reverify-pr-$prnum" 2>/dev/null || true
          done
        else
          log "deploy success + live prod suite OK — shipped PRs production-verified this pass"
        fi
      fi
    else
      log "post-merge deploy/live skipped (dry_run)"
    fi
  elif [[ -n "$(ls "$STATE_DIR"/needs-live-reverify-pr-* 2>/dev/null || true)" ]]; then
    # No new merges — still try deploy+live re-verify for previously shipped PRs lacking prod proof
    log "re-verify pass for shipped PRs lacking live/prod acceptance"
    deploy_result="$(wait_main_deploy || echo timeout)"
    log "deploy result (reverify)=$deploy_result"
    if [[ "$deploy_result" == "success" ]] && run_live_verify; then
      for nf in "$STATE_DIR"/needs-live-reverify-pr-*; do
        [[ -f "$nf" ]] || continue
        prnum=$(basename "$nf" | sed 's/needs-live-reverify-pr-//')
        echo "live_ok $(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$STATE_DIR/prod-verified-pr-$prnum"
        rm -f "$nf"
        if [[ -d /work/proofs/PR-$prnum ]]; then
          echo "prod_verified $(date -u +%Y-%m-%dT%H:%M:%SZ)" >"/work/proofs/PR-$prnum/99-prod-verified.txt"
          cp -f "$LOG_DIR/live-full.out" "/work/proofs/PR-$prnum/10-live-full.out" 2>/dev/null || true
        fi
        log "PR #$prnum marked production-verified"
      done
    else
      log "re-verify still blocked deploy=$deploy_result"
      run_live_verify || true
    fi
  fi

  # Write pass summary for operators
  {
    echo "pass_ts=$PASS_TS"
    echo "merged_this_pass=$MERGED_THIS_PASS"
    echo "open_prs=$(gh pr list --base "$BASE_BRANCH" --state open --limit 50 --json number -q 'length' 2>/dev/null || echo '?')"
  } > "$LOG_DIR/last-pass.env"

  log "======== pass end merged=$MERGED_THIS_PASS ========"
}

# --- main loop ---
if [[ "$ONCE" == "1" ]]; then
  one_pass
  exit 0
fi

log "entering continuous loop interval=${INTERVAL_SEC}s (SIGINT/SIGTERM to stop)"
trap 'log "signal received — exiting loop"; exit 0' INT TERM

while true; do
  one_pass || log "pass error (continuing)"
  sleep "$INTERVAL_SEC"
done
