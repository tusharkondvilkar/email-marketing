import os
import random
import requests
import time
import pandas as pd
from datetime import datetime
from flask import Flask, render_template_string, redirect, url_for, request, flash
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = Flask(__name__)
app.secret_key = "hrmantra_super_secret_key"

scheduler = BackgroundScheduler()

# List of templates to cycle through sequentially
TEMPLATES = [
    "hrmantra_daily_newsletter_day_01",
    "hrmantra_daily_newsletter_day_02",
    "hrmantra_daily_newsletter_day_03",
    "hrmantra_daily_newsletter_day_04",
    "hrmantra_daily_newsletter_day_05"
]

# Global state to track execution and the uploaded emails
state = {
    "status": "Stopped",  
    "template_index": 0,  # Tracks which template to send next
    "active_days": [],    
    "email_list": []      # Stores the list of 500+ emails
}

def pick_random_days():
    """Picks 2 random days of the week (0=Monday to 6=Sunday)."""
    state["active_days"] = random.sample(range(0, 7), 2)
    print(f"[{datetime.now()}] System picked these days for the week: {state['active_days']}")

def shoot_email():
    """Shoots the CURRENT template to ALL uploaded emails."""
    if state["status"] != "Running":
        return

    current_day = datetime.today().weekday()
    
    if current_day in state["active_days"]:
        if not state["email_list"]:
            print(f"[{datetime.now()}] No email data loaded. Skipping execution.")
            return

        # Pick the template for today's blast
        current_template = TEMPLATES[state["template_index"]]
        print(f"[{datetime.now()}] Starting blast for template: {current_template}")
        
        # Blast to all 500+ emails
        for email in state["email_list"]:
            url = (
                f"https://eapi.instaalerts.zone/email?uname=HRM_Email"
                f"&pass=ASHOKsurendra123%21%40%23&fromName=HRMantra"
                f"&TemplateID={current_template}&fromEmail=sales@hrmantra.com"
                f"&toEmail={email}&subject=Stage+test"
            )
            
            try:
                response = requests.get(url)
                print(f"Sent {current_template} to {email} - Status: {response.status_code}")
                # 1-second delay to prevent overloading your email API provider
                time.sleep(1) 
            except Exception as e:
                print(f"Error shooting email to {email}: {e}")

        # Once the blast is complete, queue up the next template for the NEXT active day
        state["template_index"] = (state["template_index"] + 1) % len(TEMPLATES)
        print(f"[{datetime.now()}] Blast complete. Next template queued: {TEMPLATES[state['template_index']]}")

# Schedule the randomizer to run every Monday at 00:00 to pick new days
scheduler.add_job(pick_random_days, CronTrigger(day_of_week='mon', hour=0, minute=0))

# Schedule the email job to check and shoot every day at 10:00 AM
scheduler.add_job(shoot_email, CronTrigger(hour=10, minute=0))

# Web Dashboard HTML
HTML_UI = """
<!DOCTYPE html>
<html>
<head>
    <title>HRMantra Email Automation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f9; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0px 0px 10px #ccc; max-width: 600px; margin: auto; text-align: center; }
        h2 { color: #333; }
        .status { font-size: 20px; font-weight: bold; margin: 20px 0; }
        .Running { color: green; }
        .Paused { color: orange; }
        .Stopped { color: red; }
        .btn { padding: 10px 20px; font-size: 16px; margin: 5px; cursor: pointer; border: none; border-radius: 5px; color: white; }
        .btn-start { background-color: #28a745; }
        .btn-pause { background-color: #ffc107; color: black; }
        .btn-stop { background-color: #dc3545; }
        .btn-upload { background-color: #007bff; margin-top: 10px; }
        .details { margin-top: 20px; font-size: 14px; color: #555; text-align: left; background: #f8f9fa; padding: 15px; border-radius: 5px; }
        .upload-section { margin-top: 20px; padding: 20px; border: 2px dashed #ccc; border-radius: 5px; }
        .flash { color: green; font-weight: bold; margin-bottom: 15px; }
        .error { color: red; font-weight: bold; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Email Automation Panel</h2>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <p class="status {{ state['status'] }}">Current Status: {{ state['status'] }}</p>
        
        <form action="/action/start" method="post" style="display:inline;">
            <button type="submit" class="btn btn-start">Start</button>
        </form>
        <form action="/action/pause" method="post" style="display:inline;">
            <button type="submit" class="btn btn-pause">Pause</button>
        </form>
        <form action="/action/stop" method="post" style="display:inline;">
            <button type="submit" class="btn btn-stop">Stop</button>
        </form>

        <div class="upload-section">
            <h3>Upload Email List (.xlsx or .csv)</h3>
            <p style="font-size: 12px; color: #666;">File must contain a column named exactly <b>Email</b>.</p>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="email_file" accept=".xlsx, .csv" required>
                <br>
                <button type="submit" class="btn btn-upload">Upload Data</button>
            </form>
            <p>Total Emails Loaded: <strong>{{ state['email_list']|length }}</strong></p>
        </div>

        <div class="details">
            <p><strong>Next Template to Blast:</strong> <span style="color: blue;">{{ current_template }}</span></p>
            <p><strong>Active Days (0=Mon, 6=Sun):</strong> {{ state['active_days'] }}</p>
            <hr>
            <p><i>System checks daily at 10:00 AM. If today is an active day, it shoots the 'Next Template' to all uploaded emails, then queues up the next template for the next scheduled day.</i></p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(
        HTML_UI, 
        state=state,
        current_template=TEMPLATES[state["template_index"]]
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'email_file' not in request.files:
        flash("No file uploaded.", "error")
        return redirect(url_for('index'))
        
    file = request.files['email_file']
    if file.filename == '':
        flash("No selected file.", "error")
        return redirect(url_for('index'))

    if file:
        try:
            # Handle both Excel and CSV uploads seamlessly
            if file.filename.endswith('.xlsx'):
                df = pd.read_excel(file)
            elif file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                flash("Please upload a valid .xlsx or .csv file.", "error")
                return redirect(url_for('index'))
            
            # Check if required column exists
            if 'Email' not in df.columns:
                flash("Error: File must contain an 'Email' column.", "error")
                return redirect(url_for('index'))
            
            # Drop empty rows and extract list of emails
            df = df.dropna(subset=['Email'])
            emails = df['Email'].astype(str).str.strip().tolist()
            
            # Clean out any empty strings
            cleaned_emails = [e for e in emails if e]
            
            state["email_list"] = cleaned_emails
            flash(f"Successfully loaded {len(cleaned_emails)} emails!", "flash")
            
        except Exception as e:
            flash(f"Error processing file: {str(e)}", "error")
        
    return redirect(url_for('index'))

@app.route('/action/<cmd>', methods=['POST'])
def handle_action(cmd):
    if cmd == 'start':
        if state["status"] == "Stopped":
            pick_random_days()
            state["template_index"] = 0 # Reset to day 01 template when started fresh
        state["status"] = "Running"
        if not scheduler.running:
            scheduler.start()
            
    elif cmd == 'pause':
        state["status"] = "Paused"
        
    elif cmd == 'stop':
        state["status"] = "Stopped"
        state["active_days"] = []
        state["email_list"] = [] # Clears the loaded data
        state["template_index"] = 0 # Resets the template cycle back to the beginning
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    pick_random_days()
    scheduler.start()
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
