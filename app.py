import os
# import MySQLdb
from urllib.parse import quote_plus
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from datetime import datetime


app = Flask(__name__)
CORS(app)


password = quote_plus("baps@1907")
# Configure Database (Use PostgreSQL, MySQL, or SQLite)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:hammesh2005@localhost:3306/compliance_db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://root:{password}@127.0.0.1:3306/acms?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = "your_secret_key"

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Policy Model (for storing uploaded policies)
class Policy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_compliant = db.Column(db.Boolean, default=True)
    uploaded_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create Tables
with app.app_context():
    db.create_all()

# Home Page
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

# Upload Page
@app.route("/upload", methods=["GET"])
def upload():
    return render_template("upload.html")

# Compliance Page
@app.route("/compliance", methods=["GET"])
def compliance():
    return render_template("compliance.html")

# About Page
@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html")

# Contact Page
@app.route("/contact", methods=["GET"])
def contact():
    return render_template("contact.html")

# User Registration
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"message": "User already exists"}), 400
    new_user = User(username=data["username"], password=data["password"])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201

# User Login
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data["username"], password=data["password"]).first()
    if not user:
        return jsonify({"message": "Invalid Credentials"}), 401
    token = create_access_token(identity=user.username)
    return jsonify(access_token=token)

# Upload Policy
@app.route("/upload_policy", methods=["POST"])
@jwt_required()
def upload_policy():
    current_user = get_jwt_identity()
    data = request.json
    new_policy = Policy(title=data["title"], content=data["content"], uploaded_by=current_user)

    # Simple Compliance Check (Example)
    if "fraud" in data["content"].lower():
        new_policy.is_compliant = False

    db.session.add(new_policy)
    db.session.commit()

    return jsonify({"message": "Policy uploaded successfully", "compliant": new_policy.is_compliant})

# View Compliance Reports
@app.route("/compliance_report", methods=["GET"])
@jwt_required()
def compliance_report():
    policies = Policy.query.all()
    report = [
        {
            "title": p.title,
            "is_compliant": p.is_compliant,
            "uploaded_by": p.uploaded_by,
            "created_at": p.created_at
        } for p in policies
    ]
    return jsonify(report)

# Analytics Insight
@app.route("/analytics", methods=["GET"])
@jwt_required()
def analytics():
    total_policies = Policy.query.count()
    non_compliant = Policy.query.filter_by(is_compliant=False).count()
    compliant = total_policies - non_compliant
    return jsonify({
        "total_policies": total_policies,
        "compliant_policies": compliant,
        "non_compliant_policies": non_compliant
    })

if __name__ == "__main__":
    app.run(debug=True)