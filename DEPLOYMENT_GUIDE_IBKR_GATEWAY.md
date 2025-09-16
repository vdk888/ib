# IBKR Gateway Deployment Guide - Digital Ocean Droplet

Complete guide for deploying automated trading application with Interactive Brokers Gateway on Digital Ocean droplet.

## Overview

This guide sets up a production-ready automated trading system with:
- **Your FastAPI trading app** (portfolio optimization, screening, execution)
- **IBKR Gateway in Docker** with VNC remote access
- **Headless operation** with remote authentication capability
- **Production security** and monitoring

## Architecture

```
Digital Ocean Droplet
├── uncle-stock-api (Your FastAPI app)
│   ├── Portfolio optimization
│   ├── Stock screening
│   └── Order execution
├── ib-gateway (IBKR Gateway + VNC)
│   ├── API ports: 4001/4002
│   └── VNC port: 5900
└── nginx (Optional reverse proxy)
```

## Prerequisites

- Digital Ocean account
- Interactive Brokers account (paper or live)
- VNC client (TigerVNC, RealVNC, or built-in)
- Basic Docker knowledge

## Step 1: Provision Digital Ocean Droplet

### Recommended Specifications
- **Size**: 4GB RAM / 2 CPU ($24/month)
- **OS**: Ubuntu 24.04 LTS x64
- **Options**: Docker One-Click App
- **Storage**: 80GB SSD
- **Authentication**: SSH key (not password)

### Create Droplet
```bash
# Using doctl CLI (optional)
doctl compute droplet create trading-bot \
  --image docker-20-04 \
  --size s-2vcpu-4gb \
  --region nyc1 \
  --ssh-keys your_ssh_key_fingerprint
```

## Step 2: Initial Server Setup

### Connect and Update
```bash
ssh root@your_droplet_ip
apt update && apt upgrade -y
```

### Install Docker Compose (if not present)
```bash
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### Setup Firewall
```bash
ufw allow 22      # SSH
ufw allow 8000    # Your API
# ufw allow 5900  # VNC - Use SSH tunnel instead
ufw --force enable
```

## Step 3: Deploy Your Application

### Clone Repository
```bash
git clone your_repository_url
cd your_repository_name
```

### Create Production docker-compose.yml

```yaml
version: '3.8'

services:
  uncle-stock-api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - UNCLE_STOCK_USER_ID=${UNCLE_STOCK_USER_ID}
      - IBKR_HOST=ib-gateway
      - IBKR_PORT=${IBKR_PORT:-4002}
      - IBKR_CLIENT_ID=${IBKR_CLIENT_ID:-1}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - ENVIRONMENT=production
      - DEBUG=false
      - PORTFOLIO_MAX_RANKED_STOCKS=${PORTFOLIO_MAX_RANKED_STOCKS:-30}
      - PORTFOLIO_MAX_ALLOCATION=${PORTFOLIO_MAX_ALLOCATION:-0.10}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    depends_on:
      - ib-gateway
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - trading-network

  # IBKR Gateway with VNC for remote access
  ib-gateway:
    image: gnzsnz/ib-gateway:latest
    environment:
      - TWS_USERID=${IBKR_USERNAME}
      - TWS_PASSWORD=${IBKR_PASSWORD}
      - TRADING_MODE=${TRADING_MODE:-paper}
      - VNC_SERVER_PASSWORD=${VNC_PASSWORD}
      - DISPLAY=:0
      - TZ=America/New_York
    ports:
      - "4001:4001"  # Live trading API
      - "4002:4002"  # Paper trading API
      - "5900:5900"  # VNC server
      - "6080:6080"  # Web VNC (if available)
    volumes:
      - ./ibkr-settings:/root/Jts
      - ./ibkr-logs:/root/IBGateway/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "netstat -an | grep -q :4002"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - trading-network

  # Optional: Redis for caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    networks:
      - trading-network
    profiles:
      - with-redis

  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - uncle-stock-api
    restart: unless-stopped
    networks:
      - trading-network
    profiles:
      - with-proxy

networks:
  trading-network:
    driver: bridge

volumes:
  redis-data:
```

### Create Environment File

```bash
cat > .env << 'EOF'
# IBKR Credentials - SECURE THESE!
IBKR_USERNAME=your_ib_username
IBKR_PASSWORD=your_ib_password
VNC_PASSWORD=secure_vnc_password

# IBKR Configuration
IBKR_HOST=ib-gateway
IBKR_PORT=4002
IBKR_CLIENT_ID=1
TRADING_MODE=paper

# Uncle Stock API
UNCLE_STOCK_USER_ID=your_user_id

# Application Configuration
LOG_LEVEL=INFO
ENVIRONMENT=production
DEBUG=false

# Portfolio Configuration
PORTFOLIO_MAX_RANKED_STOCKS=30
PORTFOLIO_MAX_ALLOCATION=0.10
EOF
```

**🚨 SECURITY**: Set proper permissions on `.env` file:
```bash
chmod 600 .env
```

## Step 4: Start Services

### Basic Deployment
```bash
docker-compose up -d
```

### With Redis Caching
```bash
docker-compose --profile with-redis up -d
```

### Full Production Setup
```bash
docker-compose --profile with-redis --profile with-proxy up -d
```

### Verify Deployment
```bash
docker-compose ps
docker-compose logs -f uncle-stock-api
docker-compose logs -f ib-gateway
```

## Step 5: IBKR Gateway Authentication

### Method 1: SSH Tunnel + VNC Client

**On your local machine:**
```bash
# Create SSH tunnel for VNC
ssh -L 5900:localhost:5900 root@your_droplet_ip

# Keep this terminal open, then in another terminal:
# Connect with VNC client to localhost:5900
```

**Using VNC client:**
1. Connect to `localhost:5900`
2. Enter VNC password
3. You'll see IBKR Gateway interface
4. Login with your credentials
5. Complete 2FA with IBKR Mobile app

### Method 2: Web VNC (if available)

Some Docker images provide web VNC:
```bash
# Access via browser
http://your_droplet_ip:6080
```

### Authentication Steps

1. **Initial Login**: Gateway shows login dialog
2. **Enter Credentials**: Username/password (may auto-fill via IBC)
3. **2FA Authentication**: Use IBKR Mobile app to approve
4. **API Activation**: Gateway enables API connections
5. **Verify Connection**: Check your app logs for successful connection

## Step 6: Production Hardening

### SSL Certificate (with nginx)

```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Get certificate
certbot --nginx -d your_domain.com
```

### Monitoring Setup

```bash
# Create monitoring script
cat > /usr/local/bin/check-trading-services.sh << 'EOF'
#!/bin/bash
# Check if services are running
cd /path/to/your/app

# Check API health
curl -f http://localhost:8000/health || {
    echo "API unhealthy, restarting..."
    docker-compose restart uncle-stock-api
}

# Check IBKR Gateway connection
if ! docker-compose exec ib-gateway netstat -an | grep -q :4002; then
    echo "IBKR Gateway API not responding, restarting..."
    docker-compose restart ib-gateway
fi
EOF

chmod +x /usr/local/bin/check-trading-services.sh
```

### Cron Jobs

```bash
crontab -e
```

Add these lines:
```bash
# Daily IBKR Gateway restart (at 1 AM EST)
0 6 * * * cd /path/to/your/app && docker-compose restart ib-gateway

# Health check every 5 minutes
*/5 * * * * /usr/local/bin/check-trading-services.sh

# Weekly full restart (Sunday 2 AM)
0 7 * * 0 cd /path/to/your/app && docker-compose restart
```

### Log Rotation

```bash
cat > /etc/logrotate.d/trading-app << 'EOF'
/path/to/your/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 root root
}
EOF
```

## Step 7: Operational Procedures

### Daily Authentication Flow

1. **Check Gateway Status**:
   ```bash
   docker-compose logs ib-gateway | tail -20
   ```

2. **If Authentication Needed**:
   ```bash
   # Connect via VNC
   ssh -L 5900:localhost:5900 root@your_droplet_ip
   # Use VNC client to login
   ```

3. **Verify API Connection**:
   ```bash
   # Check your app logs
   docker-compose logs uncle-stock-api | grep -i "IBKR connection"
   ```

### Troubleshooting Commands

```bash
# View all service logs
docker-compose logs -f

# Restart specific service
docker-compose restart ib-gateway

# Access container shell
docker-compose exec ib-gateway bash

# Check network connectivity
docker-compose exec uncle-stock-api ping ib-gateway

# Monitor resource usage
docker stats

# Backup important data
tar -czf backup-$(date +%Y%m%d).tar.gz data/ ibkr-settings/ .env
```

### Update Deployment

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# Verify health
docker-compose ps
curl http://localhost:8000/health
```

## Security Best Practices

1. **Credentials**:
   - Never commit `.env` to git
   - Use Docker secrets in production
   - Rotate passwords regularly

2. **Network Security**:
   - Use SSH tunnels for VNC access
   - Don't expose VNC port publicly
   - Enable UFW firewall

3. **Access Control**:
   - Use SSH keys only
   - Disable password authentication
   - Regular security updates

4. **Monitoring**:
   - Set up log monitoring
   - Monitor trading account for unauthorized activity
   - Alert on service failures

## Cost Optimization

### Digital Ocean Costs
- **4GB Droplet**: $24/month
- **Backups**: +20% ($4.80/month)
- **Load Balancer**: $12/month (optional)
- **Total**: ~$30-45/month

### Alternative Solutions
- **Smaller Droplet**: 2GB RAM ($12/month) for light trading
- **Managed Database**: For production data persistence
- **CDN**: For static assets (if applicable)

## Troubleshooting Guide

### Common Issues

1. **IBKR Connection Refused**:
   - Check if Gateway is running: `netstat -an | grep 4002`
   - Verify API settings in Gateway
   - Restart Gateway container

2. **VNC Connection Failed**:
   - Check if VNC server is running
   - Verify SSH tunnel is active
   - Check VNC password

3. **Daily Authentication Loop**:
   - IBKR requires daily re-authentication
   - Set up monitoring for authentication failures
   - Consider using IBC auto-restart features

4. **Performance Issues**:
   - Monitor resource usage with `docker stats`
   - Check logs for memory/CPU constraints
   - Consider upgrading droplet size

### Log Locations

- **Your App**: `./logs/`
- **IBKR Gateway**: `./ibkr-logs/`
- **Docker**: `docker-compose logs [service]`
- **System**: `/var/log/syslog`

## Support Resources

- **IBKR API Documentation**: https://interactivebrokers.github.io/tws-api/
- **Docker Image Issues**: https://github.com/gnzsnz/ib-gateway-docker
- **Digital Ocean Docs**: https://docs.digitalocean.com/
- **Your App Issues**: Check your repository issues

## Next Steps

After successful deployment:

1. **Test Trading Functions**: Verify all API endpoints work
2. **Set Up Monitoring**: Implement comprehensive logging
3. **Backup Strategy**: Regular data and configuration backups
4. **Performance Tuning**: Optimize based on usage patterns
5. **Security Review**: Regular security audits and updates

---

## Quick Reference Commands

```bash
# Status check
docker-compose ps

# View logs
docker-compose logs -f [service_name]

# Restart service
docker-compose restart [service_name]

# Full restart
docker-compose down && docker-compose up -d

# VNC access
ssh -L 5900:localhost:5900 root@your_droplet_ip

# Health check
curl http://localhost:8000/health

# Resource monitoring
docker stats
```

Remember: IBKR Gateway requires daily authentication, so plan for regular VNC access or consider automated solutions for production environments.