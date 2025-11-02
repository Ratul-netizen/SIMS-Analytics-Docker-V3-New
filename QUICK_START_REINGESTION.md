# Quick Start: Running Reingestion in Docker

## 🚀 Easiest Method (Recommended)

**Run from your host machine** - Since port 5000 is exposed, this works immediately:

```bash
# 1. Make sure containers are running
docker-compose up -d

# 2. Wait for backend to be healthy (optional check)
docker-compose logs backend | grep -i "healthy\|ready\|running"

# 3. Install requests if you don't have it
pip install requests

# 4. Run the script
python run_reingestion.py
```

That's it! The script will connect to `http://localhost:5000` which is exposed by your Docker container.

---

## 🔧 Alternative: Run Inside Backend Container

If you prefer to run it in the same environment:

```bash
# 1. Copy script to container
docker cp run_reingestion.py sims_backend:/app/

# 2. Install requests (one-time)
docker exec sims_backend pip install requests

# 3. Run the script
docker exec -it sims_backend python /app/run_reingestion.py
```

---

## 📦 Using Docker Service (Most Docker-Native)

If you want to add it as a Docker service, add this to your `docker-compose.yml`:

```yaml
  reingestion:
    image: python:3.10-slim
    container_name: sims_reingestion
    working_dir: /app
    environment:
      - BACKEND_URL=http://backend:5000
    volumes:
      - ./run_reingestion_docker.py:/app/run_reingestion.py
    command: >
      sh -c "pip install -q requests && python run_reingestion.py"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - sims_network
    profiles:
      - tools
```

Then run:
```bash
docker-compose --profile tools run --rm reingestion
```

---

## ⚙️ Using the Docker-Compatible Script

I've created `run_reingestion_docker.py` which automatically detects if it's running in Docker and uses the correct URL:

```bash
# From host (uses localhost:5000)
python run_reingestion_docker.py

# Or set custom URL
BACKEND_URL=http://your-backend:5000 python run_reingestion_docker.py
```

---

## 🔍 Troubleshooting

**Can't connect to backend?**
```bash
# Check if backend is running
docker-compose ps

# Check backend health
curl http://localhost:5000/api/health

# View backend logs
docker-compose logs backend
```

**Script times out?**
- The script has timeouts: 300s for fetch, 600s for reanalyze
- Check backend logs: `docker-compose logs -f backend`
- You may need to increase timeouts for large datasets

**Missing requests module?**
```bash
# On host
pip install requests

# In container
docker exec sims_backend pip install requests
```

---

## 📝 Summary

**For one-time runs**: Use the first method (run from host)
**For automation**: Add it as a cron job or scheduled task
**For production**: Consider creating a Flask CLI command (see full guide)

For more details, see `DOCKER_REINGESTION_GUIDE.md`

