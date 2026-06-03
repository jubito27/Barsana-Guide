from flask import Flask, request, jsonify , render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS # Frontend se connect karne ke liye
import os
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

# --- SQLite Database Configuration ---
# Yeh aapke project folder mein 'brij_guide.db' naam ki file automatic bana dega
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'brij_guide.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model (Table structure)
class UserRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # --- User Personal Details ---
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    
    # --- Page 2: Guide & Package Choices ---
    selected_guide = db.Column(db.String(100))   # Pandit Rajesh, etc.
    package_type = db.Column(db.String(50))     # Guide+Taxi, Full Package, etc.
    selected_places = db.Column(db.Text)        # Barsana (Kirti Mandir), etc.
    free_addons = db.Column(db.Text)            # Prasad, Tulsi Mala
    
    # --- Other Details ---
    visit_date = db.Column(db.String(20))
    members = db.Column(db.Integer, default=1)
    city = db.Column(db.String(50))

# Table create karne ke liye (Agar file nahi bani hogi toh automatic ban jayegi)
with app.app_context():
    db.create_all()
    
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    
    try:
        # Khali values ko handle karne ke liye logic
        def clean_int(val):
            try:
                return int(val) if val else 0
            except:
                return 0

        new_user = UserRegistration(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            city=data.get('city', ''),
            visit_date=data.get('visitDate', ''),
            members=clean_int(data.get('noOfMembers')),
            selected_places=data.get('placesInterested', ''),
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Radhe Radhe! Data saved successfully!"}), 201
    except Exception as e:
        print(f"Error: {e}") # Debugging ke liye terminal pe error dikhega
        return jsonify({"error": str(e)}), 400
    
@app.route('/save-booking', methods=['POST'])
def save_booking():
    data = request.json
    try:
        user_email = data.get('email')
        user = UserRegistration.query.filter_by(email=user_email).first()

        if user:
            user.selected_guide = data.get('guideName')
            user.package_type = data.get('package')
            user.selected_places = ", ".join(data.get('places', []))
            user.free_addons = ", ".join(data.get('addons', []))
            
            db.session.commit()
            return jsonify({"message": "Radhe Radhe! Aapki choices save ho gayi hain."}), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route('/get-user-data/<email>', methods=['GET'])
def get_user_data(email):
    try:
        user = UserRegistration.query.filter_by(email=email).first()
        if user:
            return jsonify({
                "status": "success",
                "name": user.name,
                "guide": user.selected_guide,
                "package": user.package_type,
                "places": user.selected_places,
                "addons": user.free_addons
            }), 200
        else:
            return jsonify({"status": "error", "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/braj_user/', methods=['GET'])
def get_all_users():
    try:
        users = UserRegistration.query.all()
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "city": user.city,
                "visit_date": user.visit_date,
                "members": user.members,
                "selected_guide": user.selected_guide,
                "package_type": user.package_type,
                "selected_places": user.selected_places,
                "free_addons": user.free_addons
            })
        return jsonify(user_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Temp dictionary OTP aur Email track karne ke liye
otp_store = {}

# Email Sending Function
def send_email_otp(receiver_email, otp_code):
    sender_email = "abhishek.sharma1008as@gmail.com"  # Aapka Gmail yahan aayega
    sender_password = "abhishek12345@"  # Gmail ka 16-digit App Password

    msg = MIMEText(f"Radhe Radhe! BrijGuide login ke liye aapka OTP hai: {otp_code}\nYeh OTP 5 minute ke liye valid hai.")
    msg['Subject'] = 'BrijGuide Login OTP'
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Mail sending error: {e}")
        return False

# --- ROUTES ---

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    
    # 1. DB mein check karein ki email exist karta hai ya nahi
    user = UserRegistration.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Yeh email registered nahi hai! Kripya pehle register karein."}), 404
    
    # 2. Generate 6 digit OTP
    otp = str(random.randint(100000, 999909))
    otp_store[email] = otp  # Save to memory
    
    # 3. Email send karein
    if send_email_otp(email, otp):
        return jsonify({"message": f"Radhe Radhe {user.name}! OTP aapke mail par bhej diya gaya hai."}), 200
    else:
        # Development bypass: Agar email config na ho toh testing ke liye terminal par OTP print kar lo
        print(f"DEVELOPMENT OTP FOR {email}: {otp}")
        return jsonify({"message": "OTP generated! (Check backend terminal for OTP if Email config missing)"}), 200

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    submitted_otp = data.get('otp')
    
    # Check memory for OTP match
    if email in otp_store and otp_store[email] == submitted_otp:
        del otp_store[email] # Clear OTP after verification
        
        # --- NAYA LOGIC: Database se user ka saara data nikalein ---
        user = UserRegistration.query.filter_by(email=email).first()
        
        if user:
            return jsonify({
                "message": "Success",
                "user_data": {
                    "name": user.name,
                    "email": user.email,
                    "phone": user.phone,
                    "city": user.city,
                    "visit_date": user.visit_date,
                    "members": user.members,
                    "guide": user.selected_guide,
                    "package": user.package_type,
                    "places": user.selected_places,
                    "addons": user.free_addons
                }
            }), 200
        else:
            return jsonify({"error": "User found in OTP store but missing in DB!"}), 404
            
    else:
        return jsonify({"error": "Invalid or expired OTP!"}), 400
    

@app.route('/')
def home():
    # Agar aapka main home page index.html hai
    return render_template('index.html')

@app.route('/registeration')
def registration_page():
    return render_template('registeration.html')

@app.route('/account')
def account_page():
    return render_template('./templates/account.html')

@app.route('/radharani')
def radharani():
    return render_template('radhaRani.html')

@app.route('/maangarh')
def maangarh():
    return render_template('maangarh.html')

@app.route('/dangarh')
def dangarh():
    return render_template('dangarh.html')

@app.route('/vilasgarh')
def vilasgarh():
    return render_template('vilasgarh.html')

@app.route('/morkuti')
def morkuti():
    return render_template('morkuti.html')

@app.route('/kushalbihari')
def kushalbihari():
    return render_template('kushalbihari.html')

@app.route('/chitrasakhi')
def chitrasakhi():
    return render_template('chitrasakhi.html')

@app.route('/gehvarvan')
def gehvarvan():
    return render_template('gehvarvan.html')

@app.route('/radhaBagh')
def radhaBagh():
    return render_template('radhaBagh.html')

@app.route('/krishnaBagh')
def krishnaBagh():
    return render_template('krishnaBagh.html')

@app.route('/priyakund')
def priyakund():
    return render_template('priyakund.html')

@app.route('/sankrikhor')
def sankrikhor():
    return render_template('sankrikhor.html')

@app.route('/rangiligali')
def rangiligali():
    return render_template('rangiligali.html')

@app.route('/vinodbaba')
def vinodbaba():
    return render_template('vinodbaba.html')

@app.route('/rameshbabagaushala')
def rameshbabagaushala():
    return render_template('rameshbabagaushala.html')

@app.route('/brishbhanugaushala')
def brishbhanugaushala():
    return render_template('brishbhanugaushala.html')

@app.route('/108kutiya')
def kutiya():
    return render_template('108kutiya.html')

@app.route('/aboutme')
def aboutme():
    return render_template('aboutme.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/guidecard')
def guidecard():
    return render_template('guidecard.html')

@app.route('/guidebooking')
def guidebooking():
    return render_template('guidebooking.html')

@app.route('/live3')
def live3():
    return render_template('live3.html')

if __name__ == '__main__':
    app.run(debug=True)