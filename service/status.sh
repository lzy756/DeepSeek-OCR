#!/bin/bash
# DeepSeek-OCR API Service Status Checker

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SERVICE_NAME="deepseek-ocr-api"
API_URL="http://localhost:8000"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DeepSeek-OCR API Service Status${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if service is installed
if [ ! -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
    echo -e "${RED}❌ Service not installed${NC}"
    echo -e "${YELLOW}   Run: sudo bash service/install.sh${NC}"
    exit 1
fi

# Get service status
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${GREEN}✅ Service Status: RUNNING${NC}"
else
    echo -e "${RED}❌ Service Status: STOPPED${NC}"
fi

# Check if enabled
if systemctl is-enabled --quiet ${SERVICE_NAME} 2>/dev/null; then
    echo -e "${GREEN}✅ Auto-start: ENABLED${NC}"
else
    echo -e "${YELLOW}⚠️  Auto-start: DISABLED${NC}"
fi

echo ""

# Show service information
echo -e "${CYAN}Service Information:${NC}"
systemctl show ${SERVICE_NAME} --no-pager | grep -E "^(MainPID|ActiveState|SubState|LoadState|UnitFileState|ExecMainStartTimestamp)" | while IFS='=' read -r key value; do
    case $key in
        MainPID)
            if [ "$value" != "0" ]; then
                echo -e "  Process ID: ${GREEN}${value}${NC}"
            fi
            ;;
        ActiveState)
            if [ "$value" == "active" ]; then
                echo -e "  Active State: ${GREEN}${value}${NC}"
            else
                echo -e "  Active State: ${RED}${value}${NC}"
            fi
            ;;
        SubState)
            echo -e "  Sub State: ${YELLOW}${value}${NC}"
            ;;
        LoadState)
            echo -e "  Load State: ${CYAN}${value}${NC}"
            ;;
        UnitFileState)
            echo -e "  Unit File State: ${CYAN}${value}${NC}"
            ;;
        ExecMainStartTimestamp)
            if [ -n "$value" ]; then
                echo -e "  Started: ${CYAN}${value}${NC}"
            fi
            ;;
    esac
done

echo ""

# Check API health
echo -e "${CYAN}API Health Check:${NC}"
if systemctl is-active --quiet ${SERVICE_NAME}; then
    HEALTH_RESPONSE=$(curl -s "${API_URL}/health" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✅ API is responding${NC}"
        echo -e "  Response: ${CYAN}${HEALTH_RESPONSE}${NC}"
    else
        echo -e "  ${RED}❌ API not responding${NC}"
        echo -e "  ${YELLOW}Service may still be starting...${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  Service not running${NC}"
fi

echo ""
echo -e "${CYAN}Recent Logs (last 10 lines):${NC}"
echo -e "${YELLOW}────────────────────────────────────────${NC}"
journalctl -u ${SERVICE_NAME} -n 10 --no-pager --no-hostname
echo -e "${YELLOW}────────────────────────────────────────${NC}"

echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo -e "  Full logs:       ${YELLOW}sudo journalctl -u ${SERVICE_NAME} -f${NC}"
echo -e "  Restart service: ${YELLOW}sudo systemctl restart ${SERVICE_NAME}${NC}"
echo -e "  Stop service:    ${YELLOW}sudo systemctl stop ${SERVICE_NAME}${NC}"
echo -e "  Start service:   ${YELLOW}sudo systemctl start ${SERVICE_NAME}${NC}"
echo -e "  API docs:        ${YELLOW}${API_URL}/docs${NC}"
echo ""
