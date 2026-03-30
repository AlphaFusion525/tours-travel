

# ===============================
# 📧 EMAIL CONFIGURATION
# ===============================
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USERNAME'] = 'pradnyakadam489@gmail.com'   # your Gmail
# app.config['MAIL_PASSWORD'] = 'qbvt jysv gjlm ffgc'          # your App Password
# app.config['MAIL_DEFAULT_SENDER'] = ('ShivaSamarth Tours', 'pradnyakadam489@gmail.com')


from flask import Flask, request, jsonify, send_from_directory
from flask_mail import Mail, Message
import sqlite3, os
from datetime import datetime, timedelta

app = Flask(__name__)

# ===============================
# 📧 EMAIL CONFIG (IMPORTANT)
# ===============================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'pradnyakadam489@gmail.com'

# 👉 PUT YOUR NEW APP PASSWORD HERE (NOT OLD ONE)
app.config['MAIL_PASSWORD'] = 'qbvt jysv gjlm ffgc'

app.config['MAIL_DEFAULT_SENDER'] = ('ShivaSamarth Tours', 'pradnyakadam489@gmail.com')

mail = Mail(app)

# ===============================
# 🗃️ DATABASE
# ===============================
DB_FILE = "booking.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Tour bookings
    c.execute("""
        CREATE TABLE IF NOT EXISTS tour_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            destination TEXT,
            travelers INTEGER,
            travel_date TEXT,
            booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Hotel bookings
    c.execute("""
        CREATE TABLE IF NOT EXISTS hotel_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            hotel_name TEXT,
            checkin TEXT,
            checkout TEXT,
            guests INTEGER,
            booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Hotels
    c.execute("""
        CREATE TABLE IF NOT EXISTS hotel_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT UNIQUE,
            total_rooms INTEGER,
            speciality TEXT
        )
    """)

    hotels = [
        ("Hotel Sunrise", 10, "Near temple • AC Rooms • Free breakfast"),
        ("Hotel Galaxy", 8, "Budget-friendly • Family rooms"),
        ("Hotel Paradise", 12, "Luxury • Rooftop • WiFi")
    ]

    for h in hotels:
        c.execute("INSERT OR IGNORE INTO hotel_availability VALUES (NULL,?,?,?)", h)

    conn.commit()
    conn.close()

init_db()

MAX_PASSENGERS_PER_TOUR = 40

# ===============================
# 🌍 ROUTES
# ===============================

@app.route('/')
def home():
    return send_from_directory('.', 'home.html')

@app.route('/hotel')
def hotel_page():
    return send_from_directory('.', 'hotel.html')

@app.route('/images/<path:filename>')
def images(filename):
    return send_from_directory('images', filename)

# ===============================
# 🚐 TOUR
# ===============================

@app.route('/tourcheck')
def tour_check():
    dest = request.args.get('dest')
    date_ = request.args.get('date')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT SUM(travelers) FROM tour_bookings WHERE destination=? AND travel_date=?", (dest, date_))
    booked = c.fetchone()[0] or 0
    conn.close()

    remaining = MAX_PASSENGERS_PER_TOUR - booked

    return jsonify({
        "available": remaining > 0,
        "slots_left": remaining
    })


@app.route('/book', methods=['POST'])
def book():
    f = request.form
    name = f['name']
    email = f['email']
    phone = f['phone']
    dest = f['destination']
    travelers = int(f['travelers'])
    travel_date = f['travel_date']

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT SUM(travelers) FROM tour_bookings WHERE destination=? AND travel_date=?", (dest, travel_date))
    booked = c.fetchone()[0] or 0

    if booked + travelers > MAX_PASSENGERS_PER_TOUR:
        conn.close()
        return "<h3 style='color:red;text-align:center;'>❌ Tour Full</h3>"

    c.execute("INSERT INTO tour_bookings (name,email,phone,destination,travelers,travel_date) VALUES (?,?,?,?,?,?)",
              (name,email,phone,dest,travelers,travel_date))
    conn.commit()
    conn.close()

    # EMAIL
    send_email(
        "🚌 Tour Booking Confirmed",
        f"""
Hello {name},

✅ Your tour is booked!

Destination: {dest}
Date: {travel_date}
Travelers: {travelers}

Thank you 🙏
""",
        email
    )

    return f"<h3 style='color:green;text-align:center;'>✅ Booking Confirmed for {dest}</h3>"

# ===============================
# 🏨 HOTEL
# ===============================

@app.route('/hotelbook', methods=['POST'])
def hotel_book():
    f = request.form
    name = f['name']
    email = f['email']
    phone = f['phone']
    hotel = f['hotel_name']
    checkin = f['checkin']
    checkout = f['checkout']
    guests = int(f['guests'])

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT total_rooms FROM hotel_availability WHERE hotel_name=?", (hotel,))
    total = c.fetchone()['total_rooms']

    start = datetime.strptime(checkin, "%Y-%m-%d")
    end = datetime.strptime(checkout, "%Y-%m-%d")

    current = start
    while current < end:
        d = current.strftime("%Y-%m-%d")
        c.execute("SELECT SUM(guests) FROM hotel_bookings WHERE hotel_name=? AND checkin=?", (hotel, d))
        booked = c.fetchone()[0] or 0

        if booked + guests > total:
            conn.close()
            return "<h3 style='color:red;text-align:center;'>❌ Not Available</h3>"

        current += timedelta(days=1)

    c.execute("INSERT INTO hotel_bookings (name,email,phone,hotel_name,checkin,checkout,guests) VALUES (?,?,?,?,?,?,?)",
              (name,email,phone,hotel,checkin,checkout,guests))
    conn.commit()
    conn.close()

    # EMAIL
    send_email(
        "🏨 Hotel Booking Confirmed",
        f"""
Hello {name},

✅ Your hotel is booked!

Hotel: {hotel}
Check-in: {checkin}
Check-out: {checkout}
Guests: {guests}

Enjoy 😊
""",
        email
    )

    return f"<h3 style='color:green;text-align:center;'>✅ Hotel Booked</h3>"

# ===============================
# 📧 EMAIL FUNCTION
# ===============================

def send_email(subject, body, user_email):
    try:
        msg = Message(
            subject=subject,
            recipients=[user_email, 'pradnyakadam489@gmail.com'],
            body=body
        )
        mail.send(msg)
        print("✅ Email Sent")
    except Exception as e:
        print("❌ Email Error:", e)

@app.route('/all_users')
def all_users():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM tour_bookings")
    tours = c.fetchall()

    c.execute("SELECT * FROM hotel_bookings")
    hotels = c.fetchall()

    conn.close()

    html = "<h2 style='text-align:center;'>📊 All Bookings</h2>"

    # Tour Table
    html += "<h3>🚐 Tour Bookings</h3>"
    html += "<table border='1' cellpadding='8'>"
    html += "<tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Destination</th><th>Travelers</th><th>Date</th></tr>"

    for r in tours:
        html += "<tr>" + "".join([f"<td>{x}</td>" for x in r]) + "</tr>"

    html += "</table><br>"

    # Hotel Table
    html += "<h3>🏨 Hotel Bookings</h3>"
    html += "<table border='1' cellpadding='8'>"
    html += "<tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Hotel</th><th>Checkin</th><th>Checkout</th><th>Guests</th></tr>"

    for r in hotels:
        html += "<tr>" + "".join([f"<td>{x}</td>" for x in r]) + "</tr>"

    html += "</table>"

    return html
# ===============================
# 🌍 DESTINATION FULL FEATURE
# ===============================

DESTINATIONS = {
    "kerala": {
        "about": "Kerala is a beautiful state known as God's Own Country. It has greenery, backwaters and hill stations. It is perfect for relaxing and nature lovers.",
        "places": ["Munnar", "Alleppey", "Wayanad", "Kochi"],
        "dance": ["Kathakali", "Mohiniyattam"],
        "entertainment": ["Houseboat ride", "Cultural shows", "Local food experience"],
        "games": ["Beach games", "Boat racing", "Outdoor games"]
    },

    "goa": {
        "about": "Goa is famous for beaches, nightlife and fun activities. It is one of the best places for friends and parties.",
        "places": ["Baga Beach", "Calangute", "Fort Aguada", "Dudhsagar Falls"],
        "dance": ["Goan folk dance"],
        "entertainment": ["Night party", "Live music", "Beach relaxation"],
        "games": ["Water sports", "Beach volleyball"]
    }
}


@app.route('/destination/<place>', methods=['GET', 'POST'])
def destination(place):
    data = DESTINATIONS.get(place)
    plan_html = ""

    # Convert lists to HTML
    places_html = "".join([f"<li>{p}</li>" for p in data["places"]])
    dance_html = "".join([f"<li>{d}</li>" for d in data["dance"]])
    entertainment_html = "".join([f"<li>{e}</li>" for e in data["entertainment"]])
    games_html = "".join([f"<li>{g}</li>" for g in data["games"]])

    # PLAN LOGIC
    if request.method == 'POST':
        days = int(request.form.get('days'))

        plan_html += "<h2>🗺️ Your Travel Plan</h2>"

        for i in range(days):
            if i < len(data["places"]):
                place_name = data["places"][i]
                activity = data["entertainment"][i % len(data["entertainment"])]
            else:
                place_name = "Explore nearby / Rest"
                activity = "Enjoy local culture"

            plan_html += f"""
            <p>
            <b>Day {i+1}</b> → {place_name}<br>
            👉 {activity}
            </p>
            """

    return f"""
    <html>
    <head>
        <title>{place}</title>
        <style>
            body {{ font-family: Arial; background:#f5f5f5; padding:20px; }}
            .box {{ background:white; padding:20px; border-radius:10px; max-width:700px; margin:auto; }}
            li {{ background:#eee; margin:5px; padding:8px; border-radius:5px; }}
            button {{ padding:10px; background:orange; color:white; border:none; }}
        </style>
    </head>

    <body>

    <div class="box">

    <h1>{place.capitalize()}</h1>

    <h2>📌 About</h2>
    <p>{data['about']}</p>

    <h2>📍 Places to Visit</h2>
    <ul>{places_html}</ul>

    <h2>💃 Popular Dance</h2>
    <ul>{dance_html}</ul>

    <h2>🎉 Entertainment</h2>
    <ul>{entertainment_html}</ul>

    <h2>🎮 Games</h2>
    <ul>{games_html}</ul>

    <hr>

    <h2>Enter Number of Days</h2>
    <form method="POST">
        <input type="number" name="days" required>
        <button>Generate Plan</button>
    </form>

    {plan_html}

    </div>

    </body>
    </html>
    """
# ===============================
# 🚀 RUN
# ===============================

if __name__ == "__main__":
    app.run(debug=True)

