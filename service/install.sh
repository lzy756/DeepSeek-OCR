#!/bin/bash
# DeepSeek-OCR API Service Installation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="/root/DeepSeek-OCR"
SERVICE_DIR="${PROJECT_ROOT}/service"
SERVICE_FILE="deepseek-ocr-api.service"
ENV_FILE="deepseek-ocr.env"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DeepSeek-OCR API Service Installer${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Check if service files exist
if [ ! -f "${SERVICE_DIR}/${SERVICE_FILE}" ]; then
    echo -e "${RED}❌ Service file not found: ${SERVICE_DIR}/${SERVICE_FILE}${NC}"
    exit 1
fi

if [ ! -f "${SERVICE_DIR}/${ENV_FILE}" ]; then
    echo -e "${RED}❌ Environment file not found: ${SERVICE_DIR}/${ENV_FILE}${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found at ${PROJECT_ROOT}/.venv${NC}"
    echo -e "${YELLOW}   Please create it first:${NC}"
    echo -e "${YELLOW}   python3 -m venv .venv${NC}"
    echo -e "${YELLOW}   source .venv/bin/activate${NC}"
    echo -e "${YELLOW}   pip install -r requirements.txt${NC}"
    exit 1
fi

# Check if model directory exists
if [ ! -d "${PROJECT_ROOT}/deepseek_ocr" ]; then
    echo -e "${YELLOW}⚠️  Model directory not found: ${PROJECT_ROOT}/deepseek_ocr${NC}"
    echo -e "${YELLOW}   Please ensure the model is downloaded and extracted${NC}"
    exit 1
fi

# Stop existing service if running
if systemctl is-active --quiet deepseek-ocr-api; then
    echo -e "${YELLOW}⏸  Stopping existing service...${NC}"
    systemctl stop deepseek-ocr-api
fi

# Copy service file to systemd
echo -e "${GREEN}📋 Installing service file...${NC}"
cp "${SERVICE_DIR}/${SERVICE_FILE}" /etc/systemd/system/

# Set correct permissions
chmod 644 /etc/systemd/system/${SERVICE_FILE}

# Create symlink for environment file (easier to edit)
echo -e "${GREEN}🔗 Linking environment file...${NC}"
if [ -f /etc/deepseek-ocr.env ]; then
    rm -f /etc/deepseek-ocr.env
fi
ln -sf "${SERVICE_DIR}/${ENV_FILE}" /etc/deepseek-ocr.env

# Reload systemd
echo -e "${GREEN}🔄 Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Enable service to start on boot
echo -e "${GREEN}✅ Enabling service to start on boot...${NC}"
systemctl enable ${SERVICE_FILE}

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Service Commands:${NC}"
echo -e "  Start service:   ${YELLOW}sudo systemctl start deepseek-ocr-api${NC}"
echo -e "  Stop service:    ${YELLOW}sudo systemctl stop deepseek-ocr-api${NC}"
echo -e "  Restart service: ${YELLOW}sudo systemctl restart deepseek-ocr-api${NC}"
echo -e "  Check status:    ${YELLOW}sudo systemctl status deepseek-ocr-api${NC}"
echo -e "  View logs:       ${YELLOW}sudo journalctl -u deepseek-ocr-api -f${NC}"
echo -e "  Disable service: ${YELLOW}sudo systemctl disable deepseek-ocr-api${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo -e "  Edit settings:   ${YELLOW}nano ${SERVICE_DIR}/${ENV_FILE}${NC}"
echo -e "  After editing:   ${YELLOW}sudo systemctl restart deepseek-ocr-api${NC}"
echo ""
echo -e "${YELLOW}💡 Next steps:${NC}"
echo -e "  1. Review/edit configuration: ${SERVICE_DIR}/${ENV_FILE}"
echo -e "  2. Start the service: sudo systemctl start deepseek-ocr-api"
echo -e "  3. Check status: sudo systemctl status deepseek-ocr-api"
echo -e "  4. View API docs: http://localhost:8000/docs"
echo ""
