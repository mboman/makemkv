#!/bin/bash

# Run makemkvcon in headless mode to rip DVDs or Blu-rays.
# https://github.com/mboman/makemkv/blob/master/bin/rip.sh
# Save as (chmod +x): /rip.sh

set -E  # Call ERR traps when using -e.
set -e  # Exit script if a command fails.
set -u  # Treat unset variables as errors and exit immediately.
set -o pipefail  # Exit script if pipes fail instead of just the last program.

# Source function library.
source /env.sh
hook post-env

# Print environment.
if [ "$DEBUG" == "true" ]; then
    set -x  # Print command traces before executing command.
    env |sort
fi

# Verify the device.
if [ -z "$DEVNAME" ]; then
    echo -e "\nERROR: Unable to find optical device.\n" >&2
    exit 1
fi
if [ ! -b "$DEVNAME" ]; then
    echo -e "\nERROR: Device $DEVNAME not a block-special file.\n" >&2
    exit 1
fi

# Setup trap for hooks and FAILED_EJECT.
trap "hook pre-on-err; on_err; hook post-on-err; wait" ERR

# Prepare the environment before ripping.
hook pre-prepare
prepare
hook post-prepare

# Rip media.
echo "Ripping..."
hook pre-rip
run_makemkvcon &
makemkvcon_pid=$!
timeout 5 bash -c "until [ -e /tmp/titles_done ]; do sleep 0.1; done"
export TITLE_PATH
while read -rd $'\0' TITLE_PATH; do
    if [ "$TITLE_PATH" == "fini" ]; then
        break
    elif [ "$TITLE_PATH" == "init" ]; then
        continue
    else
        hook post-title
    fi
done < /tmp/titles_done
unset TITLE_PATH
wait ${makemkvcon_pid}
hook post-rip
move_back

# Eject.
if [ "$NO_EJECT" != "true" ]; then
    hook pre-success-eject
    echo "Ejecting..."
    eject "$DEVNAME"
    hook post-success-eject
fi

hook end
wait
echo Done after $(date -u -d @$SECONDS +%T) with $(basename "$DIR_FINAL")
