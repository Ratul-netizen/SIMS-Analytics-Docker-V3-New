# SIMS Analytics Deployment Guide

## Docker Build Issues

### SpaCy Model Download Timeout

**Problem:** Docker build fails with timeout errors when downloading the SpaCy model (`en_core_web_sm`).

**Error Message:**
```
ReadTimeoutError: HTTPSConnectionPool(host='release-assets.githubusercontent.com', port=443): Read timed out.
```

**Simple Solution:**
The app is configured to automatically download the SpaCy model at runtime if it's not available during the Docker build. The Docker build will skip the model download and the application will handle it when it starts.

Just run:
```bash
docker-compose up --build
```

The SpaCy model will be downloaded automatically when the application starts, and if it fails, the app will use a fallback English model.

## VM Deployment Troubleshooting

### Common Issues and Solutions

#### 1. "Could not fetch data" Error

This error typically occurs due to network configuration issues when deploying to a VM.

**Solutions:**

1. **Check Backend Accessibility**
   ```bash
   # Test if backend is running
   curl http://YOUR_VM_IP:5000/api/health
   ```

2. **Check Firewall Settings**
   ```bash
   # Allow ports 3000 and 5000
   sudo ufw allow 3000
   sudo ufw allow 5000
   ```

3. **Verify Docker Services**
   ```bash
   # Check if containers are running
   docker ps
   
   # Check container logs
   docker logs sims_backend
   docker logs sims_frontend
   ```

#### 2. CORS Issues

The backend is configured to handle CORS for VM deployment, but you may need to adjust:

**Backend CORS Configuration:**
- The backend allows all origins (`*`) for API endpoints
- Supports credentials and common HTTP methods
- Configured for both localhost and VM IP access

#### 3. Network Configuration

**Frontend API Configuration:**
- Frontend automatically detects if running on localhost vs VM
- For VM deployment, it uses `http://YOUR_VM_IP:5000` for backend calls
- Make sure port 5000 is accessible from the frontend

### Deployment Steps

1. **Build and Start Services**
   ```bash
   docker-compose up --build -d
   ```

2. **Check Service Health**
   ```bash
   # Backend health check
   curl http://localhost:5000/api/health
   
   # Frontend should be accessible at
   http://YOUR_VM_IP:3000
   ```

3. **Verify Database**
   ```bash
   # Check database stats
   curl http://localhost:5000/api/database-stats
   ```

### Environment Variables

Make sure your `.env` file in the backend directory contains:
```
EXA_API_KEY=your_exa_api_key_here
FLASK_ENV=production
```

### Troubleshooting Commands

```bash
# Restart services
docker-compose restart

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Rebuild and restart
docker-compose down
docker-compose up --build -d

# Check network connectivity
docker network ls
docker network inspect sims_analytics_sims_network
```

### Port Configuration

- **Frontend**: Port 3000
- **Backend**: Port 5000
- **Database**: SQLite (file-based, no external port needed)

### Security Considerations

1. **Firewall**: Only expose necessary ports (3000, 5000)
2. **Environment Variables**: Keep API keys secure
3. **HTTPS**: Consider using a reverse proxy with SSL for production

### Monitoring

The application includes health check endpoints:
- `/api/health` - Backend health status
- `/api/database-stats` - Database statistics

Use these to monitor the application status.

## Database Management

### Extracting Database from Docker Container

When you need to backup or extract the database from the Docker container:

#### 1. Copy Database File from Container
```bash
# Copy the database file from the backend container
docker cp sims_backend:/app/instance/SIMS_Analytics.db ./SIMS_Analytics_backup.db

# Or if using a different container name
docker cp $(docker ps -q -f name=backend):/app/instance/SIMS_Analytics.db ./SIMS_Analytics_backup.db
```

#### 2. Copy Database to Container
```bash
# Copy a database file into the container
docker cp ./SIMS_Analytics_backup.db sims_backend:/app/instance/SIMS_Analytics.db

# Restart the backend container to use the new database
docker-compose restart backend
```

#### 3. Backup Database with Timestamp
```bash
# Create a timestamped backup
docker cp sims_backend:/app/instance/SIMS_Analytics.db "./SIMS_Analytics_$(date +%Y%m%d_%H%M%S).db"
```

#### 4. Check Database Size
```bash
# Check the size of the database file
docker exec sims_backend ls -lh /app/instance/SIMS_Analytics.db
```

### Database Reset

To completely reset the database:
```bash
# Remove the database file from the container
docker exec sims_backend rm /app/instance/SIMS_Analytics.db

# Restart the backend to create a fresh database
docker-compose restart backend
```

### Database Migration

If you need to migrate the database to a new deployment:
1. Extract the database using the commands above
2. Copy the `.db` file to the new deployment
3. Place it in the `backend/instance/` directory
4. Restart the backend container 