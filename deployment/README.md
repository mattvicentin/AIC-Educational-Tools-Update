# AI Collab Online - Production Deployment

This directory contains all the configuration files and scripts needed to deploy AI Collab Online to Digital Ocean.

## 🚀 Quick Deployment

1. **Provision Digital Ocean Droplet**
   - Ubuntu 22.04 LTS
   - 2GB RAM minimum (for Ollama)
   - 50GB SSD
   - Add your SSH key

2. **Connect to your droplet**
   ```bash
   ssh root@your-droplet-ip
   ```

3. **Clone the repository**
   ```bash
   git clone https://github.com/writeian/Collab_AI_Online.git
   cd Collab_AI_Online
   ```

4. **Run the deployment script**
   ```bash
   chmod +x deployment/deploy.sh
   ./deployment/deploy.sh
   ```

## 📋 Manual Deployment Steps

If you prefer to deploy manually:

### 1. System Setup
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib certbot python3-certbot-nginx
```

### 2. Application Setup
```bash
# Create application directory
sudo mkdir -p /var/www/ai_collab_online
sudo chown $USER:$USER /var/www/ai_collab_online

# Copy application files
cp -r . /var/www/ai_collab_online/
cd /var/www/ai_collab_online

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_production.txt
```

### 3. Database Setup
```bash
# Create PostgreSQL database
sudo -u postgres psql -c "CREATE DATABASE ai_collab_online;"
sudo -u postgres psql -c "CREATE USER ai_collab_user WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ai_collab_online TO ai_collab_user;"
```

### 4. Nginx Configuration
```bash
# Copy Nginx config
sudo cp deployment/nginx.conf /etc/nginx/sites-available/ai_collab_online
sudo ln -sf /etc/nginx/sites-available/ai_collab_online /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Systemd Service
```bash
# Set up systemd service
sudo cp deployment/ai_collab_online.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai_collab_online
```

### 6. Start Application
```bash
# Initialize database
export FLASK_ENV=production
export DATABASE_URL="postgresql://ai_collab_user:your_secure_password@localhost:5432/ai_collab_online"
python -c "from app import create_app; from models import db; app = create_app('production'); app.app_context().push(); db.create_all()"

# Start service
sudo systemctl start ai_collab_online
```

## 🔧 Configuration Files

### Environment Variables
Create a `.env` file in the application root:
```env
FLASK_ENV=production
DATABASE_URL=postgresql://ai_collab_user:your_secure_password@localhost:5432/ai_collab_online
SECRET_KEY=your-production-secret-key-here
USE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b
```

### Domain Configuration
Update `deployment/nginx.conf`:
- Replace `your-domain.com` with your actual domain
- Update SSL certificate paths if needed

### Database Configuration
Update `deployment/ai_collab_online.service`:
- Change database password
- Update any other environment variables

## 🛠️ Management Commands

### Check Application Status
```bash
sudo systemctl status ai_collab_online
```

### View Logs
```bash
# Application logs
sudo journalctl -u ai_collab_online -f

# Nginx logs
sudo tail -f /var/log/nginx/ai_collab_access.log
sudo tail -f /var/log/nginx/ai_collab_error.log

# Gunicorn logs
sudo tail -f /var/log/ai_collab/access.log
sudo tail -f /var/log/ai_collab/error.log
```

### Restart Application
```bash
sudo systemctl restart ai_collab_online
```

### Update Application
```bash
cd /var/www/ai_collab_online
git pull origin dev
source venv/bin/activate
pip install -r requirements_production.txt
sudo systemctl restart ai_collab_online
```

## 🔒 Security Considerations

1. **Change default passwords** in configuration files
2. **Set up SSL certificates** with Let's Encrypt
3. **Configure firewall** to only allow necessary ports
4. **Regular security updates**
5. **Database backups**

## 📊 Monitoring

### Health Check
The application includes a health check endpoint at `/health`

### Performance Monitoring
Consider setting up monitoring tools like:
- Prometheus + Grafana
- New Relic
- DataDog

## 🆘 Troubleshooting

### Common Issues

1. **Application won't start**
   ```bash
   sudo journalctl -u ai_collab_online -n 50
   ```

2. **Database connection issues**
   ```bash
   sudo -u postgres psql -c "\l"  # List databases
   ```

3. **Nginx configuration errors**
   ```bash
   sudo nginx -t
   ```

4. **Permission issues**
   ```bash
   sudo chown -R www-data:www-data /var/www/ai_collab_online
   ```

## 📞 Support

For issues or questions:
1. Check the logs first
2. Review the configuration files
3. Ensure all environment variables are set correctly
4. Verify database connectivity 