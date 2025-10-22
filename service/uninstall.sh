#!/bin/bash
# DeepSeek-OCR API Service Uninstallation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_FILE="deepseek-ocr-api.service"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DeepSeek-OCR API Service Uninstaller${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if service exists
if [ ! -f "/etc/systemd/system/${SERVICE_FILE}" ]; then
    echo -e "${YELLOW}⚠️  Service not installed${NC}"
    exit 0
fi

# Stop service if running
if systemctl is-active --quiet deepseek-ocr-api; then
    echo -e "${YELLOW}⏸  Stopping service...${NC}"
    systemctl stop deepseek-ocr-api
fi

# Disable service
if systemctl is-enabled --quiet deepseek-ocr-api 2>/dev/null; then
    echo -e "${YELLOW}🔓 Disabling service...${NC}"
    systemctl disable deepseek-ocr-api
fi

# Remove service file
echo -e "${GREEN}🗑  Removing service file...${NC}"
rm -f /etc/systemd/system/${SERVICE_FILE}

# Remove environment symlink
if [ -L /etc/deepseek-ocr.env ]; then
    echo -e "${GREEN}🗑  Removing environment symlink...${NC}"
    rm -f /etc/deepseek-ocr.env
fi

# Reload systemd
echo -e "${GREEN}🔄 Reloading systemd daemon...${NC}"
systemctl daemon-reload
systemctl reset-failed

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Uninstallation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Note: Project files remain at /root/DeepSeek-OCR${NC}"
echo ""
