# Gemini 2.5 Flash Integration Setup Guide

This guide explains how to set up and use Google Gemini 2.5 Flash exclusively with your SIMS Analytics application. This integration uses only Gemini AI without any fallback models.

## Prerequisites

1. **Google AI Studio Account**: You need access to Google AI Studio and a Gemini API key
2. **Python Dependencies**: The integration requires the `google-genai` package

## Setup Instructions

### 1. Install Dependencies

The `google-genai` dependency has already been added to `backend/requirements.txt`. Install it by running:

```bash
cd backend
pip install -r requirements.txt
```

### 2. Get Your Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key for the next step

### 3. Configure Environment Variables

Create or update your environment files:

**For the root directory (.env):**
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

**For the backend directory (backend/.env):**
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Test the Integration

1. Start your backend server:
   ```bash
   cd backend
   python app.py
   ```

2. Start your frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Navigate to `http://localhost:3000/gemini-test` to test the Gemini AI integration

## How It Works

### Backend Integration

The Gemini AI integration is implemented in `backend/app.py`:

- **`call_gemini_api()`**: Main function that sends requests to Gemini AI
- **`parse_gemini_response()`**: Parses and structures the AI response
- **Enhanced `call_gemma_api()`**: Now tries Gemini AI first, falls back to OpenAI
- **New API endpoint**: `/api/gemini-analyze` for direct Gemini analysis

### Frontend Interface

A new test page has been created at `/gemini-test` that allows you to:
- Input article text and title
- Analyze with Gemini AI
- View structured results including:
  - Sentiment analysis
  - Category classification
  - Key entity extraction
  - Fact-checking status
  - Geopolitical implications
  - Media bias assessment

### Features

**Enhanced Analysis Capabilities:**
- **Web Search Integration**: Gemini AI can search the web for supporting information
- **Geopolitical Analysis**: Specific insights for Bangladesh-India relations
- **Media Bias Assessment**: Analysis of potential bias in reporting
- **Entity Extraction**: Automatic identification of key people, places, and organizations

**Exclusive Gemini Integration:**
- Uses only Google Gemini 2.5 Flash model for all analysis
- No fallback models - ensures consistent AI behavior
- Graceful error handling with detailed error messages
- Optimized for Gemini's capabilities and features

## Usage Examples

### Direct API Call

```bash
curl -X POST http://localhost:5000/api/gemini-analyze \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bangladesh-India Trade Agreement",
    "text": "Bangladesh and India have signed a new trade agreement..."
  }'
```

### Integration with Article Processing

The Gemini 2.5 Flash integration automatically enhances the existing article ingestion process. When new articles are processed, the system will:

1. Use Gemini 2.5 Flash model exclusively for analysis
2. Return error if Gemini is unavailable (no fallback models)
3. Store enhanced analysis results in the database
4. Display results in the main dashboard with Gemini-powered insights

## Troubleshooting

### Common Issues

1. **"Gemini AI not available" error**
   - Check that `GEMINI_API_KEY` is properly set in your environment
   - Verify the API key is valid and has sufficient quota

2. **Import errors for `google-genai`**
   - Run `pip install google-genai` in your backend directory
   - Make sure you're using the correct Python environment

3. **Timeout errors**
   - Gemini AI with web search can take longer than regular API calls
   - This is normal behavior as it searches for supporting information

### Environment Variable Priority

The application looks for environment variables in this order:
1. System environment variables
2. `.env` file in the backend directory
3. `.env` file in the root directory

## Security Notes

- Never commit your API keys to version control
- Keep your `.env` files in `.gitignore`
- Consider using environment variable management tools for production deployments
- Monitor your API usage to avoid unexpected charges

## API Limits and Costs

- Check your Google AI Studio dashboard for current usage and limits
- The Gemini API may have rate limits and usage quotas
- Web search functionality may have additional costs

## Next Steps

Once the integration is working, you can:

1. **Enhance Analysis Prompts**: Modify the analysis prompts in `call_gemini_api()` for more specific insights
2. **Add Custom Filters**: Create custom dashboard filters for Gemini-enhanced articles
3. **Expand Entity Recognition**: Use Gemini's advanced NLP for better entity extraction
4. **Integrate Real-time Alerts**: Set up alerts based on Gemini's geopolitical analysis

For support or questions, refer to the main SIMS Analytics documentation or create an issue in the project repository. 