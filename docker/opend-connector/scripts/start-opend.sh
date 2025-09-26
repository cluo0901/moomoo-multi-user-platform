#!/bin/bash
set -e

# Start OpenD Script for Containerized Environment
# This script configures and starts the real moomoo OpenD binary

echo "=========================================="
echo "Starting OpenD for User: ${USER_ID}"
echo "=========================================="

# Set default values
export MOOMOO_USERNAME=${MOOMOO_USERNAME:-""}
export MOOMOO_PASSWORD=${MOOMOO_PASSWORD:-""}
export SECURITY_FIRM=${SECURITY_FIRM:-"FUTUSG"}
export TRADE_MARKET=${TRADE_MARKET:-"US"}
export TRADE_ENV=${TRADE_ENV:-"1"}
export LOG_LEVEL=${LOG_LEVEL:-"info"}
export TIME_ZONE=${TIME_ZONE:-"America/New_York"}

# Validate required credentials
if [ -z "$MOOMOO_USERNAME" ] || [ -z "$MOOMOO_PASSWORD" ]; then
    echo "ERROR: MOOMOO_USERNAME and MOOMOO_PASSWORD environment variables are required"
    exit 1
fi

echo "Configuration:"
echo "- Username: ${MOOMOO_USERNAME}"
echo "- Security Firm: ${SECURITY_FIRM}"
echo "- Trade Market: ${TRADE_MARKET}"
echo "- Trade Environment: ${TRADE_ENV}"
echo "- Log Level: ${LOG_LEVEL}"

# Check if real OpenD binary exists
OPEND_BINARY="/app/opend/OpenD"
OPEND_STATUS_FILE="/app/opend/binary_status"

if [ -f "$OPEND_STATUS_FILE" ]; then
    BINARY_STATUS=$(cat "$OPEND_STATUS_FILE")
    if [ "$BINARY_STATUS" = "PLACEHOLDER_BINARY=true" ]; then
        echo "WARNING: Using placeholder OpenD binary"
        echo "For production, download real OpenD from: https://www.moomoo.com/us/support/topic3_441"
        echo "Replace placeholder binary with real OpenD binary and Appdata.dat"
    fi
fi

# Generate OpenD configuration from template
echo "Generating OpenD.xml configuration..."
envsubst < /app/templates/OpenD.xml.template > /app/config/OpenD.xml

# Check if OpenD.xml was generated successfully
if [ ! -f "/app/config/OpenD.xml" ]; then
    echo "ERROR: Failed to generate OpenD.xml configuration file"
    exit 1
fi

echo "OpenD.xml generated successfully"

# Change to OpenD directory
cd /app/opend

# Check for required data file
if [ ! -f "./Appdata.dat" ]; then
    echo "WARNING: Appdata.dat not found - this may cause startup issues"
    echo "For production, ensure Appdata.dat is available from official OpenD package"
    # Create placeholder for development
    echo "PLACEHOLDER_APPDATA" > ./Appdata.dat
fi

# Set executable permissions
chmod +x "$OPEND_BINARY"

# Start OpenD with command line parameters
echo "Starting OpenD binary..."
echo "Command: $OPEND_BINARY -login_account=${MOOMOO_USERNAME} -login_pwd=${MOOMOO_PASSWORD} -lang=en"

# Execute OpenD binary
exec "$OPEND_BINARY" \
    -login_account="${MOOMOO_USERNAME}" \
    -login_pwd="${MOOMOO_PASSWORD}" \
    -lang=en \
    2>&1 | tee /app/logs/opend.log