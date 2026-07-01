#!/usr/bin/env bash
# Launch 8 MemEye scenarios in tmux (MCQ + Open per window, no judge).
set -euo pipefail

SESSION="${SESSION:-memeye_full}"
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_memeye_task_full.sh"

TASKS=(
  brand_memory_test
  card_playlog_test
  cartoon_entertainment_companion
  home_renovation_interior_design
  multi_scene_visual_case_archive_assistant
  outdoor_navigation_route_memory_assistant
  personal_health_dashboard_assistant
  social_chat_memory_test
)

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session '$SESSION' already exists. Attach with: tmux attach -t $SESSION"
  exit 1
fi

tmux new-session -d -s "$SESSION" -n "${TASKS[0]}"
tmux send-keys -t "$SESSION:0" "$SCRIPT ${TASKS[0]}" C-m

for ((i = 1; i < ${#TASKS[@]}; i++)); do
  tmux new-window -t "$SESSION" -n "${TASKS[$i]}"
  tmux send-keys -t "$SESSION:$i" "$SCRIPT ${TASKS[$i]}" C-m
done

echo "Launched tmux session: $SESSION"
echo "Attach: tmux attach -t $SESSION"
