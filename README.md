# Email Meeting Assistant

A Streamlit application that analyzes emails for meeting requests and automatically suggests responses for meetings scheduled outside your working hours.

## Features

- Paste email content for analysis
- Configure your timezone and available working hours for each day
- AI-powered email analysis using Google's Gemini 2.0 Flash model
- Automatic response suggestions for out-of-hours meeting requests
- One-click response sending via webhook

## Setup Instructions

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Google API Setup**

   - Get an API key from [Google AI Studio](https://aistudio.google.com/)
   - Add your API key to `.streamlit/secrets.toml`:
     ```toml
     GOOGLE_API_KEY = "your-api-key-here"
     ```

3. **Run the Application**

   ```bash
   streamlit run app.py
   ```

## How to Use

1. Configure your timezone and available hours in the sidebar
2. Paste the complete email content into the text area
3. Click "Analyze Email"
4. If a meeting outside your hours is detected:
   - Review the proposed response
   - Click "Send Response Email" to send it via the webhook

## Technical Details

The application uses:
- Streamlit for the web interface
- Google Gemini 2.0 Flash model for email analysis
- Webhook integration with n8n for email sending