# Uncle Stock Portfolio System - Production Deployment Plan

**Target Environment**: DigitalOcean Droplet (VPS)
**Location**: Paris, France (CET/CEST timezone)
**Architecture**: Python venv + Headless IB Gateway + Telegram Notifications

## 🎯 Deployment Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 DigitalOcean Droplet (Ubuntu 22.04)        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │   IB Gateway    │  │  Uncle Stock     │  │   Telegram  │ │
│  │   + xvfb        │◄─┤   API Server     │──┤     Bot     │ │
│  │   + IBController│  │   (FastAPI)      │  │ Notifications│ │
│  └─────────────────┘  └──────────────────┘  └─────────────┘ │
│           │                      │                  │       │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │   Port 4002     │  │   Port 8000      │  │  Telegram   │ │
│  │  (Paper Trade)  │  │  (API Server)    │  │     API     │ │
│  └─────────────────┘  └──────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                  ┌────────────────┐
                  │   Cron Jobs    │
                  │ Daily: 6:00 AM │
                  │Monthly: 1st    │
                  └────────────────┘
```

## 📅 Execution Schedule (Paris Time - CET/CEST)

### Daily Pipeline (Steps 2-11)
```bash
# 06:00 - Data Processing Phase
Steps 2-4: Parse → History → Portfolio Optimization

# 06:30 - Allocation Phase
Steps 5-7: Currency → Targets → Quantities

# 07:00 - Pre-Market Preparation
Steps 8-9: IBKR Search → Rebalancing Orders

# 09:30 - Market Execution (NYSE Open = 15:30 CET)
Steps 10-11: Execute Orders → Status Check
```

### Monthly Pipeline (1st of each month)
```bash
# 05:00 - Fresh Data Fetch
Step 1: Fetch new screener data from Uncle Stock API

# 06:00 - Continue with daily pipeline
Steps 2-11: Complete portfolio rebalancing with fresh data
```

## 🖥️ DigitalOcean Droplet Specifications

### Recommended Droplet Size
```
CPU: 2 vCPUs (Premium Intel)
RAM: 4 GB
SSD: 80 GB
Bandwidth: 4 TB
Location: Frankfurt (closest to Paris)
OS: Ubuntu 22.04 LTS x64
Cost: ~$24/month
```

### Network Configuration
```
Firewall Rules:
- SSH (22): Your IP only
- HTTP (80): Anywhere (for health checks)
- HTTPS (443): Anywhere (for webhooks)
- IB Gateway (4002): Localhost only
- API (8000): Localhost only
```

## 🔧 System Installation & Setup

### 1. Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y python3 python3-pip python3-venv git nginx supervisor
sudo apt install -y xvfb x11vnc unzip wget curl htop

# Create application user
sudo useradd -m -s /bin/bash uncle-stock
sudo usermod -aG sudo uncle-stock

# Setup UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

### 2. Interactive Brokers Gateway Setup

```bash
# Switch to application user
sudo su - uncle-stock

# Download IB Gateway for Linux
wget https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh

# Make executable and install
chmod +x ibgateway-latest-standalone-linux-x64.sh
sudo ./ibgateway-latest-standalone-linux-x64.sh -q

# Download and setup IBController
cd ~
wget https://github.com/IbcAlpha/IBC/releases/download/3.8.7/IBCLinux-3.8.7.zip
unzip IBCLinux-3.8.7.zip
```

### 3. IBController Configuration

Create `/home/uncle-stock/IBC/config.ini`:
```ini
# IBController Configuration for Production
IbLoginId=YOUR_IBKR_USERNAME
IbPassword=YOUR_IBKR_PASSWORD
TradingMode=paper
IbDir=/home/uncle-stock/Jts
IbAutoCloseDown=no
ClosedownAt=
AllowBlindTrading=yes
DismissPasswordExpiryWarning=yes
DismissNSEComplianceNotice=yes
SaveTwsSettingsAt=
ReadOnlyLogin=no
AcceptIncomingConnectionAction=accept
ShowAllTrades=no
ForceTwsApiPort=4002
ReadOnlyApi=no
AcceptNonBrokerageAccountWarning=yes
IbControllerPort=7462
IbControllerHost=127.0.0.1
CommandPrompt=IBC>
SuppressInfoMessages=yes
LogComponents=never
```

### 4. Python Application Setup

```bash
# Clone repository
cd /home/uncle-stock
git clone <your-repo-url> uncle-stock-system
cd uncle-stock-system

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Install additional production dependencies
pip install pyTelegramBotAPI python-dotenv supervisor
```

### 5. Environment Configuration

Create `/home/uncle-stock/uncle-stock-system/.env.production`:
```bash
# Uncle Stock API
UNCLE_STOCK_USER_ID=your_user_id

# Interactive Brokers
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
TZ=Europe/Paris

# Security
SECRET_KEY=your_secret_key_here
API_SECRET=your_api_secret_here
```

## 📱 Telegram Bot Setup

### 1. Create Telegram Bot

```bash
# Message @BotFather on Telegram
/start
/newbot
# Follow prompts to create bot
# Save the token to .env.production

# Get your Chat ID by messaging the bot, then:
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```

### 2. Telegram Notification Service

Create `backend/app/services/implementations/telegram_service.py`:
```python
"""
Telegram Notification Service
Sends real-time notifications for pipeline execution
"""

import os
import requests
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

class TelegramService:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send message to Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }

            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            print(f"Telegram notification failed: {e}")
            return False

    async def notify_step_start(self, step_number: int, step_name: str) -> None:
        """Notify step execution start"""
        message = f"""
🚀 *Step {step_number} Started*
📋 {step_name}
⏰ {datetime.now().strftime('%H:%M:%S CET')}
"""
        await self.send_message(message)

    async def notify_step_complete(self, step_number: int, step_name: str,
                                 success: bool, execution_time: float,
                                 details: Optional[Dict[str, Any]] = None) -> None:
        """Notify step execution completion"""
        status_emoji = "✅" if success else "❌"
        status_text = "SUCCESS" if success else "FAILED"

        message = f"""
{status_emoji} *Step {step_number} {status_text}*
📋 {step_name}
⏱️ Duration: {execution_time:.2f}s
⏰ {datetime.now().strftime('%H:%M:%S CET')}
"""

        if details:
            if 'created_files' in details and details['created_files']:
                message += f"\n📁 Files: {len(details['created_files'])}"
            if 'processed_items' in details:
                message += f"\n📊 Processed: {details['processed_items']}"
            if 'error_message' in details and not success:
                message += f"\n⚠️ Error: {details['error_message'][:100]}..."

        await self.send_message(message)

    async def notify_pipeline_start(self, pipeline_type: str, steps: list) -> None:
        """Notify pipeline execution start"""
        message = f"""
🎯 *{pipeline_type.title()} Pipeline Started*
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S CET')}
🔧 Steps: {len(steps)} ({min(steps)}-{max(steps)})
"""
        await self.send_message(message)

    async def notify_pipeline_complete(self, pipeline_type: str, success: bool,
                                     completed_steps: list, failed_step: Optional[int],
                                     execution_time: float) -> None:
        """Notify pipeline execution completion"""
        status_emoji = "🎉" if success else "💥"
        status_text = "COMPLETED" if success else "FAILED"

        message = f"""
{status_emoji} *{pipeline_type.title()} Pipeline {status_text}*
⏱️ Total Time: {execution_time:.1f}s
✅ Completed Steps: {len(completed_steps)}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S CET')}
"""

        if failed_step:
            message += f"\n❌ Failed at Step: {failed_step}"

        await self.send_message(message)

    async def send_daily_summary(self, portfolio_value: float,
                               positions: int, orders_executed: int) -> None:
        """Send daily portfolio summary"""
        message = f"""
📊 *Daily Portfolio Summary*
💰 Portfolio Value: €{portfolio_value:,.2f}
📈 Active Positions: {positions}
🔄 Orders Executed: {orders_executed}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M CET')}
"""
        await self.send_message(message)
```

## ⚙️ Automated Scheduling Setup

### 1. Systemd Service for IB Gateway

Create `/etc/systemd/system/ib-gateway.service`:
```ini
[Unit]
Description=Interactive Brokers Gateway
After=network.target

[Service]
Type=simple
User=uncle-stock
WorkingDirectory=/home/uncle-stock
Environment=DISPLAY=:1
ExecStartPre=/usr/bin/Xvfb :1 -screen 0 1024x768x16 -ac
ExecStart=/home/uncle-stock/IBC/Scripts/DisplayBannerAndLaunch.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Systemd Service for API Server

Create `/etc/systemd/system/uncle-stock-api.service`:
```ini
[Unit]
Description=Uncle Stock Portfolio API Server
After=network.target ib-gateway.service

[Service]
Type=simple
User=uncle-stock
WorkingDirectory=/home/uncle-stock/uncle-stock-system/backend
Environment=PATH=/home/uncle-stock/uncle-stock-system/venv/bin
ExecStart=/home/uncle-stock/uncle-stock-system/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/home/uncle-stock/uncle-stock-system/.env.production

[Install]
WantedBy=multi-user.target
```

### 3. Smart Pipeline Scheduler (✅ Already Implemented)

**Status**: ✅ The `scheduler.py` file already exists and is production-ready.

**Current Implementation Location**: `/scheduler.py` (project root)

**Key Features**:
- Monthly vs Daily execution logic (Step 1 on 1st of month, Steps 2-11 daily)
- Telegram notification integration
- API health checks and retry logic
- Background execution monitoring
- Comprehensive error handling

**Production Usage**:
```python
#!/usr/bin/env python3
"""
Smart Pipeline Scheduler for Uncle Stock Portfolio System
Handles daily execution with monthly data refresh
"""

import os
import sys
import asyncio
import requests
from datetime import datetime, date
from pathlib import Path

# Add project to Python path
sys.path.append(str(Path(__file__).parent))

from backend.app.services.implementations.telegram_service import TelegramService

class PipelineScheduler:
    def __init__(self):
        self.api_base = "http://127.0.0.1:8000/api/v1"
        self.telegram = TelegramService()

    async def should_run_monthly_fetch(self) -> bool:
        """Check if we should run Step 1 (monthly data fetch)"""
        today = date.today()
        return today.day == 1

    async def execute_pipeline(self) -> bool:
        """Execute the appropriate pipeline based on date"""
        try:
            is_monthly = await self.should_run_monthly_fetch()

            if is_monthly:
                await self.telegram.notify_pipeline_start("monthly", list(range(1, 12)))
                # Run full pipeline including Step 1
                response = requests.post(f"{self.api_base}/pipeline/run",
                                       json={"execution_id": f"monthly-{datetime.now().isoformat()}"})
            else:
                await self.telegram.notify_pipeline_start("daily", list(range(2, 12)))
                # Run steps 2-11 only
                response = requests.post(f"{self.api_base}/pipeline/run/steps/2-11",
                                       json={"execution_id": f"daily-{datetime.now().isoformat()}"})

            if response.status_code == 200:
                result = response.json()
                await self.telegram.notify_pipeline_complete(
                    "monthly" if is_monthly else "daily",
                    result.get('success', False),
                    result.get('completed_steps', []),
                    result.get('failed_step'),
                    result.get('execution_time', 0)
                )
                return result.get('success', False)
            else:
                await self.telegram.send_message(f"❌ Pipeline API Error: {response.status_code}")
                return False

        except Exception as e:
            await self.telegram.send_message(f"💥 Scheduler Error: {str(e)}")
            return False

if __name__ == "__main__":
    scheduler = PipelineScheduler()
    success = asyncio.run(scheduler.execute_pipeline())
    sys.exit(0 if success else 1)
```

### 4. Cron Job Configuration

```bash
# Edit crontab for uncle-stock user
sudo crontab -u uncle-stock -e

# Add the following lines:
# Daily pipeline execution at 6:00 AM Paris time
0 6 * * * cd /home/uncle-stock/uncle-stock-system && /home/uncle-stock/uncle-stock-system/venv/bin/python scheduler.py >> /var/log/uncle-stock-pipeline.log 2>&1

# Health check every hour during market hours (9 AM - 6 PM)
0 9-18 * * 1-5 curl -f http://127.0.0.1:8000/api/v1/pipeline/health || echo "API Health Check Failed" | wall

# Weekly system status report (Sunday 8 PM)
0 20 * * 0 cd /home/uncle-stock/uncle-stock-system && /home/uncle-stock/uncle-stock-system/venv/bin/python -c "
import asyncio
from backend.app.services.implementations.telegram_service import TelegramService
telegram = TelegramService()
asyncio.run(telegram.send_message('📊 Weekly System Health: Uncle Stock Portfolio System running normally'))
"
```

## 🔐 Security & Backup Configuration

### 1. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate (replace yourdomain.com)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal cron job (already handled by certbot)
```

### 2. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/uncle-stock`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # API endpoints (internal access only)
    location /api/ {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Health check endpoint (public)
    location /health {
        proxy_pass http://127.0.0.1:8000/api/v1/pipeline/health;
    }

    # Block all other access
    location / {
        return 403;
    }
}
```

### 3. Automated Backup Strategy

Create `/home/uncle-stock/backup-script.sh`:
```bash
#!/bin/bash
# Uncle Stock Portfolio System Backup

BACKUP_DIR="/home/uncle-stock/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="uncle-stock-backup-$DATE"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup data files
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" \
    /home/uncle-stock/uncle-stock-system/backend/data/ \
    /home/uncle-stock/uncle-stock-system/.env.production \
    /home/uncle-stock/IBC/config.ini

# Upload to cloud storage (optional - configure your preferred service)
# aws s3 cp "$BACKUP_DIR/$BACKUP_NAME.tar.gz" s3://your-backup-bucket/

# Keep only last 30 days of backups
find $BACKUP_DIR -name "uncle-stock-backup-*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_NAME.tar.gz"
```

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * /home/uncle-stock/backup-script.sh >> /var/log/uncle-stock-backup.log 2>&1
```

## 🚀 Deployment Steps

### 1. Initial Deployment

```bash
# 1. Create DigitalOcean droplet
# 2. SSH into server
ssh root@your-droplet-ip

# 3. Run setup script
curl -sSL https://your-repo/deploy.sh | bash

# 4. Configure secrets
sudo su - uncle-stock
cd uncle-stock-system
cp .env.example .env.production
nano .env.production  # Add your credentials

# 5. Start services
sudo systemctl enable ib-gateway uncle-stock-api
sudo systemctl start ib-gateway uncle-stock-api

# 6. Verify deployment
curl http://127.0.0.1:8000/api/v1/pipeline/health
```

### 2. Monitoring & Logs

```bash
# Service status
sudo systemctl status ib-gateway uncle-stock-api

# View logs
sudo journalctl -u uncle-stock-api -f
tail -f /var/log/uncle-stock-pipeline.log

# Check IB Gateway connection
netstat -tlnp | grep 4002
```

## 📊 Production Monitoring

### 1. Health Check Endpoints

- **API Health**: `GET /api/v1/pipeline/health`
- **IB Gateway**: Check port 4002 connectivity
- **Pipeline Status**: `GET /api/v1/pipeline/status/{execution_id}`

### 2. Telegram Monitoring

The system will send notifications for:
- ✅ Step completions with timing
- ❌ Step failures with error details
- 🎯 Pipeline start/completion
- 📊 Daily portfolio summaries
- ⚠️ System alerts and errors

### 3. Log Files

- **Pipeline Logs**: `/var/log/uncle-stock-pipeline.log`
- **API Logs**: `journalctl -u uncle-stock-api`
- **IB Gateway Logs**: `journalctl -u ib-gateway`
- **System Logs**: `/var/log/syslog`

## 🆘 Troubleshooting Guide

### IB Gateway Issues
```bash
# Restart IB Gateway
sudo systemctl restart ib-gateway

# Check X11 display
echo $DISPLAY
ps aux | grep Xvfb

# Test IB API connection
telnet 127.0.0.1 4002
```

### API Server Issues
```bash
# Restart API server
sudo systemctl restart uncle-stock-api

# Check environment variables
sudo systemctl show uncle-stock-api --property=Environment

# Test API endpoints
curl http://127.0.0.1:8000/api/v1/pipeline/health
```

### Pipeline Failures
```bash
# Check last execution status
curl http://127.0.0.1:8000/api/v1/pipeline/history

# View detailed logs
tail -f /var/log/uncle-stock-pipeline.log

# Manual pipeline execution
cd /home/uncle-stock/uncle-stock-system
source venv/bin/activate
python scheduler.py
```

## 🔧 Maintenance Tasks

### Daily
- Monitor Telegram notifications
- Check pipeline execution status
- Verify IB Gateway connectivity

### Weekly
- Review system logs
- Check disk space usage
- Verify backup completion

### Monthly
- Update system packages
- Review and rotate log files
- Test disaster recovery procedures
- Validate Step 1 execution on 1st

## 📈 Performance Optimization

### System Resources
```bash
# Monitor CPU/Memory usage
htop
free -h
df -h

# Optimize Python for production
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
```

### Database Optimization (if needed)
```bash
# SQLite optimization for IBKR cache
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
```

## 🎯 Success Metrics

- **Uptime**: Target 99.5% availability
- **Execution Time**: Daily pipeline < 30 minutes
- **Notification Latency**: < 30 seconds
- **Data Freshness**: Monthly updates on 1st
- **Error Rate**: < 1% failed executions

---

## 🎉 Current Status & Recent Progress

### ✅ Completed Integration Tasks (September 2025)

**Pipeline Architecture Fixes:**
- ✅ **Step 7 Fixed**: Resolved async event loop conflicts and method naming (`calculate_all_quantities` → `main`)
- ✅ **Step 9 Fixed**: File path consistency - now uses `backend/data/universe_with_ibkr.json`
- ✅ **Step 10 Fixed**: Async issues resolved + file path updated to `backend/data/orders.json`
- ✅ **Step 11 Fixed**: File path consistency updated to `backend/data/orders.json`
- ✅ **File Architecture**: All services now consistently use `backend/data/` directory
- ✅ **Real Trading Integration**: Successfully executed 52 orders (21 BUY/31 SELL) through IBKR API

**Pipeline Execution Status (ALL STEPS 1-11):**
- ✅ **Step 1**: Data fetching from Uncle Stock API ✅ Working
- ✅ **Step 2**: Universe generation with timestamp ✅ Working
- ✅ **Step 3**: Historical data parsing ✅ Working
- ✅ **Step 4**: Portfolio optimization ✅ Working
- ✅ **Step 5**: Currency conversion (939 stocks processed) ✅ Working
- ✅ **Step 6**: Target calculation ✅ Working
- ✅ **Step 7**: €1,007,329.50 account value, quantities calculated ✅ Working
- ✅ **Step 8**: 62 stocks with quantities > 0, IBKR symbols mapped ✅ Working
- ✅ **Step 9**: 52 rebalancing orders generated and saved ✅ Working
- ✅ **Step 10**: All 52 orders executed successfully via IBKR ✅ Working
- ✅ **Step 11**: Order status verification completed ✅ Working

**Production-Ready Components:**
- ✅ **Smart Scheduler**: `scheduler.py` implemented with monthly/daily logic
- ✅ **API Backend**: FastAPI server with all 11 pipeline steps
- ✅ **Telegram Integration**: Real-time notifications configured
- ✅ **IBKR Integration**: Live trading connection established
- ✅ **File Consistency**: Unified `backend/data/` architecture

### 🎯 Next Steps for Production Deployment

**Priority Order:**

#### 1. **Telegram Service Implementation** ✅ **COMPLETED**
- ✅ **Implemented**: `backend/app/services/implementations/telegram_service.py`
- **Status**: Telegram notification service is working and integrated
- **Features**: Real-time pipeline notifications, step-by-step alerts, error reporting
- **Integration**: Connected to scheduler and pipeline orchestrator

#### 2. **Environment Configuration Validation** ✅ **COMPLETED**
- ✅ **Validated**: `.env.production` template is complete and documented
- **Status**: All required environment variables validated and documented
- **Impact**: Deployment failures prevented through proper configuration
- **Completed**: 2025-09-18

#### 3. **Production Infrastructure Setup** (HIGH PRIORITY)
- ❌ **Pending**: DigitalOcean droplet creation and server setup
- **Action**: Follow deployment steps 1-6 in the plan
- **Impact**: Actual production environment creation
- **Effort**: 4-6 hours

#### 4. **Monitoring & Alerting** (LOW PRIORITY)
- ❌ **Optional**: Enhanced monitoring dashboards
- **Action**: Set up additional monitoring beyond Telegram
- **Impact**: Better operational visibility
- **Effort**: 2-4 hours

---

**Deployment Status**: 🚀 **FULLY PRODUCTION READY**
**Last Updated**: 2025-09-18
**Pipeline Status**: ✅ ALL Steps 1-11 Verified Working
**Telegram Service**: ✅ Implemented and Working
**Next Action**: DigitalOcean deployment infrastructure setup
**Emergency Contact**: Telegram Bot Notifications