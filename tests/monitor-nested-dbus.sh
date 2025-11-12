#!/bin/bash
# Monitor D-Bus signals in the nested session

export DBUS_SESSION_BUS_ADDRESS="unix:path=/tmp/dbus-T43UvcToU7,guid=204a5b0c354d99d73413611a6910bda9"

echo "Monitoring D-Bus signals on org.gnome.henzai..."
echo "Send a message in the nested shell to see signals"
echo ""

dbus-monitor --session "type='signal',sender='org.gnome.henzai'"




