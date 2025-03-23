import sys
import os
from flask import Flask, request, jsonify, send_from_directory, render_template, session, redirect, url_for
from flask_cors import CORS
from sqlalchemy import text
from database import engine
from datetime import datetime

# Ensure root directory is in path for config import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = Flask(__name__, static_folder="../")  # Serve frontend
app.secret_key = "donkey_monkey_stop"  # Required for session management
CORS(app)

# -------------------- Before Request Handler --------------------

@app.before_request
def require_login():
    # List of routes that do not require login
    allowed_routes = ['login_page', 'login', 'static']
    
    # Debugging: Print the requested endpoint
    print(f"Requested endpoint: {request.endpoint}")

    # Check if the user is logged in
    if not session.get('logged_in') and request.endpoint not in allowed_routes:
        print("User not logged in. Redirecting to login page.")  # Debugging
        return redirect(url_for('login_page'))

# -------------------- Login --------------------

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    # Debugging: Print login attempt
    print(f"Login attempt: username={username}, password={password}")

    # Check credentials (this is a simple example, use proper authentication in production)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users WHERE username = :username AND password = :password"), {
            "username": username,
            "password": password
        })
        user = result.fetchone()

    if user:
        session['logged_in'] = True
        session['username'] = username
        print("Login successful. Session set.")  # Debugging
        return jsonify({"success": True})
    else:
        print("Login failed. Invalid credentials.")  # Debugging
        return jsonify({"success": False, "error": "Invalid username or password"})

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    print("User logged out. Session cleared.")  # Debugging
    return redirect(url_for('login_page'))

# -------------------- Serve Frontend --------------------

@app.route("/")
def serve_index():
    # Debugging: Print session status
    print(f"Session status: logged_in={session.get('logged_in')}, username={session.get('username')}")

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT transaction_id, date, amount, description, risk, status FROM transactions ORDER BY date DESC"))
            rows = [row._asdict() for row in result]  # Convert rows to dictionaries
            return render_template("index.html", rows=rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- Chatbot --------------------

@app.route("/api/chatbot", methods=["POST"])
def chatbot_reply():
    data = request.json
    user_message = data.get("message", "").lower()

    # Get the current time for personalized greetings
    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting = "Good morning!"
    elif current_hour < 18:
        greeting = "Good afternoon!"
    else:
        greeting = "Good evening!"

    # Enhanced bot logic with interactive responses
    responses = {
        "hello": f"{greeting} How can I assist you today?",
        "how are you": "I'm a bot, but I'm here to make your work easier! How about you?",
        "add transaction": "Sure! Please provide the transaction details: ID, Date, Amount, Description, Risk Level, and Status.",
        "view transactions": "You can view all transactions on the left panel. Need help filtering them?",
        "add deadline": "To add a deadline, please provide the due date, description, and status.",
        "view deadlines": "Deadlines are available in the Audit Calendar section. Anything else?",
        "generate heatmap": "Click the 'Generate Heatmap' button to visualize high-risk transactions.",
        "help": (
                    "Here are some commands you can try:\n"
                    "- 'Hello' or 'Hi'\n"
                    "- 'Add transaction' to add a new record\n"
                    "- 'Show transactions' to view recent records\n"
                    "- 'Help' to view available commands\n"
                    "- 'Bye' to exit the chat"
                ),        
        "what can you do": "I can help you with adding/viewing transactions, managing deadlines, and generating heatmaps. What would you like to do?",
        "bye": "Goodbye! If you need help again, I'm always here.",
    }

    # Handle dynamic responses for transactions
    if "transaction" in user_message and "add" in user_message:
        bot_reply = "To add a transaction, please provide Transaction ID, Date, Amount, Description, Risk Level (Low/Medium/High), and Status (Approved/Pending/Rejected)."
    elif "transaction" in user_message and "view" in user_message:
        bot_reply = "You can view transactions in the left panel. Would you like to filter by risk level or status?"

    # Handle deadlines queries
    elif "deadline" in user_message and "add" in user_message:
        bot_reply = "Please provide the due date, a brief description, and the status (Open/Closed) to add a deadline."
    elif "deadline" in user_message and "view" in user_message:
        bot_reply = "Audit deadlines are displayed in the calendar section. Do you want to add a new one?"

    # Personalized greetings based on time
    elif "good morning" in user_message:
        bot_reply = "Good morning! How can I help you today?"
    elif "good afternoon" in user_message:
        bot_reply = "Good afternoon! What would you like to do?"
    elif "good evening" in user_message:
        bot_reply = "Good evening! Need assistance with something?"

    # Check predefined responses
    else:
        bot_reply = responses.get(user_message, "I'm not sure about that. Could you clarify or ask in a different way?")

    return jsonify({"reply": bot_reply})



# -------------------- Add transactions --------------------

@app.route("/api/add-transaction", methods=["POST"])
def add_transaction():
    data = request.json
    transaction_id = data.get("transaction_id")
    date = data.get("date")
    amount = data.get("amount")
    description = data.get("description")
    risk = data.get("risk")
    status = data.get("status")

    try:
        with engine.connect() as conn:
            # Insert the new transaction into the database
            conn.execute(text("""
                INSERT INTO transactions (transaction_id, date, amount, description, risk, status)
                VALUES (:transaction_id, :date, :amount, :description, :risk, :status)
            """), {
                "transaction_id": transaction_id,
                "date": date,
                "amount": amount,
                "description": description,
                "risk": risk,
                "status": status
            })
            conn.commit()  # Commit the transaction
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
# -------------------- risk heatmap --------------------

@app.route("/api/risk-data", methods=["GET"])
def get_risk_data():
    try:
        with engine.connect() as conn:
            # Count transactions by risk level
            result = conn.execute(text("""
                SELECT risk, COUNT(*) as count
                FROM transactions
                GROUP BY risk
            """))
            
            # Convert the result into a dictionary
            risk_counts = {row[0]: row[1] for row in result}

            # Default counts if no data exists
            high = risk_counts.get('High', 0)
            medium = risk_counts.get('Medium', 0)
            low = risk_counts.get('Low', 0)

            return jsonify({
                "high": high,
                "medium": medium,
                "low": low
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500    


# -------------------- counts for every box--------------------

@app.route("/api/get-counts", methods=["GET"])
def get_counts():
    with engine.connect() as conn:
        pending = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE status = 'Pending'")).scalar()
        rejected = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE status = 'Rejected'")).scalar()
        approved = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE status = 'Approved'")).scalar()
        high_risk = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE risk = 'High'")).scalar()
        medium_risk = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE risk = 'Medium'")).scalar()
        low_risk = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE risk = 'Low'")).scalar()
        present_year = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE YEAR(date) = YEAR(CURDATE())")).scalar()
        previous_year = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE YEAR(date) = YEAR(CURDATE()) - 1")).scalar()
        previous_to_previous_year = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE YEAR(date) = YEAR(CURDATE()) - 2")).scalar()

        return jsonify({
            "pending": pending,
            "rejected": rejected,
            "approved": approved,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "present_year": present_year,
            "previous_year": previous_year,
            "previous_to_previous_year": previous_to_previous_year
        })
    
# -------------------- Main --------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
