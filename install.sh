#!/bin/bash
set -e

TAR=tar
PYTHON=python

INSTALL_DIR="/usr/local/bin/dragonfly_backup"
CONFIG_FILE="/etc/dragonfly_backup.config"
SERVICE_FILE="/etc/systemd/system/dragonfly_backupd.service"
TIMER_FILE="/etc/systemd/system/dragonfly_backupd.timer"

if ! command -v $TAR 2>&1 >/dev/null
then
    echo " Could not find tar and had to quit. Please install it."
    exit 1
fi

tar_version=$($TAR --version | awk 'NR==1{print $4}')
echo "-Found tar version $tar_version"

if ! command -v $PYTHON 2>&1 >/dev/null
then
    echo " Could not find python and had to quit. Please install it."
    exit 1
fi

python_version=$($PYTHON --version | awk '{print $2}')
echo "-Found python version $python_version"

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or use sudo. Will quit for now."
    exit 1
fi

echo "-Installing backup script..."
mkdir -p $INSTALL_DIR
cp dragonfly_backup.py $INSTALL_DIR
chmod +x $INSTALL_DIR/dragonfly_backup.py
mkdir -p /var/log/dragonfly_backup
chmod 750 /var/log/dragonfly_backup

echo "-Copying config file..."
if [ ! -f $CONFIG_FILE ]; then
    cp dragonfly_backup.config $CONFIG_FILE
else
    echo "Config file found. Skipping."
fi

echo "-Installing systemd service and timer."
cp systemd_timer/dragonfly_backupd.service $SERVICE_FILE
cp systemd_timer/dragonfly_backupd.timer $TIMER_FILE

echo "-Reloading systemd daemon."
systemctl daemon-reload

echo "-Enabling and starting backup timer."
systemctl enable dragonfly_backupd.timer
systemctl start dragonfly_backupd.timer

echo "Installation complete. Did you know - dragonflies can fly backwards?"
echo "Please review configuration at '/etc/dragonfly_backup.config' to set up what files to backup up and where."

