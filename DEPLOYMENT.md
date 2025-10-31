# 🚀 GoldMineAI Deployment Guide

This guide will help you deploy GoldMineAI to production using Docker. The application is designed to be deployed quickly and efficiently.

## 🎯 **Quick Deploy (Today)**

### **Option 1: DigitalOcean App Platform (Recommended for Today)**

1. **Push to GitHub** (if not already done)
2. **Connect to DigitalOcean App Platform**
3. **Deploy in 5 minutes**

### **Option 2: AWS ECS (Alternative)**

1. **Build and push Docker image**
2. **Deploy to ECS Fargate**
3. **Set up load balancer**

### **Option 3: Local Docker (Testing)**

1. **Run `./deploy.sh`**
2. **Access at http://localhost:8000**

## 🐳 **Docker Setup**

### **Prerequisites**
- Docker Desktop installed
- docker-compose installed
- Git repository with your code

### **Files Created**
- `Dockerfile` - Production container definition
- `docker-compose.yml` - Local development setup
- `nginx.conf` - Web server configuration
- `.dockerignore` - Exclude unnecessary files
- `deploy.sh` - Automated deployment script

## 🚀 **Local Deployment (Test First)**

```bash
# Make script executable
chmod +x deploy.sh

# Deploy locally
./deploy.sh
```

**Expected Output:**
```
🚀 Starting GoldMineAI deployment...
📋 Environment Configuration:
   Database: localhost:5432/goldmineai
   Allowed Hosts: localhost,127.0.0.1
   Secret Key: your-secret-key-cha...
🛑 Stopping existing containers...
🔨 Building Docker image...
🚀 Starting services...
⏳ Waiting for services to be ready...
🔍 Checking application health...
✅ Application is healthy!
🗄️  Running database migrations...
📁 Collecting static files...
👤 Creating superuser (if needed)...
🎉 Deployment completed successfully!

📱 Application URLs:
   Main App: http://localhost:8000
   Maps: http://localhost:8000/maps/
   Admin: http://localhost:8000/admin/

🔑 Default Admin Credentials:
   Username: admin
   Password: admin123
```

## 🌐 **Production Deployment**

### **DigitalOcean App Platform (Easiest)**

1. **Create App**
   - Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
   - Click "Create App"
   - Connect your GitHub repository

2. **Configure App**
   ```yaml
   # App Spec
   name: goldmineai
   services:
   - name: web
     source_dir: /
     github:
       repo: yourusername/goldmineai
       branch: main
     dockerfile_path: Dockerfile
     http_port: 8000
     instance_count: 1
     instance_size_slug: basic-xxs
     envs:
     - key: SECRET_KEY
       value: your-production-secret-key
     - key: DEBUG
       value: "False"
     - key: ALLOWED_HOSTS
       value: yourdomain.com,www.yourdomain.com
   ```

3. **Deploy**
   - Click "Create Resources"
   - Wait for deployment (5-10 minutes)

### **AWS ECS Fargate**

1. **Build and Push Image**
   ```bash
   # Build image
   docker build -t goldmineai .
   
   # Tag for ECR
   docker tag goldmineai:latest your-account.dkr.ecr.region.amazonaws.com/goldmineai:latest
   
   # Push to ECR
   aws ecr get-login-password --region region | docker login --username AWS --password-stdin your-account.dkr.ecr.region.amazonaws.com
   docker push your-account.dkr.ecr.region.amazonaws.com/goldmineai:latest
   ```

2. **Create ECS Cluster**
   - Go to ECS Console
   - Create cluster (Fargate)
   - Create task definition
   - Create service

3. **Configure Load Balancer**
   - Application Load Balancer
   - Target group pointing to ECS service
   - SSL certificate for HTTPS

### **Environment Variables**

```bash
# Required
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (if using external)
DB_NAME=goldmineai
DB_USER=postgres
DB_PASSWORD=secure-password
DB_HOST=your-db-host
DB_PORT=5432

# Optional
MAPBOX_API_KEY=your-mapbox-key
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 📁 **File Storage**

### **Local Storage (Default)**
- Media files stored in `./media/` directory
- Mounted as Docker volume
- **Pros**: Simple, no external dependencies
- **Cons**: Not scalable, data lost if container removed

### **Cloud Storage (Recommended)**
- **AWS S3** or **DigitalOcean Spaces**
- Update `settings.py` to use `django-storages`
- **Pros**: Scalable, persistent, backup-friendly
- **Cons**: Additional setup required

## 🔒 **Security Considerations**

### **Production Checklist**
- [ ] Change default admin password
- [ ] Use strong SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS
- [ ] Enable HTTPS
- [ ] Set up firewall rules
- [ ] Regular security updates

### **SSL/HTTPS**
```bash
# Using Let's Encrypt
certbot --nginx -d yourdomain.com

# Or use Cloudflare (free SSL)
# Point DNS to Cloudflare, enable SSL
```

## 📊 **Monitoring & Logs**

### **Health Check**
- Endpoint: `/health/`
- Returns application status
- Used by Docker health checks

### **Logs**
```bash
# View logs
docker-compose logs web

# Follow logs
docker-compose logs -f web

# View specific service
docker-compose logs nginx
```

### **Performance Monitoring**
- Consider adding **New Relic** or **DataDog**
- Monitor response times
- Track error rates

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Port Already in Use**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Kill process or change port
   docker-compose down
   # Edit docker-compose.yml port mapping
   ```

2. **Database Connection Issues**
   ```bash
   # Check database container
   docker-compose ps db
   
   # View database logs
   docker-compose logs db
   
   # Test connection
   docker-compose exec web python manage.py dbshell
   ```

3. **Static Files Not Loading**
   ```bash
   # Rebuild static files
   docker-compose exec web python manage.py collectstatic --noinput
   
   # Check nginx configuration
   docker-compose logs nginx
   ```

### **Reset Everything**
```bash
# Stop and remove everything
docker-compose down -v

# Remove all images
docker system prune -a

# Start fresh
./deploy.sh
```

## 📈 **Scaling**

### **Horizontal Scaling**
- **DigitalOcean**: Increase instance count
- **AWS ECS**: Auto-scaling groups
- **Load Balancer**: Distribute traffic

### **Vertical Scaling**
- Increase instance size
- Add more memory/CPU
- Optimize database queries

## 💰 **Cost Optimization**

### **DigitalOcean App Platform**
- **Basic**: $5/month (512MB RAM, 0.25 vCPU)
- **Professional**: $12/month (1GB RAM, 0.5 vCPU)
- **Performance**: $24/month (2GB RAM, 1 vCPU)

### **AWS ECS Fargate**
- **CPU**: $0.04048 per vCPU per hour
- **Memory**: $0.004445 per GB per hour
- **Estimated**: $15-30/month for small app

## 🎯 **Next Steps After Deployment**

1. **Test all functionality**
   - Maps page
   - Chatbot
   - File uploads
   - Coordinate generation

2. **Set up monitoring**
   - Uptime monitoring
   - Error tracking
   - Performance metrics

3. **Configure backups**
   - Database backups
   - Media file backups
   - Configuration backups

4. **Set up CI/CD**
   - Automatic deployments
   - Testing pipeline
   - Rollback procedures

## 📞 **Support**

If you encounter issues:
1. Check the logs: `docker-compose logs`
2. Verify environment variables
3. Test locally first
4. Check Docker and system resources

---

**🎉 Congratulations! Your GoldMineAI application is now deployed and ready for your client!**
