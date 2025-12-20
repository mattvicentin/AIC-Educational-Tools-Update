# Railway Deployment Guide for AI Collab Online

This guide will help you deploy your AI Collab Online application to Railway.

## 🚀 Quick Start

### 1. Prerequisites
- Railway account (sign up at [railway.app](https://railway.app))
- GitHub repository connected to Railway
- Anthropic API key for Claude AI

### 2. Connect Repository to Railway

1. **Login to Railway** and create a new project
2. **Connect your GitHub repository**:
   - Click "Deploy from GitHub repo"
   - Select your `Collab_AI_Online` repository
   - Railway will automatically detect it's a Python application

### 3. Configure Environment Variables

In your Railway project dashboard, add these environment variables:

```env
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SECRET_KEY=your_secure_secret_key_here

# Database (Railway will auto-provision PostgreSQL)
DATABASE_URL=postgresql://... (Railway will set this automatically)

# Flask settings
FLASK_ENV=production

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Additional settings
RAILWAY_ENVIRONMENT=true
```

### 4. Deploy

Railway will automatically:
- Build your application using the `Procfile`
- Install dependencies from `requirements_railway.txt`
- Start the application using Gunicorn
- Run health checks at `/health`

## 🔧 Configuration Files

### Procfile
```
web: gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

### railway.toml
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

[deploy.envs]
FLASK_ENV = "production"
```

## 📊 Monitoring & Health Checks

### Health Check Endpoint
Your application includes a health check at `/health` that returns:
```json
{
  "status": "healthy",
  "message": "App is running - PHASE 3 RESTRUCTURING COMPLETE",
  "database": "connected",
  "achievement_tables": "✓ Achievement tables ensured",
  "version": "3.0.0",
  "deployment_test": "PHASE 3 SUCCESSFUL"
}
```

### Railway Dashboard
- **Logs**: View real-time application logs
- **Metrics**: Monitor CPU, memory, and network usage
- **Deployments**: Track deployment history and rollbacks

## 🔄 Automatic Deployments

Railway automatically deploys when you:
- Push to the `main` branch
- Create a new release tag
- Manually trigger a deployment

## 🛠️ Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check Railway logs for specific errors
   # Common issues:
   # - Missing dependencies in requirements_railway.txt
   # - Import errors in Python code
   # - Environment variable issues
   ```

2. **Database Connection Issues**
   ```bash
   # Ensure DATABASE_URL is set correctly
   # Check if PostgreSQL service is provisioned
   # Verify database migrations are running
   ```

3. **Application Won't Start**
   ```bash
   # Check the health check endpoint
   # Verify all environment variables are set
   # Check Gunicorn configuration in Procfile
   ```

### Debug Commands

```bash
# View application logs
railway logs

# Check environment variables
railway variables

# Restart the application
railway service restart

# Run database migrations manually
railway run python -c "from src.main import run_production_migrations; run_production_migrations()"
```

## 🔒 Security Considerations

1. **Environment Variables**: Never commit sensitive data to your repository
2. **API Keys**: Use Railway's secure environment variable storage
3. **Database**: Railway automatically provides secure PostgreSQL connections
4. **HTTPS**: Railway automatically provides SSL certificates

## 📈 Scaling

Railway allows you to:
- **Scale horizontally**: Add more instances
- **Scale vertically**: Increase CPU/memory allocation
- **Auto-scaling**: Configure automatic scaling based on traffic

## 🔄 Migration from Digital Ocean

If you're migrating from Digital Ocean:

1. **Export your data**:
   ```bash
   # From your Digital Ocean server
   pg_dump $DATABASE_URL > backup.sql
   ```

2. **Import to Railway**:
   ```bash
   # In Railway shell
   psql $DATABASE_URL < backup.sql
   ```

3. **Update DNS**: Point your domain to Railway's URL

## 📞 Support

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Application Issues**: Check the `/health` endpoint and logs

## ✅ Deployment Checklist

- [ ] Repository connected to Railway
- [ ] Environment variables configured
- [ ] Database service provisioned
- [ ] Application builds successfully
- [ ] Health check passes (`/health`)
- [ ] All routes working correctly
- [ ] Database migrations completed
- [ ] SSL certificate active
- [ ] Custom domain configured (optional)

---

**Your AI Collab Online application is now ready for Railway deployment!** 🚀












