#!/bin/sh
# Install (or upgrade) the Gas City job runner as a persistent user service (runner r4).
# Run it ONCE, from a real WSL terminal, as loucmane:
#   sh <J>/operator/INSTALL.sh <reviewed commit>
#
# What it does, in order. It stops at the first failed check, before anything changes.
#  1. Checks that the ga-e0t1 worktree is clean at <commit>, and that <commit> carries a good signature
#     from primary key 7720D1FE.
#  2. Copies jobrunner.py, source-launch.py and gcjobs out of the git objects of <commit> into
#     ~/.local/share/gas-city-jobrunner/<commit>/ (read-only). Each digest must match the pins below.
#     The service runs these copies, so later commits in the worktree never change the running code.
#  3. Stops the transient gas-city-jobrunner if it is running. A job it started keeps its own
#     gc-job-* unit.
#  4. Writes ~/.config/systemd/user/gas-city-jobrunner.service and installs ~/.local/bin/gcjobs.
#  5. Runs daemon-reload, then enable --now. With linger enabled, the service then starts at every WSL
#     boot. Finally it prints gcjobs.
# Uninstall: systemctl --user disable --now gas-city-jobrunner
#            rm ~/.config/systemd/user/gas-city-jobrunner.service ~/.local/bin/gcjobs
#            systemctl --user daemon-reload
set -eu
COMMIT=${1:?usage: INSTALL.sh <reviewed commit>}
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
RUNNER_SHA=0c493db2872c8a44b729376b9d2bcdd2f33fe2d913f2e82c15096dfe0cce9b71
GCJOBS_SHA=7a3180ea5f74de7e4b8cecb9f28f411d44263fd5c3b728005d4d90118f64b863
LAUNCH_SHA=31bdeea83152c5ad0253a74d743f4d4d103dc7e14e7975da00055df6786d6dea
SIGNER=7720D1FE503A88EDECA61A6F0C7D823543E01875
MARK='# managed by gct-jobrunner operator/INSTALL.sh'
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
stop() { echo "INSTALL STOPPED: $*" >&2; exit 1; }
g() { git -c core.fsmonitor=false -c core.hooksPath=/dev/null -c gpg.program=/usr/bin/gpg -C "$W" "$@"; }

[ "$(id -u)" = 1000 ] || stop "run as loucmane (uid 1000)"
case "$COMMIT" in (*[!0-9a-f]*|'') stop "commit must be 40 lowercase hex characters";; esac
[ "${#COMMIT}" = 40 ] || stop "commit must be 40 lowercase hex characters"
[ "$(g rev-parse HEAD)" = "$COMMIT" ] || stop "the worktree HEAD is not $COMMIT"
[ -z "$(g --no-optional-locks status --porcelain --untracked-files=all)" ] || stop "the worktree is not clean"
g verify-commit --raw "$COMMIT" 2>&1 | grep -q "^\[GNUPG:\] VALIDSIG .* $SIGNER\$" || stop "no good signature from $SIGNER"

DEST=$HOME/.local/share/gas-city-jobrunner/$COMMIT
mkdir -p "$HOME/.local/share/gas-city-jobrunner"
[ ! -L "$HOME/.local/share/gas-city-jobrunner" ] || stop "the install root is a symlink"
extract() { # extract <repo path> <file name> <sha256>
  if [ -e "$DEST/$2" ]; then
    [ "$(sha256sum < "$DEST/$2" | cut -c1-64)" = "$3" ] || stop "$DEST/$2 exists with other bytes"
    return 0
  fi
  g show "$COMMIT:$D/$1" > "$DEST/.$2.tmp"
  [ "$(sha256sum < "$DEST/.$2.tmp" | cut -c1-64)" = "$3" ] || stop "$1 at $COMMIT does not match its pin"
  chmod 0444 "$DEST/.$2.tmp"
  mv "$DEST/.$2.tmp" "$DEST/$2"
}
mkdir -p -m 0700 "$DEST"
[ ! -L "$DEST" ] || stop "$DEST is a symlink"
extract gct-jobrunner/jobrunner.py jobrunner.py "$RUNNER_SHA"
extract gct-m1wh-p6/source-launch.py source-launch.py "$LAUNCH_SHA"
extract gct-jobrunner/gcjobs.py gcjobs "$GCJOBS_SHA"

UNIT=$HOME/.config/systemd/user/gas-city-jobrunner.service
BIN=$HOME/.local/bin/gcjobs
if [ -e "$UNIT" ] || [ -L "$UNIT" ]; then
  [ ! -L "$UNIT" ] && grep -qxF "$MARK" "$UNIT" || stop "$UNIT exists and was not written by this installer"
fi
if [ -e "$BIN" ] || [ -L "$BIN" ]; then
  [ ! -L "$BIN" ] && grep -q '^# gas-city-jobrunner status' "$BIN" || stop "$BIN exists and is not gcjobs"
fi

# Stop whichever runner is active (the transient one from JOBRUNNER.sh, or an older install).
if systemctl --user is-active --quiet gas-city-jobrunner.service; then
  systemctl --user stop gas-city-jobrunner.service
fi
for i in 1 2 3 4 5 6 7 8 9 10; do
  systemctl --user is-active --quiet gas-city-jobrunner.service || break
  sleep 1
done
! systemctl --user is-active --quiet gas-city-jobrunner.service || stop "the running job runner did not stop"

mkdir -p "$HOME/.config/systemd/user" "$HOME/.local/bin"
cat > "$UNIT.tmp" <<UNITFILE
$MARK
# Reviewed commit $COMMIT; runner sha256 $RUNNER_SHA.
[Unit]
Description=Gas City reviewed job runner ($(echo "$COMMIT" | cut -c1-8))
Documentation=file://$W/$D/gct-jobrunner/README.md

[Service]
Type=simple
Slice=app.slice
UMask=0022
ExecStart=/usr/bin/python3 -I -S -B $DEST/source-launch.py $DEST/jobrunner.py $RUNNER_SHA
Restart=on-failure
RestartSec=30
RestartPreventExitStatus=2 3

[Install]
WantedBy=default.target
UNITFILE
mv "$UNIT.tmp" "$UNIT"
install -m 0755 "$DEST/gcjobs" "$BIN.tmp"
mv "$BIN.tmp" "$BIN"

systemctl --user daemon-reload
systemctl --user enable --now gas-city-jobrunner.service
sleep 3
systemctl --user is-active --quiet gas-city-jobrunner.service || { journalctl --user -u gas-city-jobrunner -n 20 --no-pager; stop "the service did not stay up"; }
echo "INSTALLED: gas-city-jobrunner runs $COMMIT and starts at every WSL boot."
"$BIN"
