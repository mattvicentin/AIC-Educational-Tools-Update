#!/bin/bash
# Deployment script for AI_Collab_Online on Digital Ocean
# Run this script on your Digital Ocean droplet

set -e  # Exit on any error

echo "🚀 Starting AI Collab Online deployment..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "🔧 Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib certbot python3-certbot-nginx

# Create application directory
echo "📁 Setting up application directory..."
sudo mkdir -p /var/www/ai_collab_online
sudo chown $USER:$USER /var/www/ai_collab_online

# Clone or copy application files
echo "📋 Copying application files..."
# If you're running this from the project directory:
cp -r . /var/www/ai_collab_online/
cd /var/www/ai_collab_online

# Set up Python virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements_production.txt

# Set up PostgreSQL database
echo "🗄️ Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE ai_collab_online;"
sudo -u postgres psql -c "CREATE USER ai_collab_user WITH PASSWORD 'your_secure_password_here';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ai_collab_online TO ai_collab_user;"

# Set up Nginx
echo "🌐 Configuring Nginx..."
sudo cp deployment/nginx.conf /etc/nginx/sites-available/ai_collab_online
sudo ln -sf /etc/nginx/sites-available/ai_collab_online /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Set up systemd service
echo "⚙️ Setting up systemd service..."
sudo cp deployment/ai_collab_online.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai_collab_online

# Create log directories
echo "📝 Setting up logging..."
sudo mkdir -p /var/log/ai_collab
sudo chown www-data:www-data /var/log/ai_collab

# Set proper permissions
echo "🔐 Setting proper permissions..."
sudo chown -R www-data:www-data /var/www/ai_collab_online
sudo chmod -R 755 /var/www/ai_collab_online

# Initialize database
echo "🗃️ Initializing database..."
source venv/bin/activate
export FLASK_ENV=production
export DATABASE_URL="postgresql://ai_collab_user:your_secure_password_here@localhost:5432/ai_collab_online"
python -c "from src.main import app; from src.app import db; app('production'); app.app_context().push(); db.create_all(); print('Database initialized successfully!')"

# Start the application
echo "🚀 Starting the application..."
sudo systemctl start ai_collab_online
sudo systemctl status ai_collab_online

echo "✅ Deployment completed!"
echo "🌐 Your application should be running at http://your-domain.com"
echo "📊 Check status with: sudo systemctl status ai_collab_online"
echo "📝 View logs with: sudo journalctl -u ai_collab_online -f" 