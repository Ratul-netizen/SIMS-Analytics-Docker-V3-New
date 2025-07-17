# API Setup Guide for SIMS Analytics

## Required API Keys

To run the SIMS Analytics application, you need to set up the following API keys:

### 1. OpenRouter API Key (for Gemma AI)

1. **Sign up at OpenRouter**: Visit [https://openrouter.ai/](https://openrouter.ai/) and create an account
2. **Get your API key**: Go to your dashboard and copy your API key
3. **Set the environment variable**: Replace `your_openrouter_api_key_here` in `docker-compose.yml` with your actual API key

```yaml
environment:
  - GEMMA_API_KEY=sk-or-v1-your-actual-api-key-here
```

### 2. Exa API Key (for news search)

The Exa API key is already configured in your environment. If you need to update it:

1. **Sign up at Exa**: Visit [https://exa.ai/](https://exa.ai/) and create an account
2. **Get your API key**: Copy your API key from the dashboard
3. **Update the environment**: Replace the existing `EXA_API_KEY` value

## Quick Setup Steps

1. **Get your OpenRouter API key** from [https://openrouter.ai/](https://openrouter.ai/)
2. **Edit `docker-compose.yml`** and replace `your_openrouter_api_key_here` with your actual API key
3. **Restart the containers**:
   ```bash
   docker compose down
   docker compose up -d
   ```

## Alternative: Create .env file

You can also create a `backend/.env` file with your API keys:

```env
EXA_API_KEY=4909c8ea-feb6-4f27-bf9e-acfd9b765229
GEMMA_API_KEY=sk-or-v1-your-actual-openrouter-api-key
GEMMA_API_URL=https://openrouter.ai/api/v1/chat/completions
GEMMA_MODEL=google/gemma-3n-e4b-it:free
```

## Verify Setup

After setting up the API keys, check that they're loaded correctly:

```bash
docker compose exec backend python -c "import os; print('EXA_API_KEY:', 'SET' if os.getenv('EXA_API_KEY') else 'NOT SET'); print('GEMMA_API_KEY:', 'SET' if os.getenv('GEMMA_API_KEY') else 'NOT SET')"
```

Both should show "SET" if configured correctly.

## Troubleshooting

- **400 Bad Request errors**: Usually mean the API key is invalid or the model is not available
- **Rate limiting**: OpenRouter has rate limits on the free tier
- **Model availability**: Ensure the `google/gemma-3n-e4b-it:free` model is available in your region 