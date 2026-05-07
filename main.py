from playwright.sync_api import sync_playwright
import smtplib
from email.mime.text import MIMEText
import os

# --- SETTINGS ---
# In GitHub Actions, these will be pulled from Secrets. 
# For local testing, you can temporarily hardcode your credentials here.
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "your_email@gmail.com") 
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your_app_password") 
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "receiver_email@gmail.com")
URL = "https://www.apartments-hn.de/en/book-apartment"
STATE_FILE = "known_rooms.txt"

def get_known_rooms():
    """Reads previously found apartments from the state file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def save_known_rooms(rooms):
    """Saves the current available apartments to the state file."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(rooms)))

def check_apartments():
    print("Waiting for the website to load and JavaScript to execute...")
    known_available_rooms = get_known_rooms()
    current_available_rooms = set()
    
    try:
        # Launch Playwright's headless browser
        with sync_playwright() as p:
            # Set headless=False if you want to visually see the browser open during local testing
            browser = p.chromium.launch(headless=True) 
            page = browser.new_page()
            
            # Go to the URL and wait until all network activity (including API calls) is finished
            page.goto(URL, wait_until="networkidle")
            
            # Wait up to 10 seconds for the table rows to appear in the DOM
            page.wait_for_selector("table tbody tr", timeout=10000)
            
            # Fetch all rows from the table based on the selector structure
            rows = page.locator("table tbody tr").all()
            print(f"Found {len(rows)} rows (apartments). Analyzing...")
            
            for row in rows:
                # Target the 6th column (Status column)
                status_cell = row.locator("td:nth-child(6)")
                
                if status_cell.count() > 0:
                    # Get the text inside the cell and convert to lowercase for safety
                    status_text = status_cell.inner_text().lower()
                    
                    # If the status DOES NOT contain "already taken", proceed
                    if status_text and "already taken" not in status_text:
                        # Extract all texts from the row's cells
                        columns = row.locator("td").all_inner_texts()
                        if len(columns) >= 5:
                            # Combine the first 3 columns (e.g., Appt. Name - Size - Price) to create a unique ID
                            room_id = " - ".join([col.strip() for col in columns[:5]])
                            current_available_rooms.add(room_id)
                            print(f"Potential Available Apartment: {room_id} | Status: {status_text}")
                            
            browser.close() # Close the browser
            
        # Determine if there are any NEW apartments that weren't in our state file
        new_rooms = current_available_rooms - known_available_rooms
        
        if new_rooms:
            sorted_rooms = sorted(new_rooms)
            print(f"\nNEW AVAILABLE APARTMENTS FOUND:\n{sorted_rooms}")
            # Call the email function to send alerts
            # send_email(new_rooms)  # <-- UNCOMMENT THIS LINE to activate email sending!
            save_known_rooms(current_available_rooms)
        else:
            print("\nNo new available apartments. Current state preserved.")
            save_known_rooms(current_available_rooms)
            
    except Exception as e:
        print(f"An error occurred during scraping: {e}")

def send_email(new_rooms):
    subject = "Apartments-HN: APARTMENT ALERT!"
    room_list = "\n".join(list(new_rooms))
    body = (f"Hello,\n\n"
            f"There are available or soon-to-be available apartments on the website you are tracking:\n\n"
            f"{room_list}\n\n"
            f"Check it out immediately and apply: {URL}\n\nBot")
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    try:
        # Establish secure connection and send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    check_apartments()