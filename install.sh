#!/usr/bin/env bash
# Symlink this repo's files into place, so edits in either location are the
# same file and show up in git.
set -euo pipefail
repo=$(cd "$(dirname "$0")" && pwd)

link() {
  mkdir -p "$(dirname "$2")"
  ln -sfn "$repo/$1" "$2"
  echo "$2 -> $repo/$1"
}

link bin/miniflux-digest              "$HOME/.local/bin/miniflux-digest"
link recipes/miniflux.recipe          "$HOME/.config/miniflux-digest/miniflux.recipe"
link systemd/miniflux-digest.service  "$HOME/.config/systemd/user/miniflux-digest.service"
link systemd/miniflux-digest.timer    "$HOME/.config/systemd/user/miniflux-digest.timer"

systemctl --user daemon-reload
