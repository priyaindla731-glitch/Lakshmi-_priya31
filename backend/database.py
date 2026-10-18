import sqlite3
import os
import json
import hashlib
import hmac
import re
from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.environ.get("DATABASE_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'veduka.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_password(password: str) -> str:
    return generate_password_hash(password)

def verify_password(stored_hash: str, password: str) -> bool:
    if re.fullmatch(r"[0-9a-fA-F]{64}", stored_hash or ""):
        legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(stored_hash.lower(), legacy_hash)
    try:
        return check_password_hash(stored_hash, password)
    except (TypeError, ValueError):
        return False

def is_legacy_password_hash(stored_hash: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", stored_hash or ""))

def demo_data_enabled() -> bool:
    requested = os.environ.get("ENABLE_DEMO_DATA", "false").lower() in ("1", "true", "yes")
    production = (
        os.environ.get("ENVIRONMENT", "").lower() == "production"
        or os.environ.get("FLASK_ENV", "").lower() == "production"
        or bool(os.environ.get("RENDER_SERVICE_ID"))
    )
    return requested and not production

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        phone TEXT UNIQUE,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('customer', 'vendor', 'admin')),
        preferred_language TEXT DEFAULT 'en' CHECK(preferred_language IN ('en', 'te', 'hi')),
        high_contrast INTEGER DEFAULT 0,
        speech_speed REAL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Vendor Profiles
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vendor_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        business_name TEXT NOT NULL,
        category TEXT NOT NULL,
        cities TEXT NOT NULL, -- comma separated
        service_radius_km INTEGER DEFAULT 50,
        kyc_verified INTEGER DEFAULT 0,
        rating_avg REAL DEFAULT 4.9,
        review_count INTEGER DEFAULT 0,
        bio_en TEXT,
        bio_te TEXT,
        bio_hi TEXT,
        image_url TEXT,
        portfolio_json TEXT, -- JSON array of image/video URLs
        terms_and_conditions TEXT,
        response_time TEXT DEFAULT '< 15 mins',
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 3. Packages & Itemized Rate Cards
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        pricing_model TEXT NOT NULL, -- 'per_day', 'per_plate', 'per_hour', 'per_event', 'fixed'
        base_price REAL NOT NULL,
        unit TEXT NOT NULL,
        inclusions_json TEXT, -- JSON array of strings
        exclusions_json TEXT, -- JSON array of strings
        specifications_json TEXT, -- JSON object
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY(vendor_id) REFERENCES vendor_profiles(id) ON DELETE CASCADE
    )
    ''')

    # 4. Package Add-ons
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS package_addons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY(package_id) REFERENCES packages(id) ON DELETE CASCADE
    )
    ''')

    # 5. Inventory & Rentals
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        total_stock INTEGER NOT NULL,
        available_stock INTEGER NOT NULL,
        rental_price_per_day REAL NOT NULL,
        security_deposit REAL DEFAULT 0,
        item_condition TEXT DEFAULT 'Excellent',
        damage_policy TEXT,
        FOREIGN KEY(vendor_id) REFERENCES vendor_profiles(id) ON DELETE CASCADE
    )
    ''')

    # 6. Customer Events
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_date TEXT NOT NULL,
        city TEXT NOT NULL,
        venue TEXT,
        guest_count INTEGER DEFAULT 150,
        total_budget REAL DEFAULT 250000,
        theme_name TEXT,
        color_palette TEXT,
        dietary_preference TEXT DEFAULT 'mixed',
        special_notes TEXT,
        status TEXT DEFAULT 'planning' CHECK(status IN ('planning', 'in_progress', 'completed', 'cancelled')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 7. Event Collaborators
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS event_collaborators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        collaborator_email TEXT NOT NULL,
        collaborator_name TEXT,
        permission TEXT DEFAULT 'view_and_vote' CHECK(permission IN ('view_only', 'view_and_vote', 'co_planner_edit')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
    )
    ''')

    # 8. Event Budget Breakdown
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS budget_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        allocated_amount REAL NOT NULL,
        spent_amount REAL DEFAULT 0,
        FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
    )
    ''')

    # 9. Quotation Requests (RFQs)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quotation_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        vendor_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        event_date TEXT NOT NULL,
        guest_count INTEGER,
        requirements TEXT,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'quoted', 'declined', 'expired')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
        FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(vendor_id) REFERENCES vendor_profiles(id) ON DELETE CASCADE
    )
    ''')

    # 10. Quotations & Revisions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        event_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        vendor_id INTEGER NOT NULL,
        version INTEGER DEFAULT 1,
        subtotal REAL NOT NULL,
        discount_amount REAL DEFAULT 0,
        tax_amount REAL DEFAULT 0,
        platform_fee REAL DEFAULT 0,
        total_amount REAL NOT NULL,
        advance_required REAL NOT NULL,
        terms_and_notes TEXT,
        validity_date TEXT,
        status TEXT DEFAULT 'sent' CHECK(status IN ('sent', 'revision_requested', 'accepted', 'rejected', 'expired')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
        FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(vendor_id) REFERENCES vendor_profiles(id) ON DELETE CASCADE
    )
    ''')

    # 11. Quotation Line Items
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quotation_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quotation_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        is_optional INTEGER DEFAULT 0,
        FOREIGN KEY(quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
    )
    ''')

    # 12. Bookings (Orders)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        quotation_id INTEGER,
        customer_id INTEGER NOT NULL,
        vendor_id INTEGER NOT NULL,
        service_category TEXT NOT NULL,
        total_amount REAL NOT NULL,
        advance_paid REAL DEFAULT 0,
        balance_amount REAL NOT NULL,
        payment_status TEXT DEFAULT 'advance_paid' CHECK(payment_status IN ('pending', 'advance_paid', 'fully_paid', 'refunded')),
        booking_status TEXT DEFAULT 'confirmed' CHECK(booking_status IN ('confirmed', 'in_progress', 'completed', 'cancelled')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
        FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(vendor_id) REFERENCES vendor_profiles(id) ON DELETE CASCADE
    )
    ''')

    # 13. Booking Milestones (Tracking)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS booking_milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        stage_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'completed', 'verified')),
        completed_at TIMESTAMP,
        proof_url TEXT,
        FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
    )
    ''')

    # 14. Event Day Master Run-Sheet (Coordination)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS event_runsheet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        vendor_id INTEGER,
        time_slot TEXT NOT NULL,
        activity TEXT NOT NULL,
        contact_name TEXT,
        contact_phone TEXT,
        is_completed INTEGER DEFAULT 0,
        FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
    )
    ''')

    # 15. Guest List, RSVPs & QR Check-in
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS guests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        side TEXT DEFAULT 'common' CHECK(side IN ('bride', 'groom', 'common', 'vip')),
        dietary TEXT DEFAULT 'veg' CHECK(dietary IN ('veg', 'non_veg', 'jain')),
        rsvp_status TEXT DEFAULT 'pending' CHECK(rsvp_status IN ('pending', 'attending', 'declined')),
        guest_count INTEGER DEFAULT 1,
        table_number TEXT,
        qr_code_token TEXT UNIQUE NOT NULL,
        checked_in INTEGER DEFAULT 0,
        checked_in_at TIMESTAMP,
        FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
    )
    ''')

    # 16. Chat Messages
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        event_id INTEGER,
        booking_id INTEGER,
        message_text TEXT NOT NULL,
        attachment_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(sender_id) REFERENCES users(id),
        FOREIGN KEY(receiver_id) REFERENCES users(id)
    )
    ''')

    # 17. Verified Reviews
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER UNIQUE,
        vendor_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        review_text TEXT,
        verified_booking INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(vendor_id) REFERENCES vendor_profiles(id) ON DELETE CASCADE,
        FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 18. Support & Dispute Tickets
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        booking_id INTEGER,
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'urgent')),
        status TEXT DEFAULT 'open' CHECK(status IN ('open', 'in_mediation', 'resolved', 'closed')),
        resolution_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    # 19. Notifications
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        category TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 20. Offers & Coupons
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        discount_percent REAL NOT NULL,
        max_discount REAL,
        min_order_amount REAL DEFAULT 0,
        valid_until TEXT,
        is_active INTEGER DEFAULT 1
    )
    ''')

    # 21. Admin Audit Logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        target_type TEXT NOT NULL,
        target_id INTEGER,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS revoked_tokens (
        token_hash TEXT PRIMARY KEY,
        expires_at INTEGER NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS auth_rate_limits (
        action TEXT NOT NULL,
        client_key TEXT NOT NULL,
        window_start INTEGER NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (action, client_key, window_start)
    )
    ''')

    cursor.execute(
        """
        UPDATE users SET role = 'customer'
        WHERE LOWER(email) = 'admin@veduka.ai'
          AND full_name = 'Super Administrator'
          AND role = 'admin'
        """
    )

    conn.commit()
    if demo_data_enabled():
        seed_initial_data(conn)
    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        return

    print("Seeding initial authentic marketplace data...")

    # Development-only customer and vendor fixtures; administrator accounts must be provisioned out of band.
    cursor.execute('''
    INSERT INTO users (email, phone, password_hash, full_name, role, preferred_language)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', ('customer@veduka.ai', '9800000002', hash_password('customer123'), 'Sravan & Deepthi', 'customer', 'te'))
    customer_id = cursor.lastrowid

    # 3. Demo Vendors
    vendors_data = [
        {
            "email": "nirvana@veduka.ai", "phone": "9800000003", "name": "Nirvana Cinematic Stories",
            "category": "photography", "cities": "Hyderabad, Warangal", "radius": 60, "rating": 4.9, "reviews": 142,
            "image": "https://images.unsplash.com/photo-1537633552985-df8429e8048b?auto=format&fit=crop&w=800&q=80",
            "bio_en": "Award-winning candid wedding photographers capturing timeless South Indian celebrations with 4K cinematography.",
            "bio_te": "దక్షిణ భారతీయ వివాహ వేడుకలను అత్యద్భుతంగా ఒడిసిపట్టే అవార్డు గ్రహీత క్యాండిడ్ ఫోటోగ్రఫీ మరియు సినిమాటిక్ టీమ్.",
            "bio_hi": "साउथ इंडियन शादियों के लिए पुरस्कार विजेता कैंडिड फोटोग्राफी और 4K सिनेमाटोग्राफी।",
            "terms": "30% advance on booking, 50% on event morning, 20% on photo album delivery. Free rescheduling up to 14 days before event.",
            "packages": [
                {
                    "title": "Candid & Traditional Essential Combo", "model": "per_day", "price": 45000, "unit": "day",
                    "inclusions": ["1 Candid Photographer (Sony A7IV)", "1 Traditional 4K Videographer", "100 Color-graded Photos", "Full Ceremony Long Video", "Cloud Gallery"],
                    "exclusions": ["Drone aerial coverage", "Physical velvet album", "Outstation travel allowance"],
                    "addons": [("Drone 4K Aerial Coverage", 12000), ("Pre-Wedding Couple Shoot", 20000)]
                },
                {
                    "title": "Royal Cinema Suite & Album", "model": "per_day", "price": 85000, "unit": "day",
                    "inclusions": ["2 Candid Photographers", "2 Cinematic 4K Videographers", "Drone Aerial Coverage", "3-Min Cinematic Teaser", "Premium Leather Album (40 sheets)"],
                    "exclusions": ["Live satellite broadcast"],
                    "addons": [("Live YouTube / Zoom 1080p Stream", 10000)]
                }
            ],
            "inventory": [
                ("Sony A7IV Full Frame Body", "Cameras", 4, 3, 3000, 10000),
                ("DJI Air 3 4K Drone Unit", "Drones", 2, 2, 6000, 15000)
            ]
        },
        {
            "email": "kalakriti@veduka.ai", "phone": "9800000004", "name": "Kalakriti Stage & Floral Decor",
            "category": "decorations", "cities": "Hyderabad, Secunderabad", "radius": 45, "rating": 4.8, "reviews": 98,
            "image": "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=800&q=80",
            "bio_en": "Eco-friendly temple floral mandaps, contemporary pastel stage decor, and theme backdrops for Pellillu and Sangeets.",
            "bio_te": "సాంప్రదాయ ఆలయ పూల మండపాలు, ఆధునిక పాస్టెల్ స్టేజ్ డెకరేషన్స్ మరియు సంగీత్ థీమ్ బ్యాక్‌డ్రాప్‌లలో నిపుణులు.",
            "bio_hi": "इको-फ्रेंडली मंदिर पुष्प मंडप और शादियों एवं संगीत के लिए आधुनिक थीम सजावट विशेषज्ञ।",
            "terms": "40% advance to secure flower orders. Setup begins 8 hours prior to Muhurtham. 100% refund if cancelled 30 days prior.",
            "packages": [
                {
                    "title": "Traditional Jasmine & Marigold Mandap", "model": "per_event", "price": 38000, "unit": "event",
                    "inclusions": ["16ft x 12ft Jasmine & Marigold Mandap", "Traditional Brass Kuthuvilakku & Urlis", "Floral Entrance Arch", "Warm Spotlight Grid", "Labor Setup & Cleanup"],
                    "exclusions": ["Exotic imported Dutch orchids", "Cold pyro fireworks"],
                    "addons": [("Selfie Floral Photo-Booth", 8000), ("Dry Ice Fog Entry Machine", 5000), ("Cold Pyro Units (4 pcs)", 6000)]
                },
                {
                    "title": "Pastel Luxury Grand Wedding Stage", "model": "per_event", "price": 75000, "unit": "event",
                    "inclusions": ["30ft Royal 3D Carved Backdrop", "Exotic Orchids & Carnations", "Fairy Light Ceiling Canopy", "Royal Velvet Sofa Set", "Monogram LED Signboard"],
                    "exclusions": ["Generator rental fee if venue lacks power"],
                    "addons": [("Grand Entrance Pathway Lights", 12000)]
                }
            ],
            "inventory": [
                ("Royal Golden Maharaja Sofa", "Furniture", 6, 5, 2500, 5000),
                ("Heavy Brass Kuthuvilakku Pair", "Props", 12, 10, 800, 2000),
                ("Dry Ice Fogger Machine 3000W", "Special Effects", 4, 3, 3500, 8000)
            ]
        },
        {
            "email": "annapurna@veduka.ai", "phone": "9800000005", "name": "Annapurna Grand Royal Caterers",
            "category": "catering", "cities": "Vijayawada, Guntur, Hyderabad", "radius": 70, "rating": 4.9, "reviews": 215,
            "image": "https://images.unsplash.com/photo-1555244162-803834f70033?auto=format&fit=crop&w=800&q=80",
            "bio_en": "Authentic Andhra & Rayalaseema culinary feasts with pure ghee sweets, live hot counters, and silver-service banquets.",
            "bio_te": "అసలైన ఆంధ్ర మరియు రాయలసీమ షడ్రుచుల విందు, స్వచ్ఛమైన నెయ్యి మిఠాయిలు మరియు లైవ్ కౌంటర్లతో రుచికరమైన క్యాటరింగ్.",
            "bio_hi": "पारंपरिक आंध्र और शुद्ध शाकाहारी शाही दावत, देसी घी की मिठाइयाँ और लाइव स्टॉल्स।",
            "terms": "Final guest count required 48 hours prior. Minimum order 80 plates. Leftover food packed in hygienic eco-containers for client.",
            "packages": [
                {
                    "title": "Classic Telugu Traditional Bhojanam", "model": "per_plate", "price": 480, "unit": "plate",
                    "inclusions": ["2 Welcome Drinks (Panakam/Majjiga)", "2 Hot Starters (Mirchi Bajji/Cutlet)", "4 Traditional Curries (Gutthi Vankaya)", "Pappu, Sambar, Rasam, Curd", "2 Ghee Sweets (Pootharekulu/Bobbatlu)", "Banana Leaf Setup & Service Staff"],
                    "exclusions": ["Non-vegetarian dishes", "Specialty mocktail bar"],
                    "addons": [("Live Ice Gola & Calcutta Paan", 4500), ("Eco-Friendly Mineral Dispensers", 2500)]
                },
                {
                    "title": "Royal Andhra & North Indian Fusion Feast", "model": "per_plate", "price": 750, "unit": "plate",
                    "inclusions": ["Live Chaat Counter (Pani Puri, Dahi Bhalla)", "Live Tandoori & Dosa Stalls", "Dum Biryani & Mirchi Ka Salan", "5 Main Course Curries + Paneer", "3 Hot Sweets + Artisanal Sundae", "Uniformed Waiters & Buffet Tables"],
                    "exclusions": ["Liquor bar license and bar setup"],
                    "addons": [("Tandoori Naan Live Station", 6000)]
                }
            ],
            "inventory": [
                ("Buffet Stainless Steel Chafing Dish Set", "Catering Utensils", 30, 25, 400, 1000),
                ("Round Banquet Tables with Silk Cloths", "Furniture", 40, 35, 300, 500)
            ]
        },
        {
            "email": "venkateswara@veduka.ai", "phone": "9800000006", "name": "Sri Venkateswara Grand Convention",
            "category": "venues", "cities": "Hyderabad", "radius": 35, "rating": 4.7, "reviews": 86,
            "image": "https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&w=800&q=80",
            "bio_en": "Central AC convention hall accommodating up to 1,200 guests with 4 deluxe guest suites, lush lawn, and 300-car valet parking.",
            "bio_te": "1,200 మంది అతిథుల సామర్థ్యం కలిగిన సెంట్రల్ ఏసీ కన్వెన్షన్ హాల్, 4 డీలక్స్ గదులు మరియు విశాలమైన పార్కింగ్ సౌకర్యం.",
            "bio_hi": "1200 मेहमानों की क्षमता वाला वातानुकूलित भव्य हॉल, 4 डीलक्स रूम और विशाल कार पार्किंग।",
            "terms": "50% advance to lock date. 100% diesel generator fuel backup included. Outside decorators allowed with prior security clearance.",
            "packages": [
                {
                    "title": "Full-Day Grand Auspicious Muhurtham Slot", "model": "fixed", "price": 175000, "unit": "12 hrs",
                    "inclusions": ["Main AC Hall (12,000 sq ft)", "Separate Dining Hall (5,000 sq ft)", "4 AC Bride/Groom Dressing Suites", "Full Generator Power Backup", "Dedicated Cleaning & Security Crew"],
                    "exclusions": ["Mandap decoration", "Catering preparation"],
                    "addons": [("Lush Lawn Cocktail Area", 35000), ("Valet Parking Management Team", 15000)]
                }
            ],
            "inventory": [
                ("Banquet Gold Chiavari Chairs", "Furniture", 500, 450, 40, 100)
            ]
        },
        {
            "email": "sowmya@veduka.ai", "phone": "9800000007", "name": "Sowmya Bridal Studio & Mehendi",
            "category": "makeup", "cities": "Visakhapatnam, Vizianagaram", "radius": 40, "rating": 4.9, "reviews": 167,
            "image": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&w=800&q=80",
            "bio_en": "HD Airbrush bridal makeup, authentic South Indian temple jewelry styling, saree draping, and organic herbal Rajasthani mehendi.",
            "bio_te": "హెచ్‌డీ ఎయిర్‌బ్రష్ బ్రైడల్ మేకప్, సాంప్రదాయ పట్టుచీర డ్రేపింగ్ మరియు స్వచ్ఛమైన ఆర్గానిక్ రాజస్థానీ మెహందీ డిజైన్లు.",
            "bio_hi": "एचडी एयरब्रश ब्राइडल मेकअप, पारंपरिक साउथ इंडियन साड़ी ड्रेपिंग और ऑर्गेनिक मेहंदी आर्ट।",
            "terms": "Non-refundable date lock token ₹3,000. Travel charges apply outside Visakhapatnam city limits. Premium brands: MAC, Huda Beauty, Bobbi Brown.",
            "packages": [
                {
                    "title": "Classic Muhurtham Bridal HD Makeover", "model": "fixed", "price": 18000, "unit": "session",
                    "inclusions": ["HD Waterproof Long-Stay Bridal Makeup", "Traditional Flower Jadai & Hair Styling", "Silk Saree Draping", "Lashes & Colored Lenses", "High-End International Cosmetics"],
                    "exclusions": ["Sider/Family makeup", "Bridal Mehendi"],
                    "addons": [("Mother / Sister Makeup Package", 6000), ("Early Morning 4 AM Travel Allowance", 2500)]
                },
                {
                    "title": "Bridal Complete Duo (HD Makeup + Organic Mehendi)", "model": "fixed", "price": 28000, "unit": "package",
                    "inclusions": ["Muhurtham Bridal HD Makeup", "Intricate Bridal Mehendi (Elbows & Feet)", "1 Sider Makeup", "Touch-up kit"],
                    "exclusions": [],
                    "addons": []
                }
            ],
            "inventory": []
        },
        {
            "email": "beatbazaar@veduka.ai", "phone": "9800000008", "name": "BeatBazaar Live Orchestra & DJ",
            "category": "dj_music", "cities": "Hyderabad, Warangal, Karimnagar", "radius": 75, "rating": 4.8, "reviews": 79,
            "image": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=800&q=80",
            "bio_en": "Electrifying Tollywood, Bollywood, and EDM party DJs with high-output JBL line arrays, moving head lighting, and live Punjabi dhol players.",
            "bio_te": "హై-ఓల్టేజ్ టాలీవుడ్ & బాలీవుడ్ బీట్స్, జేబీఎల్ సౌండ్ సిస్టమ్, మూవింగ్ హెడ్ లైట్స్ మరియు పంజాబీ డోల్ ప్లేయర్స్.",
            "bio_hi": "हाई-एनर्जी टॉलीवुड और बॉलीवुड डीजे, जेबीएल लाइन ऐरे साउंड सिस्टम और लाइव ढोल टीम।",
            "terms": "Sound setup completed 2 hours prior to start. Venue sound permissions and police NOC are client responsibility.",
            "packages": [
                {
                    "title": "Sangeet & Reception High-Output DJ Set", "model": "per_hour", "price": 22000, "unit": "4 hrs",
                    "inclusions": ["Professional Tollywood/Bollywood DJ", "JBL 5000W Line Array Sound (up to 400 pax)", "4 Moving Head Intelligent Lights", "2 Cordless Mics for Emcee", "4 Hours Performance"],
                    "exclusions": ["Additional hours (charged ₹4,000/hr)", "Live Dhol players"],
                    "addons": [("Live Nasik Dhol Duo for Baraat", 8000), ("CO2 Smoke Jet Canon (2 shots)", 4500)]
                }
            ],
            "inventory": [
                ("JBL Dual 18-inch Subwoofer Pair", "Sound Equipment", 4, 3, 4000, 10000),
                ("Sharpy Moving Head Light 230W", "Lighting", 12, 10, 1000, 3000)
            ]
        }
    ]

    for v in vendors_data:
        cursor.execute('''
        INSERT INTO users (email, phone, password_hash, full_name, role, preferred_language)
        VALUES (?, ?, ?, ?, 'vendor', 'en')
        ''', (v["email"], v["phone"], hash_password("vendor123"), v["name"]))
        u_id = cursor.lastrowid

        cursor.execute('''
        INSERT INTO vendor_profiles (user_id, business_name, category, cities, service_radius_km, kyc_verified, rating_avg, review_count, bio_en, bio_te, bio_hi, image_url, terms_and_conditions)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
        ''', (u_id, v["name"], v["category"], v["cities"], v["radius"], v["rating"], v["reviews"], v["bio_en"], v["bio_te"], v["bio_hi"], v["image"], v["terms"]))
        v_id = cursor.lastrowid

        for pkg in v["packages"]:
            cursor.execute('''
            INSERT INTO packages (vendor_id, title, category, pricing_model, base_price, unit, inclusions_json, exclusions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (v_id, pkg["title"], v["category"], pkg["model"], pkg["price"], pkg["unit"], json.dumps(pkg["inclusions"]), json.dumps(pkg["exclusions"])))
            p_id = cursor.lastrowid

            for addon_name, addon_price in pkg.get("addons", []):
                cursor.execute('''
                INSERT INTO package_addons (package_id, title, price)
                VALUES (?, ?, ?)
                ''', (p_id, addon_name, addon_price))

        for item_name, cat, total, avail, r_price, dep in v.get("inventory", []):
            cursor.execute('''
            INSERT INTO inventory_items (vendor_id, item_name, category, total_stock, available_stock, rental_price_per_day, security_deposit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (v_id, item_name, cat, total, avail, r_price, dep))

    # 4. Create a Sample Event for Demo Customer
    cursor.execute('''
    INSERT INTO events (customer_id, title, event_type, event_date, city, venue, guest_count, total_budget, theme_name, color_palette, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (customer_id, 'Sravan & Deepthi Pellillu (Wedding)', 'wedding', '2026-11-28', 'Hyderabad', 'Sri Venkateswara Grand Convention', 300, 500000, 'Temple Jasmine & Contemporary Pastel Glow', 'Temple Gold, Marigold Yellow, Pastel Peach', 'in_progress'))
    sample_event_id = cursor.lastrowid

    # Add Budget Items for the event
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount, spent_amount) VALUES (?, 'catering', 200000, 144000)", (sample_event_id,))
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount, spent_amount) VALUES (?, 'venues', 175000, 175000)", (sample_event_id,))
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount, spent_amount) VALUES (?, 'decorations', 60000, 38000)", (sample_event_id,))
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount, spent_amount) VALUES (?, 'photography', 50000, 45000)", (sample_event_id,))
    cursor.execute("INSERT INTO budget_items (event_id, category, allocated_amount, spent_amount) VALUES (?, 'dj_music', 15000, 0)", (sample_event_id,))

    # Add Sample Quotation & Booking
    cursor.execute('''
    INSERT INTO quotation_requests (event_id, customer_id, vendor_id, category, event_date, guest_count, requirements, status)
    VALUES (?, ?, 1, 'photography', '2026-11-28', 300, 'Need candid photography + drone for Muhurtham ceremony', 'quoted')
    ''', (sample_event_id, customer_id))
    req_id = cursor.lastrowid

    cursor.execute('''
    INSERT INTO quotations (request_id, event_id, customer_id, vendor_id, version, subtotal, discount_amount, tax_amount, platform_fee, total_amount, advance_required, terms_and_notes, validity_date, status)
    VALUES (?, ?, ?, 1, 1, 45000, 2000, 2250, 750, 46000, 15000, 'Special 5% wedding season discount included. Deliverables ready within 14 days.', '2026-11-15', 'accepted')
    ''', (req_id, sample_event_id, customer_id))
    quote_id = cursor.lastrowid

    cursor.execute('''
    INSERT INTO quotation_items (quotation_id, item_name, quantity, unit_price, total_price)
    VALUES (?, 'Candid & Traditional Essential Combo (Sony A7IV)', 1, 45000, 45000)
    ''', (quote_id,))

    # Create Booking
    cursor.execute('''
    INSERT INTO bookings (event_id, quotation_id, customer_id, vendor_id, service_category, total_amount, advance_paid, balance_amount, payment_status, booking_status)
    VALUES (?, ?, ?, 1, 'photography', 46000, 15000, 31000, 'advance_paid', 'confirmed')
    ''', (sample_event_id, quote_id, customer_id))
    booking_id = cursor.lastrowid

    # Create 5 Tracking Milestones for the Booking
    milestones = [
        (1, "Booking & Advance Secured", "15,000 INR advance received. Date officially locked in photographer calendar.", "completed", "2026-10-15 10:30:00"),
        (2, "Pre-Event Coordination & Shot-list", "Client moodboard reviewed. Muhurtham timings and key family shotlist finalized.", "in_progress", None),
        (3, "Event Day Venue Check-in", "Photographer and drone team arrival at venue 2 hours before Muhurtham.", "pending", None),
        (4, "Raw Footage & Teaser Delivery", "Initial curated 100 color-graded photos and 3-minute teaser uploaded.", "pending", None),
        (5, "Final Album Handover & Settlement", "Physical leather album dispatched, digital cloud access provided, balance released.", "pending", None)
    ]
    for stage, title, desc, status, comp_at in milestones:
        cursor.execute('''
        INSERT INTO booking_milestones (booking_id, stage_number, title, description, status, completed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (booking_id, stage, title, desc, status, comp_at))

    # Add Event Day Master Run-Sheet (Coordination)
    runsheet_items = [
        ("06:30 AM", "Convention hall gates open & power backup line check", "Venue Manager - Ramesh", "9800000006"),
        ("07:30 AM", "Stage floral mandap and entrance arch installation begins", "Kalakriti Decor - Satish", "9800000004"),
        ("09:00 AM", "Bridal makeup artist session starts in dressing suite", "Sowmya Bridal Studio", "9800000007"),
        ("10:00 AM", "Candid photographer & 4K camera crew arrival & gear setup", "Nirvana Photo - Vikram", "9800000003"),
        ("11:15 AM", "Muhurtham ceremony starts on floral stage", "Family Priest / Sravan", "9800000002"),
        ("01:00 PM", "Traditional banana leaf royal lunch buffet opens in dining hall", "Annapurna Caterers - Murthy", "9800000005")
    ]
    for time_slot, act, c_name, c_phone in runsheet_items:
        cursor.execute('''
        INSERT INTO event_runsheet (event_id, time_slot, activity, contact_name, contact_phone, is_completed)
        VALUES (?, ?, ?, ?, ?, 0)
        ''', (sample_event_id, time_slot, act, c_name, c_phone))

    # Add Sample Guests & QR Code tokens
    sample_guests = [
        ("Rao Garu & Family", "9848011223", "groom", "veg", "attending", 4, "Table A1", "GUEST-RAO-9848"),
        ("Venkat Reddy & Family", "9848022334", "bride", "non_veg", "attending", 3, "Table B2", "GUEST-REDDY-9848"),
        ("Dr. Lakshmi Prasad", "9848033445", "vip", "veg", "attending", 2, "VIP Lounge", "GUEST-PRASAD-VIP"),
        ("Ananya Sharma", "9848044556", "common", "jain", "pending", 1, "Table C3", "GUEST-ANANYA-7711")
    ]
    for g_name, g_phone, side, diet, rsvp, g_count, tbl, token in sample_guests:
        cursor.execute('''
        INSERT INTO guests (event_id, full_name, phone, side, dietary, rsvp_status, guest_count, table_number, qr_code_token)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sample_event_id, g_name, g_phone, side, diet, rsvp, g_count, tbl, token))

    # Add Notifications
    cursor.execute('''
    INSERT INTO notifications (user_id, title, message, category)
    VALUES (?, 'Advance Payment Verified', 'Your 15,000 INR advance for Nirvana Cinematic Stories is locked in escrow.', 'booking')
    ''', (customer_id,))
    cursor.execute('''
    INSERT INTO notifications (user_id, title, message, category)
    VALUES (?, 'Quotation Accepted by Client!', 'Sravan & Deepthi approved your Photography quote of 46,000 INR.', 'quotation')
    ''', (2,)) # vendor 1 user id

    # Add Offers
    cursor.execute('''
    INSERT INTO offers (vendor_id, code, title, discount_percent, max_discount, min_order_amount, valid_until)
    VALUES (1, 'WEDDING2026', 'Auspicious Muhurtham Early Bird Special', 10.0, 5000, 40000, '2026-12-31')
    ''')
    cursor.execute('''
    INSERT INTO offers (vendor_id, code, title, discount_percent, max_discount, min_order_amount, valid_until)
    VALUES (2, 'MANDAP5', 'Festive Stage Decor Discount', 5.0, 3000, 35000, '2026-12-31')
    ''')

    conn.commit()
    print("Database seeding completed successfully.")
