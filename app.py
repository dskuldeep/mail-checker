import streamlit as st
import pytz
import json
import requests
import google.generativeai as genai
from datetime import datetime, time
from dateutil import parser
from streamlit_option_menu import option_menu


# Page configuration
st.set_page_config(page_title="Email Meeting Assistant", layout="wide")

# Configure Google Generative AI
def configure_genai():
    # You should use environment variables or Streamlit secrets for API keys in production
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        st.warning("⚠️ Google API key not found. Please set it in the Streamlit secrets.")
        api_key = st.text_input("Enter Google API Key:")
    
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

# Function to analyze email with Gemini
def analyze_email(email_content, timezone, available_hours):
    try:
        # Create a prompt for the LLM with the modified format
        prompt = f"""
        Analyze the following email to determine if it contains a meeting or scheduled event:
        
        EMAIL:
        {email_content}
        
        USER TIMEZONE:
        {timezone}
        
        USER AVAILABLE HOURS:
        {json.dumps(available_hours, indent=2)}
        
        Instructions:
        1. If the email does NOT contain a meeting or scheduled event, return: {{"action": "No Action"}}
        2. If the email contains a meeting or scheduled event:
           a. Extract the meeting date and time
           b. Convert the meeting time to the user's timezone if needed
           c. Check if the meeting falls within the user's available hours for that day of the week
           d. If the meeting is within available hours, return: {{"action": "No Action"}}
           e. If the meeting is outside available hours, return a JSON in this exact format:
              {{"action": "Action", "sender": "<sender's email>", "subject": "<email subject>", "body": "I noticed you scheduled a meeting outside my working hours. Did you mean to do this? My working hours are [provide relevant day's hours]. Would you like to reschedule?"}}
        
        Your response must be either {{"action": "No Action"}} or a valid JSON containing "action": "Action".
        Do not include any other text before or after the JSON.
        """
        
        # Use the current supported model
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        return response.text
    except Exception as e:
        st.error(f"Error analyzing email: {str(e)}")
        return json.dumps({"action": "No Action"})

# Function to send response email via webhook
def send_response_email(email_data):
    try:
        webhook_url = "https://n8n.getzetachi.com/webhook/send-mail"
        
        payload = {
            "email": email_data.get("sender", ""),
            "subject": email_data.get("subject", "Meeting Time Confirmation"),
            "message": email_data.get("body", "")
        }
        print(f"Payload: {payload}")  # Debugging line
        headers = {"Content-Type": "application/json"}
        response = requests.post(webhook_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            st.success("Response email sent successfully!")
        else:
            st.error(f"Failed to send email. Status code: {response.status_code}")
            st.error(f"Response: {response.text}")
    
    except Exception as e:
        st.error(f"Error sending response email: {str(e)}")

# Main App UI
def main():
    st.title("📧 Email Meeting Assistant")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        
        # Timezone selection
        all_timezones = pytz.all_timezones
        common_timezones = ["US/Eastern", "US/Central", "US/Pacific", "Europe/London", 
                          "Europe/Paris", "Asia/Tokyo", "Asia/Singapore", "Australia/Sydney"]
        
        timezone_tab1, timezone_tab2 = st.tabs(["Common", "All"])
        
        with timezone_tab1:
            timezone = st.selectbox("Select your timezone (Common)", common_timezones)
        
        with timezone_tab2:
            timezone_all = st.selectbox("Select your timezone (All)", all_timezones)
            if timezone_all != all_timezones[0]:  # If user selected something in "All" tab
                timezone = timezone_all
        
        st.divider()
        
        # Available hours settings
        st.subheader("Available Hours")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Initialize available hours in session state if not already set
        if "available_hours" not in st.session_state:
            st.session_state.available_hours = {day: {"enabled": True if day not in ["Saturday", "Sunday"] else False, 
                                                    "start": "09:00", 
                                                    "end": "17:00"} for day in days}
        
        # Create available hours settings for each day
        available_hours = {}
        for day in days:
            with st.expander(day):
                # Fixed layout with appropriate column widths to prevent text wrapping
                col1, col2, col3 = st.columns([0.8, 1.1, 1.1])
                
                with col1:
                    # Use a narrower label to prevent wrapping
                    enabled = st.checkbox("On", value=st.session_state.available_hours[day]["enabled"], key=f"enable_{day}")
                
                with col2:
                    start_time = st.time_input("From", 
                                              value=datetime.strptime(st.session_state.available_hours[day]["start"], "%H:%M").time(), 
                                              key=f"start_{day}")
                
                with col3:
                    end_time = st.time_input("To", 
                                            value=datetime.strptime(st.session_state.available_hours[day]["end"], "%H:%M").time(), 
                                            key=f"end_{day}")
                
                # Update session state
                st.session_state.available_hours[day] = {
                    "enabled": enabled,
                    "start": start_time.strftime("%H:%M"),
                    "end": end_time.strftime("%H:%M")
                }
                
                available_hours[day] = st.session_state.available_hours[day]
    
    # Main content area
    st.header("Paste Email Content")
    email_content = st.text_area("", height=300, placeholder="Paste the complete email content here...")
    
    if st.button("Analyze Email", type="primary"):
        if not email_content:
            st.warning("Please paste an email to analyze.")
            return
        
        with st.spinner("Analyzing email..."):
            # Check if Google API is configured
            if not configure_genai():
                st.error("Google API key is required to analyze emails.")
                return
            
            # Analyze email with the LLM
            result = analyze_email(email_content, timezone, available_hours)
            
            # Simplified result handling with the new JSON format
            try:
                # Clean the response text and extract JSON
                result_text = result.strip()
                if "{" in result_text and "}" in result_text:
                    start_idx = result_text.find("{")
                    end_idx = result_text.rfind("}") + 1
                    json_str = result_text[start_idx:end_idx]
                else:
                    json_str = result_text
                
                # Parse the JSON response
                response_data = json.loads(json_str)
                
                # Check the action field
                if response_data.get("action") == "Action":
                    st.warning("Meeting outside available hours detected!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Details:**")
                        st.markdown(f"**Sender:** {response_data.get('sender', 'Not found')}")
                        st.markdown(f"**Subject:** {response_data.get('subject', 'Not found')}")
                    
                    with col2:
                        st.markdown("**Proposed Response:**")
                        response_body = response_data.get("body", "")
                        edited_response = st.text_area("Edit response if needed:", value=response_body, height=100, key="response_body")
                        
                        # Update the response body with any edits
                        response_data["body"] = edited_response
                    
                        send_response_email(response_data)
                else:
                    st.info("No action needed. The email either doesn't contain a meeting or the meeting is within your available hours.")
                    
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse LLM response: {str(e)}")
                st.code(result)
            except Exception as e:
                st.error(f"Error processing response: {str(e)}")

if __name__ == "__main__":
    main()