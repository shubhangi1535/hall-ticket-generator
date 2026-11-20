import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
import qrcode

# Initialize Flask App
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hall_ticket_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secure_secret_key'  # Replace with a secure key
db = SQLAlchemy(app)

# Ensure the hall_tickets directory exists
os.makedirs("hall_tickets", exist_ok=True)

### MODELS ###
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)  
    designation = db.Column(db.String(100), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    course = db.Column(db.String(100), nullable=False)

### QR CODE GENERATION ###
def generate_qr_code(data, file_path):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    img.save(file_path)

### HALL TICKET GENERATION ###
def generate_hall_ticket(student, base_url):
    qr_file = f"hall_tickets/{student.roll_number}_qr.png"
    pdf_file = f"hall_tickets/{student.roll_number}_hall_ticket.pdf"
    qr_data = f"{base_url}/verify?roll_number={student.roll_number}"
    
    try:
        # Generate the QR code
        generate_qr_code(qr_data, qr_file)
        
        # Subjects for the hall ticket
        subjects = ["Mathematics", "Physics", "Chemistry", "Computer Science"]
        
        # Create the PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Add header
        pdf.set_font("Arial", style="B", size=16)
        pdf.cell(200, 10, txt="GRAPHIC ERA DEEMED TO BE UNIVERSITY", ln=True, align="C")
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(200, 10, txt="Mid-Term Examination Admit Card", ln=True, align="C")
        pdf.ln(10)
        
        # Add a dividing line
        pdf.set_draw_color(0, 0, 0)  # Black color
        pdf.set_line_width(0.5)
        pdf.line(10, 40, 200, 40)
        pdf.ln(10)
        
        # Add student details in a bordered box
        pdf.set_font("Arial", size=12)
        pdf.set_fill_color(220, 220, 220)  # Light gray background
        pdf.cell(190, 10, txt="Student Details", ln=True, align="C", fill=True)
        pdf.set_font("Arial", size=12)
        pdf.cell(95, 10, txt=f"Roll Number: {student.roll_number}", ln=0)
        pdf.cell(95, 10, txt=f"Name: {student.name}", ln=1)
        pdf.cell(95, 10, txt=f"Course: {student.course}", ln=0)
        pdf.ln(15)
        
        # Add subject table
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(190, 10, txt="Subjects", ln=True, align="C", fill=True)
        pdf.set_font("Arial", size=12)
        for idx, subject in enumerate(subjects, start=1):
            pdf.cell(10, 10, txt=f"{idx}.", border=1, align="C")
            pdf.cell(180, 10, txt=subject, border=1)
            pdf.ln(10)
        pdf.ln(10)
        
        # Add QR code
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, txt="Scan the QR code to verify the details", ln=True, align="C")
        pdf.image(qr_file, x=80, y=130, w=50)
        pdf.ln(60)
        
        # Footer acknowledgment
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, txt="Note: This is a system-generated admit card. Please carry a valid ID proof to the examination hall.", ln=True, align="C")
        
        pdf.output(pdf_file)
    finally:
        # Delete the QR code file after creating the PDF
        if os.path.exists(qr_file):
            os.remove(qr_file)
    
    return pdf_file


### ROUTES ###

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_id = request.form["id"]
        name = request.form["name"]
        password = request.form["password"]
        designation = request.form["designation"]

        # Check if the ID already exists in the database
        existing_user = User.query.filter_by(id=user_id).first()
        if existing_user:
            flash("The ID already exists. Please choose a different ID.", "danger")
            return redirect(url_for("register"))

        # Store the plain password 
        new_user = User(id=user_id, name=name, password=password, designation=designation)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("home"))


    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form["id"]
        password = request.form["password"]
        designation = request.form["designation"]

        # Check credentials
        user = User.query.filter_by(id=user_id, password=password, designation=designation).first()
        if user:  
            # Set session variables
            session["user_id"] = user.id
            session["designation"] = user.designation
            session["name"] = user.name

            # Redirect to dashboard based on designation
            if designation == "student":
                return redirect(url_for("student_dashboard"))
            elif designation == "examiner":
                return redirect(url_for("examiner_dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/student", methods=["GET", "POST"])
def student_dashboard():
    # Ensure user is logged in and is a student
    if "user_id" not in session or session["designation"] != "student":
        flash("Access denied! Please log in as a student.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"]
        roll_number = request.form["roll_number"]
        course = request.form["course"]

        if Student.query.filter_by(roll_number=roll_number).first():
            flash("Roll number already exists!", "danger")
            return redirect(url_for("student_dashboard"))

        # Add student and generate hall ticket
        student = Student(name=name, roll_number=roll_number, course=course)
        db.session.add(student)
        db.session.commit()

        base_url = request.url_root.strip("/")
        pdf_file = generate_hall_ticket(student, base_url)
        flash("Hall ticket generated successfully!", "success")
        return send_file(pdf_file, as_attachment=True)

    return render_template("student_dashboard.html", name=session.get("name"))

@app.route("/examiner", methods=["GET", "POST"])
def examiner_dashboard():
    if "user_id" not in session or session["designation"] != "examiner":
        flash("Access denied! Please log in as an examiner.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        roll_number = request.form["roll_number"]
        student = Student.query.filter_by(roll_number=roll_number).first()
        if student:
            return render_template("verify.html", student=student)
        flash("Invalid roll number!", "danger")

    return render_template("examiner_dashboard.html", name=session.get("name"))

@app.route("/verify", methods=["GET"])
def verify():
    roll_number = request.args.get("roll_number")
    if not roll_number:
        flash("Roll Number is required!", "danger")
        return redirect(url_for("home"))

    student = Student.query.filter_by(roll_number=roll_number).first()
    if student:
        return render_template("verify.html", student=student)

    flash("Invalid Roll Number!", "danger")
    return render_template("verify.html", student=None)

### MAIN ###
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)