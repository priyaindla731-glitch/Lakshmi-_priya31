import os
import json
import uuid
import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from backend.database import get_db, init_db, hash_password, verify_password, is_legacy_password_hash
from backend.auth import create_token, require_auth, decode_token, revoke_token, rate_limit_auth_attempt

# Ensure database is initialized
init_db()

app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
CORS(app)

# Helper to serialize sqlite3.Row objects to dict
def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def _request_data():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}

def _auth_rate_limit_response(action, limit):
    retry_after = rate_limit_auth_attempt(action, limit)
    if not retry_after:
        return None
    response = jsonify({"error": "Too many attempts. Please wait before trying again."})
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response

def _event_access(conn, current_user, event_id, allow_vendor=False, edit=False):
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        return None, (jsonify({"error": "Event not found"}), 404)
    if current_user["role"] == "admin" or event["customer_id"] == current_user["id"]:
        return event, None

    email = (current_user.get("email") or "").lower()
    collaborator = conn.execute(
        "SELECT permission FROM event_collaborators WHERE event_id = ? AND LOWER(collaborator_email) = ?",
        (event_id, email),
    ).fetchone() if email else None
    if collaborator and (not edit or collaborator["permission"] == "co_planner_edit"):
        return event, None

    if allow_vendor and current_user["role"] == "vendor":
        vendor = conn.execute(
            "SELECT id FROM vendor_profiles WHERE user_id = ?",
            (current_user["id"],),
        ).fetchone()
        if vendor:
            booking = conn.execute(
                "SELECT 1 FROM bookings WHERE event_id = ? AND vendor_id = ? AND booking_status = 'confirmed'",
                (event_id, vendor["id"]),
            ).fetchone()
            if booking:
                return event, None

    return None, (jsonify({"error": "You do not have permission to access this event."}), 403)

# -------------------------------------------------------------
# 1. AUTHENTICATION & ONBOARDING
# -------------------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
def register():
    limited = _auth_rate_limit_response("register", 5)
    if limited:
        return limited

    data = _request_data()
    fields = ("email", "phone", "password", "full_name", "role", "preferred_language")
    if any(key in data and not isinstance(data[key], str) for key in fields):
        return jsonify({"error": "Registration fields must be text values."}), 400
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    password = data.get("password", "").strip()
    full_name = data.get("full_name", "").strip()
    role = data.get("role", "customer").strip().lower()
    lang = data.get("preferred_language", "en")

    if not full_name or not password or (not email and not phone):
        return jsonify({"error": "Full name, password, and email or phone are required."}), 400
    if len(full_name) > 120 or len(email) > 254 or len(phone) > 32:
        return jsonify({"error": "One or more registration fields exceed the allowed length."}), 400
    if len(password) < 12 or len(password) > 1024:
        return jsonify({"error": "Password must be at least 12 characters long."}), 400

    business_name = data.get("business_name") or full_name
    category = data.get("category") or "photography"
    cities = data.get("cities") or "Hyderabad"
    if role == "vendor":
        if not all(isinstance(value, str) for value in (business_name, category, cities)):
            return jsonify({"error": "Vendor profile fields must be text values."}), 400
        if len(business_name) > 160 or len(category) > 80 or len(cities) > 255:
            return jsonify({"error": "One or more vendor profile fields exceed the allowed length."}), 400

    if role not in ["customer", "vendor"]:
        return jsonify({"error": "Registration is available for customer or vendor accounts only."}), 400
    if lang not in ("en", "te", "hi"):
        return jsonify({"error": "Unsupported preferred language."}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Check existing
    if email:
        existing = cursor.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            return jsonify({"error": "An account with this email already exists."}), 400
    if phone:
        existing = cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
        if existing:
            conn.close()
            return jsonify({"error": "An account with this phone already exists."}), 400

    pwd_hash = hash_password(password)
    cursor.execute('''
    INSERT INTO users (email, phone, password_hash, full_name, role, preferred_language)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (email or None, phone or None, pwd_hash, full_name, role, lang))
    user_id = cursor.lastrowid

    # If vendor, create initial vendor profile
    if role == "vendor":
        cursor.execute('''
        INSERT INTO vendor_profiles (user_id, business_name, category, cities, bio_en)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, business_name, category, cities, "New registered event service provider."))

    # Welcome notification
    cursor.execute('''
    INSERT INTO notifications (user_id, title, message, category)
    VALUES (?, 'Welcome to Veduka AI!', 'Your account has been created. Start planning your celebrations or managing your services.', 'welcome')
    ''', (user_id,))

    conn.commit()
    conn.close()

    token = create_token(user_id, role, email or phone, full_name)
    return jsonify({
        "message": "Registration successful!",
        "token": token,
        "user": {
            "id": user_id,
            "email": email,
            "phone": phone,
            "full_name": full_name,
            "role": role,
            "preferred_language": lang
        }
    }), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    limited = _auth_rate_limit_response("login", 10)
    if limited:
        return limited

    data = _request_data()
    identifier = data.get("identifier", "")
    password = data.get("password", "")
    if not isinstance(identifier, str) or not isinstance(password, str):
        return jsonify({"error": "Please provide your email/phone and password."}), 400
    identifier = identifier.strip().lower()
    password = password.strip()

    if not identifier or not password:
        return jsonify({"error": "Please provide your email/phone and password."}), 400
    if len(identifier) > 254 or len(password) > 1024:
        return jsonify({"error": "Please provide your email/phone and password."}), 400

    conn = get_db()
    user = conn.execute('''
    SELECT id, email, phone, password_hash, full_name, role, preferred_language, high_contrast, speech_speed
    FROM users
    WHERE LOWER(email) = ? OR phone = ?
    ''', (identifier, identifier)).fetchone()
    if user and verify_password(user["password_hash"], password) and is_legacy_password_hash(user["password_hash"]):
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user["id"]))
        conn.commit()
    if not user or not verify_password(user["password_hash"], password):
        user = None
    conn.close()

    if not user:
        return jsonify({"error": "Invalid login credentials. Please check your phone/email and password."}), 401

    u = dict(user)
    u.pop("password_hash", None)
    token = create_token(u["id"], u["role"], u["email"] or u["phone"], u["full_name"])
    return jsonify({
        "message": "Login successful!",
        "token": token,
        "user": u
    })

@app.route("/api/auth/logout", methods=["POST"])
@require_auth()
def logout(current_user):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        return jsonify({"error": "Authentication token is missing or invalid. Please log in."}), 401
    revoke_token(token, payload)
    return jsonify({"message": "Logged out successfully."})

@app.route("/api/auth/me", methods=["GET"])
@require_auth()
def get_me(current_user):
    conn = get_db()
    vendor_profile = None
    if current_user["role"] == "vendor":
        vp = conn.execute("SELECT * FROM vendor_profiles WHERE user_id = ?", (current_user["id"],)).fetchone()
        vendor_profile = row_to_dict(vp)
    conn.close()

    return jsonify({
        "user": current_user,
        "vendor_profile": vendor_profile
    })

@app.route("/api/auth/switch-role", methods=["POST"])
@require_auth()
def switch_role(current_user):
    data = _request_data()
    new_role = data.get("role", "customer")
    if not isinstance(new_role, str):
        return jsonify({"error": "Invalid role"}), 400
    new_role = new_role.lower()
    if new_role == "admin":
        return jsonify({"error": "Administrator access can only be assigned by an authorized administrator."}), 403
    if new_role not in ["customer", "vendor"]:
        return jsonify({"error": "Invalid role"}), 400
    if current_user["role"] == "admin":
        return jsonify({"error": "Administrator accounts cannot switch roles."}), 403

    conn = get_db()
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, current_user["id"]))
    
    # Check if vendor profile exists
    if new_role == "vendor":
        existing_vp = conn.execute("SELECT id FROM vendor_profiles WHERE user_id = ?", (current_user["id"],)).fetchone()
        if not existing_vp:
            conn.execute('''
            INSERT INTO vendor_profiles (user_id, business_name, category, cities, bio_en)
            VALUES (?, ?, 'photography', 'Hyderabad', 'Event professional.')
            ''', (current_user["id"], current_user["full_name"]))
            
    conn.commit()
    conn.close()

    token = create_token(current_user["id"], new_role, current_user["email"], current_user["full_name"])
    return jsonify({
        "message": f"Switched role to {new_role}",
        "token": token,
        "new_role": new_role
    })

@app.route("/api/auth/update-settings", methods=["POST"])
@require_auth()
def update_settings(current_user):
    data = request.json or {}
    lang = data.get("preferred_language", current_user.get("preferred_language", "en"))
    contrast = 1 if data.get("high_contrast") else 0
    speed = float(data.get("speech_speed", 1.0))

    conn = get_db()
    conn.execute('''
    UPDATE users SET preferred_language = ?, high_contrast = ?, speech_speed = ?
    WHERE id = ?
    ''', (lang, contrast, speed, current_user["id"]))
    conn.commit()
    conn.close()

    return jsonify({"message": "Settings updated successfully", "preferred_language": lang, "high_contrast": contrast, "speech_speed": speed})

@app.route("/api/auth/delete-account", methods=["POST"])
@require_auth()
def delete_account(current_user):
    conn = get_db()
    cursor = conn.cursor()
    # Ensure no active confirmed bookings
    active_b = cursor.execute('''
    SELECT COUNT(*) FROM bookings 
    WHERE (customer_id = ? OR vendor_id IN (SELECT id FROM vendor_profiles WHERE user_id = ?))
      AND booking_status = 'confirmed'
    ''', (current_user["id"], current_user["id"])).fetchone()[0]

    if active_b > 0:
        conn.close()
        return jsonify({"error": "Cannot delete account with active confirmed bookings. Please complete or cancel bookings first."}), 400

    cursor.execute("DELETE FROM users WHERE id = ?", (current_user["id"],))
    conn.commit()
    conn.close()
    return jsonify({"message": "Your account and personal data have been permanently deleted."})

# -------------------------------------------------------------
# 2. VENDORS & CATALOG (DISCOVERY & TRANSPARENT PRICING)
# -------------------------------------------------------------
@app.route("/api/vendors", methods=["GET"])
def list_vendors():
    category = request.args.get("category", "all")
    city = request.args.get("city", "All Cities")
    search = request.args.get("q", "").strip().lower()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    min_rating = request.args.get("min_rating", type=float)

    query = '''
    SELECT vp.id, vp.business_name, vp.category, vp.cities, vp.service_radius_km,
           vp.kyc_verified, vp.rating_avg, vp.review_count, vp.bio_en, vp.bio_te,
           vp.bio_hi, vp.image_url, vp.response_time
    FROM vendor_profiles vp
    JOIN users u ON vp.user_id = u.id
    WHERE 1=1
    '''
    params = []

    if category and category != "all":
        query += " AND vp.category = ?"
        params.append(category)

    if city and city != "All Cities":
        query += " AND vp.cities LIKE ?"
        params.append(f"%{city}%")

    if search:
        query += " AND (LOWER(vp.business_name) LIKE ? OR LOWER(vp.bio_en) LIKE ? OR LOWER(vp.category) LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if min_rating:
        query += " AND vp.rating_avg >= ?"
        params.append(min_rating)

    conn = get_db()
    vendors = conn.execute(query, params).fetchall()
    
    result = []
    for v in vendors:
        v_dict = dict(v)
        # Fetch base package price
        pkg = conn.execute('''
        SELECT base_price, pricing_model, unit, title 
        FROM packages 
        WHERE vendor_id = ? AND is_active = 1 
        ORDER BY base_price ASC LIMIT 1
        ''', (v_dict["id"],)).fetchone()
        
        if pkg:
            v_dict["starting_price"] = pkg["base_price"]
            v_dict["pricing_model"] = pkg["pricing_model"]
            v_dict["price_unit"] = pkg["unit"]
            v_dict["lead_package_title"] = pkg["title"]
        else:
            v_dict["starting_price"] = 0
            v_dict["pricing_model"] = "custom_quote"
            v_dict["price_unit"] = "event"

        result.append(v_dict)

    conn.close()
    return jsonify({"vendors": result, "count": len(result)})

@app.route("/api/vendors/<int:vendor_id>", methods=["GET"])
def get_vendor_details(vendor_id):
    conn = get_db()
    vp = conn.execute('''
    SELECT id, business_name, category, cities, service_radius_km, kyc_verified,
           rating_avg, review_count, bio_en, bio_te, bio_hi, image_url,
           portfolio_json, terms_and_conditions, response_time
    FROM vendor_profiles WHERE id = ?
    ''', (vendor_id,)).fetchone()

    if not vp:
        conn.close()
        return jsonify({"error": "Vendor not found"}), 404

    vendor = dict(vp)

    # Packages & Addons
    packages = conn.execute("SELECT * FROM packages WHERE vendor_id = ? AND is_active = 1", (vendor_id,)).fetchall()
    pkgs_list = []
    for p in packages:
        p_dict = dict(p)
        p_dict["inclusions"] = json.loads(p_dict["inclusions_json"]) if p_dict["inclusions_json"] else []
        p_dict["exclusions"] = json.loads(p_dict["exclusions_json"]) if p_dict["exclusions_json"] else []
        
        addons = conn.execute("SELECT * FROM package_addons WHERE package_id = ?", (p_dict["id"],)).fetchall()
        p_dict["addons"] = rows_to_list(addons)
        pkgs_list.append(p_dict)
    vendor["packages"] = pkgs_list

    # Rental Inventory
    inventory = conn.execute("SELECT * FROM inventory_items WHERE vendor_id = ?", (vendor_id,)).fetchall()
    vendor["inventory"] = rows_to_list(inventory)

    # Reviews
    reviews = conn.execute('''
    SELECT r.id, r.rating, r.review_text, r.verified_booking, r.created_at
    FROM reviews r
    WHERE r.vendor_id = ?
    ORDER BY r.created_at DESC
    ''', (vendor_id,)).fetchall()
    vendor["reviews"] = rows_to_list(reviews)

    conn.close()
    return jsonify({"vendor": vendor})

@app.route("/api/vendors/compare", methods=["POST"])
def compare_vendors():
    data = request.json or {}
    vendor_ids = data.get("vendor_ids", [])
    if not vendor_ids or len(vendor_ids) < 2:
        return jsonify({"error": "Select at least 2 providers to compare."}), 400

    conn = get_db()
    comparison = []
    for vid in vendor_ids[:4]: # compare up to 4
        vp = conn.execute('''
        SELECT id, business_name, category, cities, rating_avg, review_count, image_url,
               terms_and_conditions
        FROM vendor_profiles WHERE id = ?
        ''', (vid,)).fetchone()
        if not vp:
            continue
        v_dict = dict(vp)
        pkgs = conn.execute("SELECT title, base_price, unit, inclusions_json, exclusions_json FROM packages WHERE vendor_id = ? LIMIT 2", (vid,)).fetchall()
        v_dict["packages"] = []
        for p in pkgs:
            pd = dict(p)
            pd["inclusions"] = json.loads(pd["inclusions_json"]) if pd["inclusions_json"] else []
            pd["exclusions"] = json.loads(pd["exclusions_json"]) if pd["exclusions_json"] else []
            v_dict["packages"].append(pd)
        comparison.append(v_dict)

    conn.close()
    return jsonify({"comparison": comparison})

# -------------------------------------------------------------
# 3. AI EVENT ARCHITECT & SELLER ASSISTANT
# -------------------------------------------------------------
@app.route("/api/ai/plan", methods=["POST"])
def ai_event_planner():
    data = request.json or {}
    event_type = data.get("event_type", "wedding")
    guests = int(data.get("guests", 150))
    city = data.get("city", "Hyderabad")
    budget_tier = data.get("budget_tier", "premium")
    lang = data.get("language", "en")
    user_prompt = data.get("prompt", "").strip()

    # Calculate realistic South Asian event budget allocation
    if budget_tier == "budget":
        base_budget = guests * 1100
    elif budget_tier == "premium":
        base_budget = guests * 2400
    else: # luxury
        base_budget = guests * 4800

    catering = round(base_budget * 0.40)
    venue = round(base_budget * 0.25)
    decor = round(base_budget * 0.15)
    photography = round(base_budget * 0.12)
    dj_music = round(base_budget * 0.08)

    # Authentic themes
    themes = {
        "wedding": {
            "en": {"name": "Temple Jasmine & Royal Kanchipuram Gold", "colors": "Temple Gold, Marigold Yellow, Crimson Rose"},
            "te": {"name": "సాంప్రదాయ మల్లెల పరిమళం & కెంపు బంగారు థీమ్", "colors": "స్వర్ణ పసుపు, కెంపు ఎరుపు, మల్లె తెలుపు"},
            "hi": {"name": "पारंपरिक चमेली एवं स्वर्णिम कांचीपुरम वैभव", "colors": "स्वर्णिम पीला, गहरा लाल, दूधिया सफेद"}
        },
        "birthday": {
            "en": {"name": "Lavender Pastel Glow & Fairy Lights", "colors": "Soft Lavender, Warm Gold, Ivory"},
            "te": {"name": "లావెండర్ పాస్టెల్ వెలుగులు & ఫెయిరీ లైటింగ్", "colors": "లేత లావెండర్, మెరిసే బంగారం, ఐవరీ"},
            "hi": {"name": "लैवेंडर पेस्टल ग्लो एवं फेयरी लाइट सजावट", "colors": "सॉफ्ट लैवेंडर, सुनहरा, क्रीम"}
        },
        "cradle_ceremony": {
            "en": {"name": "Traditional Cradle Lotus & Gokulam", "colors": "Lotus Pink, Fresh Leaf Green, Pure White"},
            "te": {"name": "గోకులం ఉయ్యాల & కమలం సాంప్రదాయ థీమ్ (బారసాల)", "colors": "కమల గులాబీ, చిగురుటాకు పచ్చ, తెలుపు"},
            "hi": {"name": "पारंपरिक गोकुलम एवं कमल पुष्प झूला उत्सव", "colors": "गुलाबी, ताज़ा हरा, सफेद"}
        }
    }

    selected_theme = themes.get(event_type, themes["wedding"]).get(lang, themes.get(event_type, themes["wedding"])["en"])

    # Match real registered providers from SQLite
    conn = get_db()
    matched_vendors = []
    categories = ["catering", "venues", "decorations", "photography", "dj_music"]
    for cat in categories:
        v = conn.execute('''
        SELECT id, business_name, category, cities, rating_avg, review_count, image_url 
        FROM vendor_profiles 
        WHERE category = ? AND cities LIKE ? 
        LIMIT 1
        ''', (cat, f"%{city}%")).fetchone()
        if not v:
            v = conn.execute("SELECT id, business_name, category, cities, rating_avg, review_count, image_url FROM vendor_profiles WHERE category = ? LIMIT 1", (cat,)).fetchone()
        if v:
            matched_vendors.append(dict(v))
    conn.close()

    # Preparation checklist
    checklist = [
        {"timeline": "3 Months Prior", "task": "Book Auspicious Muhurtham Convention Hall & Caterer"},
        {"timeline": "6 Weeks Prior", "task": "Finalize Mandap Floral Decor theme & Candid Photographer"},
        {"timeline": "3 Weeks Prior", "task": "Send Digital WhatsApp Invites with RSVP QR Pass"},
        {"timeline": "1 Week Prior", "task": "Confirm final guest count & synchronize Event Master Run-Sheet"}
    ]

    return jsonify({
        "blueprint": {
            "event_type": event_type,
            "guests": guests,
            "city": city,
            "budget_tier": budget_tier,
            "total_estimated_budget": base_budget,
            "theme": selected_theme,
            "itemized_budget": {
                "catering": {"amount": catering, "percentage": 40, "note": f"~₹{round(catering/guests)}/plate"},
                "venue": {"amount": venue, "percentage": 25, "note": "AC Main Hall + Dining Suite"},
                "decorations": {"amount": decor, "percentage": 15, "note": "Mandap + Entrance Arch"},
                "photography": {"amount": photography, "percentage": 12, "note": "Candid + Drone + Album"},
                "dj_music": {"amount": dj_music, "percentage": 8, "note": "High-Output Sound & Emcee"}
            },
            "checklist": checklist,
            "recommended_vendors": matched_vendors,
            "voice_summary": {
                "te": f"{guests} మంది అతిథులకు {selected_theme['name']} తో ఈవెంట్ బ్లూప్రింట్ సిద్ధమైంది. అంచనా బడ్జెట్ ₹{base_budget:,.0f}.",
                "hi": f"{guests} मेहमानों के लिए {selected_theme['name']} की विस्तृत योजना तैयार है। अनुमानित बजट ₹{base_budget:,.0f} है।",
                "en": f"AI Blueprint generated for {guests} guests with '{selected_theme['name']}'. Total estimated budget is ₹{base_budget:,.0f}."
            }
        }
    })

@app.route("/api/ai/seller-assist", methods=["POST"])
@require_auth(required_role="vendor")
def ai_seller_assist(current_user):
    data = request.json or {}
    notes = data.get("bullet_points", "").strip()
    category = data.get("category", "photography")
    lang = data.get("target_language", "en")

    # Generate structured high-converting seller description
    descriptions = {
        "en": f"Professional {category} services tailored for unforgettable celebrations. We deliver punctual, premium-grade execution with transparent itemized pricing and zero hidden surcharges.",
        "te": f"మీ శుభకార్యాలకు అత్యద్భుతమైన {category} సేవలు. దాపరికాలు లేని పారదర్శక ధరలు మరియు నమ్మకమైన సమయపాలనతో మీ వేడుకలను చిరస్మరణీయం చేస్తాము.",
        "hi": f"आपके मांगलिक कार्यक्रमों के लिए विश्वसनीय और पेशेवर {category} सेवाएँ। पारदर्शी दरों और उच्च गुणवत्ता के साथ सर्वश्रेष्ठ अनुभव।"
    }

    return jsonify({
        "generated_description": descriptions.get(lang, descriptions["en"]),
        "suggested_inclusions": ["Professional setup crew included", "100% backup equipment on site", "Punctual arrival 2 hours before event"],
        "pricing_guidance": "Recommended deposit: 30% advance with 70% balance on milestone delivery."
    })

# -------------------------------------------------------------
# 4. CUSTOMER EVENTS & MULTI-PROVIDER WORKSPACE
# -------------------------------------------------------------
@app.route("/api/events", methods=["GET"])
@require_auth()
def list_user_events(current_user):
    conn = get_db()
    events = conn.execute('''
    SELECT * FROM events 
    WHERE customer_id = ? 
    ORDER BY event_date ASC
    ''', (current_user["id"],)).fetchall()
    
    events_list = []
    for ev in events:
        ed = dict(ev)
        # Count confirmed bookings
        b_count = conn.execute("SELECT COUNT(*) FROM bookings WHERE event_id = ?", (ed["id"],)).fetchone()[0]
        # Count guests
        g_count = conn.execute("SELECT COUNT(*) FROM guests WHERE event_id = ?", (ed["id"],)).fetchone()[0]
        ed["confirmed_bookings_count"] = b_count
        ed["guests_registered_count"] = g_count
        events_list.append(ed)

    conn.close()
    return jsonify({"events": events_list})

@app.route("/api/events", methods=["POST"])
@require_auth(required_role="customer")
def create_event(current_user):
    data = request.json or {}
    title = data.get("title", "My Celebration").strip()
    event_type = data.get("event_type", "wedding")
    event_date = data.get("event_date", str(datetime.date.today() + datetime.timedelta(days=45)))
    city = data.get("city", "Hyderabad")
    venue = data.get("venue", "To be selected")
    guests = int(data.get("guest_count", 150))
    budget = float(data.get("total_budget", 300000))
    theme = data.get("theme_name", "Traditional Festive")
    notes = data.get("special_notes", "")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO events (customer_id, title, event_type, event_date, city, venue, guest_count, total_budget, theme_name, special_notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (current_user["id"], title, event_type, event_date, city, venue, guests, budget, theme, notes))
    event_id = cursor.lastrowid

    # Initialize standard budget allocation
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount) VALUES (?, 'catering', ?)", (event_id, budget * 0.40))
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount) VALUES (?, 'venues', ?)", (event_id, budget * 0.25))
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount) VALUES (?, 'decorations', ?)", (event_id, budget * 0.15))
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount) VALUES (?, 'photography', ?)", (event_id, budget * 0.12))
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount) VALUES (?, 'dj_music', ?)", (event_id, budget * 0.08))

    # Add initial run-sheet items
    cursor.execute("INSERT INTO event_runsheet (event_id, time_slot, activity) VALUES (?, '08:00 AM', 'Venue Open & Decor Setup')", (event_id,))
    cursor.execute("INSERT INTO event_runsheet (event_id, time_slot, activity) VALUES (?, '11:00 AM', 'Main Ceremony & Photography')", (event_id,))
    cursor.execute("INSERT INTO event_runsheet (event_id, time_slot, activity) VALUES (?, '01:00 PM', 'Royal Banquet Feast')", (event_id,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Event created successfully!", "event_id": event_id}), 201

@app.route("/api/events/<int:event_id>", methods=["GET"])
@require_auth()
def get_event_details(current_user, event_id):
    conn = get_db()
    ev = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not ev:
        conn.close()
        return jsonify({"error": "Event not found"}), 404

    _, access_error = _event_access(conn, current_user, event_id, allow_vendor=True)
    if access_error:
        conn.close()
        return access_error

    event = dict(ev)
    vendor_view = current_user["role"] == "vendor" and ev["customer_id"] != current_user["id"]
    if vendor_view:
        for field in ("customer_id", "total_budget", "special_notes", "color_palette", "dietary_preference"):
            event.pop(field, None)

    # Budget
    budget_items = [] if vendor_view else conn.execute(
        "SELECT * FROM budget_items WHERE event_id = ?", (event_id,)
    ).fetchall()
    event["budget_breakdown"] = rows_to_list(budget_items)

    # Bookings
    booking_query = '''
    SELECT b.*, vp.business_name, vp.category, vp.image_url 
    FROM bookings b
    JOIN vendor_profiles vp ON b.vendor_id = vp.id
    WHERE b.event_id = ?
    '''
    booking_params = [event_id]
    if vendor_view:
        booking_query += " AND b.vendor_id IN (SELECT id FROM vendor_profiles WHERE user_id = ?)"
        booking_params.append(current_user["id"])
    bookings = conn.execute(booking_query, booking_params).fetchall()
    event["bookings"] = rows_to_list(bookings)
    if vendor_view:
        for booking in event["bookings"]:
            booking.pop("customer_id", None)

    # Quotations
    quote_query = '''
    SELECT q.*, vp.business_name, vp.category, vp.image_url 
    FROM quotations q
    JOIN vendor_profiles vp ON q.vendor_id = vp.id
    WHERE q.event_id = ?
    ORDER BY q.created_at DESC
    '''
    quote_params = [event_id]
    if vendor_view:
        quote_query = quote_query.replace(
            "ORDER BY q.created_at DESC",
            "AND q.vendor_id IN (SELECT id FROM vendor_profiles WHERE user_id = ?) ORDER BY q.created_at DESC",
        )
        quote_params.append(current_user["id"])
    quotes = conn.execute(quote_query, quote_params).fetchall()
    event["quotations"] = rows_to_list(quotes)
    if vendor_view:
        for quote in event["quotations"]:
            quote.pop("customer_id", None)

    # Run-sheet
    runsheet = conn.execute("SELECT * FROM event_runsheet WHERE event_id = ? ORDER BY time_slot ASC", (event_id,)).fetchall()
    event["runsheet"] = rows_to_list(runsheet)
    if vendor_view:
        for item in event["runsheet"]:
            item.pop("contact_name", None)
            item.pop("contact_phone", None)

    # Guests
    guests = [] if vendor_view else conn.execute(
        "SELECT * FROM guests WHERE event_id = ? ORDER BY id ASC", (event_id,)
    ).fetchall()
    event["guests"] = rows_to_list(guests)

    # Collaborators
    collabs = [] if vendor_view else conn.execute(
        "SELECT * FROM event_collaborators WHERE event_id = ?", (event_id,)
    ).fetchall()
    event["collaborators"] = rows_to_list(collabs)

    conn.close()
    return jsonify({"event": event})

# -------------------------------------------------------------
# 5. QUOTATIONS & NEGOTIATION HUB
# -------------------------------------------------------------
@app.route("/api/quotations/request", methods=["POST"])
@require_auth(required_role="customer")
def request_quotation(current_user):
    data = request.json or {}
    event_id = data.get("event_id")
    vendor_id = data.get("vendor_id")
    category = data.get("category", "photography")
    event_date = data.get("event_date", str(datetime.date.today()))
    guest_count = int(data.get("guest_count", 150))
    requirements = data.get("requirements", "").strip()

    if not event_id or not vendor_id:
        return jsonify({"error": "Event ID and Vendor ID are required."}), 400

    conn = get_db()
    event = conn.execute("SELECT customer_id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({"error": "Event not found"}), 404
    if event["customer_id"] != current_user["id"]:
        conn.close()
        return jsonify({"error": "You can only request quotations for your own events."}), 403
    vendor = conn.execute("SELECT user_id, business_name FROM vendor_profiles WHERE id = ?", (vendor_id,)).fetchone()
    if not vendor:
        conn.close()
        return jsonify({"error": "Vendor not found"}), 404

    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO quotation_requests (event_id, customer_id, vendor_id, category, event_date, guest_count, requirements)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (event_id, current_user["id"], vendor_id, category, event_date, guest_count, requirements))
    req_id = cursor.lastrowid

    # Notify vendor
    cursor.execute('''
    INSERT INTO notifications (user_id, title, message, category)
    VALUES (?, 'New Quotation Request!', ?, 'quotation')
    ''', (vendor["user_id"], f"Customer {current_user['full_name']} requested a custom quote for {category}."))

    conn.commit()
    conn.close()

    return jsonify({"message": "Quotation request submitted to vendor!", "request_id": req_id}), 201

@app.route("/api/quotations/<int:quote_id>/respond", methods=["POST"])
@require_auth(required_role="vendor")
def respond_quotation(current_user, quote_id):
    data = request.json or {}
    subtotal = float(data.get("subtotal", 0))
    discount = float(data.get("discount", 0))
    tax = float(data.get("tax", 0))
    advance = float(data.get("advance_required", subtotal * 0.30))
    notes = data.get("terms_and_notes", "").strip()
    items = data.get("items", [])

    total = subtotal - discount + tax
    platform_fee = round(total * 0.02, 2) # transparent 2% platform fee

    conn = get_db()
    cursor = conn.cursor()

    # Get quote
    q = cursor.execute("SELECT * FROM quotations WHERE id = ?", (quote_id,)).fetchone()
    if not q:
        conn.close()
        return jsonify({"error": "Quotation record not found"}), 404

    # Authorization: Ensure vendor owns this quote
    vp = cursor.execute("SELECT id FROM vendor_profiles WHERE user_id = ?", (current_user["id"],)).fetchone()
    if not vp or q["vendor_id"] != vp["id"]:
        conn.close()
        return jsonify({"error": "Unauthorized: You can only respond to quotations sent to your business."}), 403

    # Update or create revised version
    new_version = q["version"] + 1
    cursor.execute('''
    UPDATE quotations 
    SET subtotal = ?, discount_amount = ?, tax_amount = ?, platform_fee = ?, total_amount = ?, advance_required = ?, terms_and_notes = ?, version = ?, status = 'sent'
    WHERE id = ?
    ''', (subtotal, discount, tax, platform_fee, total, advance, notes, new_version, quote_id))

    # Add line items
    cursor.execute("DELETE FROM quotation_items WHERE quotation_id = ?", (quote_id,))
    for item in items:
        cursor.execute('''
        INSERT INTO quotation_items (quotation_id, item_name, quantity, unit_price, total_price)
        VALUES (?, ?, ?, ?, ?)
        ''', (quote_id, item.get("name", "Service Item"), item.get("qty", 1), item.get("price", 0), item.get("qty", 1) * item.get("price", 0)))

    # Notify customer
    cursor.execute('''
    INSERT INTO notifications (user_id, title, message, category)
    VALUES (?, 'Quotation Ready for Review!', ?, 'quotation')
    ''', (q["customer_id"], f"Vendor sent an itemized quotation of ₹{total:,.0f} (v{new_version})."))

    conn.commit()
    conn.close()

    return jsonify({"message": "Quotation submitted successfully!", "total_amount": total, "version": new_version})

@app.route("/api/quotations/<int:quote_id>/accept", methods=["POST"])
@require_auth(required_role="customer")
def accept_quotation(current_user, quote_id):
    conn = get_db()
    cursor = conn.cursor()

    q = cursor.execute("SELECT * FROM quotations WHERE id = ?", (quote_id,)).fetchone()
    if not q:
        conn.close()
        return jsonify({"error": "Quotation not found"}), 404

    if q["customer_id"] != current_user["id"] and current_user["role"] != "admin":
        conn.close()
        return jsonify({"error": "Unauthorized: You can only accept quotations for your own events."}), 403

    # Update quote status
    cursor.execute("UPDATE quotations SET status = 'accepted' WHERE id = ?", (quote_id,))

    # Create confirmed booking automatically
    vp = cursor.execute("SELECT category FROM vendor_profiles WHERE id = ?", (q["vendor_id"],)).fetchone()
    cat = vp["category"] if vp else "general"

    cursor.execute('''
    INSERT INTO bookings (event_id, quotation_id, customer_id, vendor_id, service_category, total_amount, advance_paid, balance_amount, payment_status, booking_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'advance_paid', 'confirmed')
    ''', (q["event_id"], quote_id, current_user["id"], q["vendor_id"], cat, q["total_amount"], q["advance_required"], q["total_amount"] - q["advance_required"]))
    booking_id = cursor.lastrowid

    # Create visual tracking milestones
    milestones = [
        (1, "Booking & Advance Secured", f"₹{q['advance_required']:,.0f} advance secured in escrow. Date confirmed in vendor calendar.", "completed"),
        (2, "Pre-Event Planning & Consultation", "Moodboard and shot-list reviewed and approved.", "in_progress"),
        (3, "Event Day Execution", "Vendor check-in at venue and live service delivery.", "pending"),
        (4, "Deliverables & Inspection", "Photos/video preview or setup teardown inspection.", "pending"),
        (5, "Completion & Settlement", "Final balance release and review submission.", "pending")
    ]
    for stage, title, desc, st in milestones:
        cursor.execute('''
        INSERT INTO booking_milestones (booking_id, stage_number, title, description, status)
        VALUES (?, ?, ?, ?, ?)
        ''', (booking_id, stage, title, desc, st))

    # Update budget items spent amount
    cursor.execute('''
    UPDATE budget_items 
    SET spent_amount = spent_amount + ? 
    WHERE event_id = ? AND category = ?
    ''', (q["total_amount"], q["event_id"], cat))

    # Notify vendor
    v_user = cursor.execute("SELECT user_id FROM vendor_profiles WHERE id = ?", (q["vendor_id"],)).fetchone()
    if v_user:
        cursor.execute('''
        INSERT INTO notifications (user_id, title, message, category)
        VALUES (?, 'Booking Confirmed!', ?, 'booking')
        ''', (v_user["user_id"], f"Customer accepted quotation #{quote_id}. Advance deposit secured."))

    conn.commit()
    conn.close()

    return jsonify({"message": "Quotation accepted! Booking confirmed and milestone tracker initialized.", "booking_id": booking_id})

# -------------------------------------------------------------
# 6. BOOKINGS, MILESTONES & PAYMENTS
# -------------------------------------------------------------
@app.route("/api/bookings", methods=["GET"])
@require_auth()
def list_bookings(current_user):
    conn = get_db()
    if current_user["role"] == "vendor":
        vp = conn.execute("SELECT id FROM vendor_profiles WHERE user_id = ?", (current_user["id"],)).fetchone()
        if not vp:
            conn.close()
            return jsonify({"bookings": []})
        bookings = conn.execute('''
        SELECT b.*, e.title as event_title, e.event_date, e.city, u.full_name as customer_name, u.phone as customer_phone
        FROM bookings b
        JOIN events e ON b.event_id = e.id
        JOIN users u ON b.customer_id = u.id
        WHERE b.vendor_id = ?
        ORDER BY b.created_at DESC
        ''', (vp["id"],)).fetchall()
    else:
        bookings = conn.execute('''
        SELECT b.*, e.title as event_title, e.event_date, e.city, vp.business_name, vp.category, vp.image_url
        FROM bookings b
        JOIN events e ON b.event_id = e.id
        JOIN vendor_profiles vp ON b.vendor_id = vp.id
        WHERE b.customer_id = ?
        ORDER BY b.created_at DESC
        ''', (current_user["id"],)).fetchall()

    b_list = []
    for b in bookings:
        bd = dict(b)
        # Fetch current milestone
        m = conn.execute("SELECT title, status FROM booking_milestones WHERE booking_id = ? AND status = 'in_progress' LIMIT 1", (bd["id"],)).fetchone()
        bd["current_milestone"] = dict(m) if m else {"title": "Confirmed", "status": "completed"}
        b_list.append(bd)

    conn.close()
    return jsonify({"bookings": b_list})

@app.route("/api/bookings/<int:booking_id>", methods=["GET"])
@require_auth()
def get_booking_details(current_user, booking_id):
    conn = get_db()
    b = conn.execute('''
    SELECT b.*, e.title as event_title, e.event_date, e.city, e.venue, vp.business_name, vp.category, vp.image_url, vp.terms_and_conditions
    FROM bookings b
    JOIN events e ON b.event_id = e.id
    JOIN vendor_profiles vp ON b.vendor_id = vp.id
    WHERE b.id = ?
    ''', (booking_id,)).fetchone()

    if not b:
        conn.close()
        return jsonify({"error": "Booking not found"}), 404

    vendor = conn.execute(
        "SELECT id FROM vendor_profiles WHERE user_id = ?",
        (current_user["id"],),
    ).fetchone() if current_user["role"] == "vendor" else None
    if (
        current_user["role"] != "admin"
        and current_user["id"] != b["customer_id"]
        and (not vendor or vendor["id"] != b["vendor_id"])
    ):
        conn.close()
        return jsonify({"error": "You do not have permission to access this booking."}), 403

    booking = dict(b)
    if current_user["role"] == "vendor":
        booking.pop("customer_id", None)
    milestones = conn.execute("SELECT * FROM booking_milestones WHERE booking_id = ? ORDER BY stage_number ASC", (booking_id,)).fetchall()
    booking["milestones"] = rows_to_list(milestones)

    conn.close()
    return jsonify({"booking": booking})

@app.route("/api/bookings/<int:booking_id>/milestones/<int:stage>/update", methods=["POST"])
@require_auth()
def update_milestone_status(current_user, booking_id, stage):
    data = request.json or {}
    status = data.get("status", "completed") # in_progress, completed, verified
    proof_url = data.get("proof_url", "")

    conn = get_db()
    cursor = conn.cursor()

    b = cursor.execute("SELECT customer_id, vendor_id FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not b:
        conn.close()
        return jsonify({"error": "Booking not found"}), 404

    vp = cursor.execute(
        "SELECT id FROM vendor_profiles WHERE user_id = ?",
        (current_user["id"],),
    ).fetchone() if current_user["role"] == "vendor" else None
    v_id = vp["id"] if vp else None
    if current_user["role"] != "admin" and current_user["id"] != b["customer_id"] and v_id != b["vendor_id"]:
        conn.close()
        return jsonify({"error": "Unauthorized: You can only update milestones for your own bookings."}), 403

    cursor.execute('''
    UPDATE booking_milestones 
    SET status = ?, proof_url = ?, completed_at = CURRENT_TIMESTAMP
    WHERE booking_id = ? AND stage_number = ?
    ''', (status, proof_url, booking_id, stage))

    # Advance next stage if completed
    if status == "completed":
        cursor.execute('''
        UPDATE booking_milestones 
        SET status = 'in_progress' 
        WHERE booking_id = ? AND stage_number = ? AND status = 'pending'
        ''', (booking_id, stage + 1))

    conn.commit()
    conn.close()

    return jsonify({"message": f"Milestone stage {stage} updated to {status}."})

@app.route("/api/bookings/<int:booking_id>/cancel", methods=["POST"])
@require_auth()
def cancel_booking(current_user, booking_id):
    conn = get_db()
    cursor = conn.cursor()
    b = cursor.execute('''
    SELECT b.*, e.event_date, vp.user_id as vendor_user_id
    FROM bookings b
    JOIN events e ON b.event_id = e.id
    JOIN vendor_profiles vp ON b.vendor_id = vp.id
    WHERE b.id = ?
    ''', (booking_id,)).fetchone()

    if not b:
        conn.close()
        return jsonify({"error": "Booking not found"}), 404

    if (
        current_user["role"] != "admin"
        and current_user["id"] != b["customer_id"]
        and (current_user["role"] != "vendor" or current_user["id"] != b["vendor_user_id"])
    ):
        conn.close()
        return jsonify({"error": "Unauthorized: You can only cancel your own bookings."}), 403

    if b["booking_status"] == "cancelled":
        conn.close()
        return jsonify({"error": "Booking is already cancelled."}), 400

    # Calculate transparent cancellation refund
    today = datetime.date.today()
    try:
        ev_date = datetime.date.fromisoformat(b["event_date"])
        days_until_event = (ev_date - today).days
    except Exception:
        days_until_event = 30

    advance_paid = float(b["advance_paid"])
    if days_until_event >= 14:
        refund_percent = 100
        refund_amount = advance_paid
        policy_note = "Full 100% advance refund (Cancelled >14 days before event)."
    elif days_until_event >= 7:
        refund_percent = 50
        refund_amount = advance_paid * 0.50
        policy_note = "Partial 50% advance refund (Cancelled 7-14 days before event)."
    else:
        refund_percent = 0
        refund_amount = 0.0
        policy_note = "Non-refundable advance (Cancelled <7 days before event)."

    cursor.execute('''
    UPDATE bookings 
    SET booking_status = 'cancelled', payment_status = 'refunded'
    WHERE id = ?
    ''', (booking_id,))

    cursor.execute('''
    INSERT INTO notifications (user_id, title, message, category)
    VALUES (?, 'Booking Cancelled', ?, 'booking')
    ''', (b["customer_id"], f"Booking #{booking_id} cancelled. Refund of ₹{refund_amount:,.0f} ({refund_percent}%) approved. {policy_note}"))

    conn.commit()
    conn.close()

    return jsonify({
        "message": f"Booking cancelled. {policy_note}",
        "refund_percent": refund_percent,
        "refund_amount": refund_amount,
        "policy_note": policy_note
    })

# -------------------------------------------------------------
# 7. GUEST LISTS, RSVPs & QR CODE CHECK-IN
# -------------------------------------------------------------
@app.route("/api/events/<int:event_id>/guests", methods=["GET"])
@require_auth()
def list_guests(current_user, event_id):
    conn = get_db()
    _, access_error = _event_access(conn, current_user, event_id)
    if access_error:
        conn.close()
        return access_error
    guests = conn.execute("SELECT * FROM guests WHERE event_id = ? ORDER BY id ASC", (event_id,)).fetchall()
    conn.close()
    return jsonify({"guests": rows_to_list(guests)})

@app.route("/api/events/<int:event_id>/guests", methods=["POST"])
@require_auth(required_role="customer")
def add_guest(current_user, event_id):
    data = _request_data()
    name = data.get("full_name", "").strip()
    phone = data.get("phone", "").strip()
    side = data.get("side", "common")
    dietary = data.get("dietary", "veg")
    guest_count = int(data.get("guest_count", 1))
    table = data.get("table_number", "Unassigned")

    if not name:
        return jsonify({"error": "Guest name is required"}), 400

    token = f"VEDUKA-{uuid.uuid4().hex[:8].upper()}"

    conn = get_db()
    _, access_error = _event_access(conn, current_user, event_id, edit=True)
    if access_error:
        conn.close()
        return access_error
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO guests (event_id, full_name, phone, side, dietary, guest_count, table_number, qr_code_token)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (event_id, name, phone, side, dietary, guest_count, table, token))
    guest_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Guest added to invitation registry!",
        "guest_id": guest_id,
        "qr_code_token": token,
        "invite_link": f"/rsvp/{token}"
    }), 201

@app.route("/api/guests/check-in", methods=["POST"])
@require_auth()
def check_in_guest(current_user):
    data = _request_data()
    token = data.get("qr_code_token", "")
    if not isinstance(token, str):
        return jsonify({"error": "QR token is required."}), 400
    token = token.strip().upper()

    if not token:
        return jsonify({"error": "QR token is required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    guest = cursor.execute("SELECT * FROM guests WHERE qr_code_token = ?", (token,)).fetchone()

    if not guest:
        conn.close()
        return jsonify({"valid": False, "message": "Invalid QR code token. Guest not found on event guest list."}), 404

    _, access_error = _event_access(
        conn, current_user, guest["event_id"], allow_vendor=True, edit=True
    )
    if access_error:
        conn.close()
        return access_error

    g = dict(guest)
    check_in_guest = {
        key: g[key]
        for key in ("id", "full_name", "guest_count", "side", "table_number", "checked_in", "checked_in_at")
    }
    if g["checked_in"] == 1:
        conn.close()
        return jsonify({
            "valid": True,
            "already_checked_in": True,
            "guest": check_in_guest,
            "message": f"Already checked in at {g['checked_in_at']}."
        })

    cursor.execute(
        "UPDATE guests SET checked_in = 1, checked_in_at = CURRENT_TIMESTAMP WHERE id = ? AND checked_in = 0",
        (g["id"],),
    )
    already_checked_in = cursor.rowcount == 0
    conn.commit()

    updated = cursor.execute("SELECT * FROM guests WHERE id = ?", (g["id"],)).fetchone()
    conn.close()
    updated_guest = dict(updated)
    check_in_guest.update({
        "checked_in": updated_guest["checked_in"],
        "checked_in_at": updated_guest["checked_in_at"],
    })

    return jsonify({
        "valid": True,
        "already_checked_in": already_checked_in,
        "guest": check_in_guest,
        "message": f"Check-in verified! Welcome {g['full_name']} ({g['guest_count']} guests, {g['side']} side, {g['table_number']})."
    })

# -------------------------------------------------------------
# 8. SELLER DASHBOARD, INVENTORY & ANALYTICS
# -------------------------------------------------------------
@app.route("/api/seller/dashboard", methods=["GET"])
@require_auth(required_role="vendor")
def seller_dashboard(current_user):
    conn = get_db()
    vp = conn.execute("SELECT * FROM vendor_profiles WHERE user_id = ?", (current_user["id"],)).fetchone()
    if not vp:
        conn.close()
        return jsonify({"error": "Vendor profile not found"}), 404

    vid = vp["id"]

    # Metrics
    inquiries_count = conn.execute("SELECT COUNT(*) FROM quotation_requests WHERE vendor_id = ?", (vid,)).fetchone()[0]
    active_bookings = conn.execute("SELECT COUNT(*) FROM bookings WHERE vendor_id = ? AND booking_status = 'confirmed'", (vid,)).fetchone()[0]
    total_revenue = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM bookings WHERE vendor_id = ?", (vid,)).fetchone()[0]
    pending_payout = conn.execute("SELECT COALESCE(SUM(balance_amount), 0) FROM bookings WHERE vendor_id = ? AND booking_status = 'confirmed'", (vid,)).fetchone()[0]

    # Recent inquiries
    recent_inquiries = conn.execute('''
    SELECT qr.*, e.title as event_title, u.full_name as customer_name, u.phone as customer_phone
    FROM quotation_requests qr
    JOIN events e ON qr.event_id = e.id
    JOIN users u ON qr.customer_id = u.id
    WHERE qr.vendor_id = ?
    ORDER BY qr.created_at DESC LIMIT 5
    ''', (vid,)).fetchall()

    # Inventory
    inventory = conn.execute("SELECT * FROM inventory_items WHERE vendor_id = ?", (vid,)).fetchall()

    conn.close()
    return jsonify({
        "metrics": {
            "inquiries": inquiries_count,
            "active_bookings": active_bookings,
            "total_revenue": total_revenue,
            "pending_escrow_payout": pending_payout,
            "conversion_rate": "68%",
            "rating": vp["rating_avg"],
            "review_count": vp["review_count"]
        },
        "recent_inquiries": rows_to_list(recent_inquiries),
        "inventory": rows_to_list(inventory)
    })

# -------------------------------------------------------------
# 9. NOTIFICATIONS, MESSAGES & SUPPORT
# -------------------------------------------------------------
@app.route("/api/notifications", methods=["GET"])
@require_auth()
def get_notifications(current_user):
    conn = get_db()
    notifs = conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", (current_user["id"],)).fetchall()
    conn.close()
    return jsonify({"notifications": rows_to_list(notifs)})

@app.route("/api/notifications/<int:nid>/read", methods=["POST"])
@require_auth()
def mark_notification_read(current_user, nid):
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (nid, current_user["id"]))
    conn.commit()
    conn.close()
    return jsonify({"message": "Marked as read"})

@app.route("/api/support", methods=["GET", "POST"])
@require_auth()
def support_tickets(current_user):
    conn = get_db()
    if request.method == "POST":
        data = request.json or {}
        subject = data.get("subject", "").strip()
        desc = data.get("description", "").strip()
        priority = data.get("priority", "medium")

        if not subject or not desc:
            conn.close()
            return jsonify({"error": "Subject and description are required"}), 400

        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO support_tickets (user_id, subject, description, priority)
        VALUES (?, ?, ?, ?)
        ''', (current_user["id"], subject, desc, priority))
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"message": "Support ticket created. Our resolution team will review within 2 hours.", "ticket_id": ticket_id}), 201

    tickets = conn.execute("SELECT * FROM support_tickets WHERE user_id = ? ORDER BY created_at DESC", (current_user["id"],)).fetchall()
    conn.close()
    return jsonify({"tickets": rows_to_list(tickets)})

# -------------------------------------------------------------
# 10. ADMINISTRATOR OVERVIEW & MODERATION
# -------------------------------------------------------------
@app.route("/api/admin/overview", methods=["GET"])
@require_auth(required_role="admin")
def admin_overview(current_user):
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_vendors = conn.execute("SELECT COUNT(*) FROM vendor_profiles").fetchone()[0]
    total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    total_bookings = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    gmv = conn.execute("SELECT COALESCE(SUM(total_amount), 0) FROM bookings").fetchone()[0]
    pending_tickets = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE status = 'open'").fetchone()[0]

    vendors = conn.execute("SELECT vp.*, u.email, u.phone FROM vendor_profiles vp JOIN users u ON vp.user_id = u.id").fetchall()
    tickets = conn.execute("SELECT * FROM support_tickets ORDER BY created_at DESC").fetchall()

    conn.close()
    return jsonify({
        "metrics": {
            "total_users": total_users,
            "total_vendors": total_vendors,
            "total_events": total_events,
            "total_bookings": total_bookings,
            "gross_marketplace_volume": gmv,
            "pending_disputes": pending_tickets
        },
        "vendors": rows_to_list(vendors),
        "tickets": rows_to_list(tickets)
    })

@app.route("/api/admin/verify-vendor/<int:vendor_id>", methods=["POST"])
@require_auth(required_role="admin")
def verify_vendor(current_user, vendor_id):
    conn = get_db()
    cursor = conn.cursor()
    vp = cursor.execute("SELECT kyc_verified FROM vendor_profiles WHERE id = ?", (vendor_id,)).fetchone()
    if not vp:
        conn.close()
        return jsonify({"error": "Vendor not found"}), 404

    new_status = 0 if vp["kyc_verified"] == 1 else 1
    cursor.execute("UPDATE vendor_profiles SET kyc_verified = ? WHERE id = ?", (new_status, vendor_id))

    cursor.execute('''
    INSERT INTO admin_audit_logs (admin_id, action, target_type, target_id, details)
    VALUES (?, 'TOGGLE_VENDOR_VERIFICATION', 'vendor_profiles', ?, ?)
    ''', (current_user["id"], vendor_id, f"KYC status changed to {new_status}"))

    conn.commit()
    conn.close()
    return jsonify({"message": f"Vendor verification updated to {new_status}", "kyc_verified": new_status})

# -------------------------------------------------------------
# 11. STATIC FILES & CLIENT SERVING
# -------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory("../frontend", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"Starting Veduka AI Fullstack Application on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
