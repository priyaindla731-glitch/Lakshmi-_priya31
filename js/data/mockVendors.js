// Realistic mock vendors data with transparent itemized pricing & service details
export const mockVendors = [
  {
    id: "v-01",
    name: "Nirvana Cinematic Stories",
    category: "photography",
    rating: 4.9,
    reviewCount: 142,
    city: "Hyderabad",
    areas: "Banjara Hills, Jubilee Hills, Gachibowli",
    serviceRadiusKm: 50,
    badge: "Verified Pro",
    availability: "Available This Weekend",
    availabilityType: "available",
    image: "https://images.unsplash.com/photo-1537633552985-df8429e8048b?auto=format&fit=crop&w=800&q=80",
    basePriceDisplay: "₹45,000",
    priceUnit: "per day",
    pricingModel: "per_day",
    responseTime: "Responds in < 15 mins",
    description: {
      en: "Award-winning candid wedding photographers and cinematic filmmakers capturing timeless South Indian celebrations.",
      te: "దక్షిణ భారతీయ వివాహ వేడుకలను అత్యద్భుతంగా ఒడిసిపట్టే అవార్డు గ్రహీత క్యాండిడ్ ఫోటోగ్రఫీ మరియు సినిమాటిక్ టీమ్.",
      hi: "पुरस्कार विजेता कैंडिड वेडिंग फोटोग्राफर और साउथ इंडियन शादियों के लिए सिनेमैटिक फिल्म मेकर्स।"
    },
    itemizedPackages: [
      {
        name: "Candid & Traditional Combo",
        price: 45000,
        inclusions: [
          "1 Candid Photographer (Sony A7IV)",
          "1 Traditional Videographer (4K)",
          "100 Edited High-Res Photos",
          "Full Ceremony Long Video (HD)",
          "Online Cloud Gallery Access"
        ]
      },
      {
        name: "Royal Cinematic Suite",
        price: 85000,
        inclusions: [
          "2 Candid Photographers",
          "2 Cinematic Videographers",
          "Drone Aerial 4K Coverage",
          "3-Minute Cinematic Teaser Video",
          "Premium Leather Bound Hardcover Album (40 Sheets)",
          "Raw Footage on 1TB Hard Drive"
        ]
      }
    ],
    addOns: [
      { name: "Drone Aerial Coverage", price: 12000 },
      { name: "Live YouTube / Zoom Streaming", price: 10000 },
      { name: "Pre-Wedding Couple Shoot", price: 20000 }
    ]
  },
  {
    id: "v-02",
    name: "Kalakriti Stage & Floral Decorators",
    category: "decorations",
    rating: 4.8,
    reviewCount: 98,
    city: "Hyderabad",
    areas: "Madhapur, Secunderabad, Kukatpally",
    serviceRadiusKm: 40,
    badge: "Trending",
    availability: "Fast Booking",
    availabilityType: "popular",
    image: "https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=800&q=80",
    basePriceDisplay: "₹38,000",
    priceUnit: "per event",
    pricingModel: "per_event",
    responseTime: "Responds in < 30 mins",
    description: {
      en: "Eco-friendly temple floral mandaps, contemporary pastel stage decor, and theme backdrops for Pellillu and Sangeets.",
      te: "సాంప్రదాయ ఆలయ పూల మండపాలు, ఆధునిక పాస్టెల్ స్టేజ్ డెకరేషన్స్ మరియు సంగీత్ థీమ్ బ్యాక్‌డ్రాప్‌లలో నిపుణులు.",
      hi: "इको-फ्रेंडली मंदिर पुष्प मंडप और शादियों एवं संगीत के लिए आधुनिक थीम सजावट विशेषज्ञ।"
    },
    itemizedPackages: [
      {
        name: "Traditional Floral Mandap",
        price: 38000,
        inclusions: [
          "16ft x 12ft Jasmine & Marigold Floral Mandap",
          "Traditional Brass Kuthuvilakku & Urlis",
          "Entrance Floral Archway",
          "Warm LED Focus Spotlight Grid",
          "Setup & Teardown Labor Included"
        ]
      },
      {
        name: "Pastel Luxury Grand Stage",
        price: 75000,
        inclusions: [
          "30ft Royal 3D Carved Backdrop",
          "Exotic Orchid, Carnation & Rose Arrangements",
          "Fairy Light Ceiling Canopy",
          "Stage Velvet Carpet & Royal Sofa Set",
          "Custom Monogram LED Signboard"
        ]
      }
    ],
    addOns: [
      { name: "Selfie Floral Photo-Booth", price: 8000 },
      { name: "Dry Ice Fog Entry Machine", price: 5000 },
      { name: "Cold Pyro Fireworks (4 units)", price: 6000 }
    ]
  },
  {
    id: "v-03",
    name: "Annapurna Grand Royal Caterers",
    category: "catering",
    rating: 4.9,
    reviewCount: 215,
    city: "Vijayawada",
    areas: "Benz Circle, MG Road, Guntur highway",
    serviceRadiusKm: 60,
    badge: "Top Rated",
    availability: "Available for Muhurtham",
    availabilityType: "available",
    image: "https://images.unsplash.com/photo-1555244162-803834f70033?auto=format&fit=crop&w=800&q=80",
    basePriceDisplay: "₹480",
    priceUnit: "per plate",
    pricingModel: "per_plate",
    responseTime: "Responds in < 10 mins",
    description: {
      en: "Authentic Andhra & Rayalaseema culinary feasts with pure ghee sweets, live live live counters, and silver-service banquets.",
      te: "అసలైన ఆంధ్ర మరియు రాయలసీమ షడ్రుచుల విందు, స్వచ్ఛమైన నెయ్యి మిఠాయిలు మరియు లైవ్ కౌంటర్లతో రుచికరమైన క్యాటరింగ్.",
      hi: "पारंपरिक आंध्र और शुद्ध शाकाहारी शाही दावत, देसी घी की मिठाइयाँ और लाइव स्टॉल्स।"
    },
    itemizedPackages: [
      {
        name: "Classic Telugu Traditional Bhojanam",
        price: 480,
        inclusions: [
          "2 Welcome Drinks (Panakam / Majjiga)",
          "2 Starters (Mirchi Bajji / Veg Cutlet)",
          "4 Traditional Curries (Gutthi Vankaya, etc.)",
          "Pappu, Sambar, Rasam, Curd",
          "2 Hot Sweets (Pootharekulu / Bobbatlu)",
          "Banana Leaf Setup & Service Staff"
        ]
      },
      {
        name: "Royal Andhra & North Indian Fusion Feast",
        price: 750,
        inclusions: [
          "Live Chaat Counter (Pani Puri, Dahi Bhalla)",
          "Live Dosa & Tandoori Counter",
          "Hyderabadi Dum Biryani & Mirchi Ka Salan",
          "5 Main Course Dishes + Paneer Delicacies",
          "3 Desserts + Artisanal Ice Cream Sundae",
          "Custom Buffet Setup & Uniformed Waiters"
        ]
      }
    ],
    addOns: [
      { name: "Live Ice Gola & Paan Counter", price: 4500 },
      { name: "Mineral Water Dispensers (Eco-friendly)", price: 2500 }
    ]
  },
  {
    id: "v-04",
    name: "Sri Venkateswara Grand Palace Convention",
    category: "venues",
    rating: 4.7,
    reviewCount: 86,
    city: "Hyderabad",
    areas: "Kompally, Medchal Road",
    serviceRadiusKm: 30,
    badge: "Verified Venue",
    availability: "Few Dates Open for Nov-Dec",
    availabilityType: "popular",
    image: "https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&w=800&q=80",
    basePriceDisplay: "₹1,75,000",
    priceUnit: "per slot (12 hrs)",
    pricingModel: "fixed",
    responseTime: "Responds in < 1 hour",
    description: {
      en: "Central AC convention hall accommodating up to 1,200 guests with 4 guest suites, lush lawn, and 300-car valet parking.",
      te: "1,200 మంది అతిథుల సామర్థ్యం కలిగిన సెంట్రల్ ఏసీ కన్వెన్షన్ హాల్, 4 డీలక్స్ గదులు మరియు విశాలమైన పార్కింగ్ సౌకర్యం.",
      hi: "1200 मेहमानों की क्षमता वाला सेंट्रली वातानुकूलित भव्य हॉल, 4 डीलक्स रूम और विशाल कार पार्किंग।"
    },
    itemizedPackages: [
      {
        name: "Full-Day Grand Auspicious Slot",
        price: 175000,
        inclusions: [
          "Main Air-Conditioned Hall (12,000 sq ft)",
          "Separate Dining Hall (5,000 sq ft)",
          "4 Air-Conditioned Bride/Groom Dressing Suites",
          "Full Diesel Generator Power Backup",
          "Cleaning & Waste Disposal Staff"
        ]
      }
    ],
    addOns: [
      { name: "Lush Lawn Cocktail Area", price: 35000 },
      { name: "Valet Parking Management Team", price: 15000 }
    ]
  },
  {
    id: "v-05",
    name: "Sowmya Bridal Studio & Mehendi Art",
    category: "makeup",
    rating: 4.9,
    reviewCount: 167,
    city: "Visakhapatnam",
    areas: "MVP Colony, Siripuram, Gajuwaka",
    serviceRadiusKm: 35,
    badge: "Celebrity Artist",
    availability: "Available for Muhurtham",
    availabilityType: "available",
    image: "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&w=800&q=80",
    basePriceDisplay: "₹18,000",
    priceUnit: "per session",
    pricingModel: "per_session",
    responseTime: "Responds in < 20 mins",
    description: {
      en: "HD Airbrush bridal makeup, authentic South Indian temple jewelry styling, saree draping, and organic herbal Rajasthani mehendi.",
      te: "హెచ్‌డీ ఎయిర్‌బ్రష్ బ్రైడల్ మేకప్, సాంప్రదాయ పట్టుచీర డ్రేపింగ్ మరియు స్వచ్ఛమైన ఆర్గానిక్ రాజస్థానీ మెహందీ డిజైన్లు.",
      hi: "एचडी एयरब्रश ब्राइडल मेकअप, पारंपरिक साउथ इंडियन साड़ी ड्रेपिंग और ऑर्गेनिक मेहंदी आर्ट।"
    },
    itemizedPackages: [
      {
        name: "Classic Muhurtham Bridal HD Makeover",
        price: 18000,
        inclusions: [
          "HD Long-Stay Waterproof Bridal Makeup",
          "Traditional Flower Jadai & Hair Styling",
          "Intricate Bridal Silk Saree Draping",
          "False Eyelashes & Lens Fitting",
          "High-End International Brands (MAC / Huda / Bobbi Brown)"
        ]
      },
      {
        name: "Bridal Complete Duo (Makeup + Bridal Mehendi)",
        price: 28000,
        inclusions: [
          "Muhurtham Bridal HD Makeup",
          "Intricate Bridal Mehendi (Elbows & Feet)",
          "1 Sider / Mother-of-Bride Makeup",
          "Premium Touch-up Travel Kit"
        ]
      }
    ],
    addOns: [
      { name: "Mother / Sister Makeup Package", price: 6000 },
      { name: "Early Morning Muhurtham (4 AM) Travel Surcharge", price: 2500 }
    ]
  },
  {
    id: "v-06",
    name: "BeatBazaar Live Orchestra & DJ Sound",
    category: "dj_music",
    rating: 4.8,
    reviewCount: 79,
    city: "Hyderabad",
    areas: "All Hyderabad & Secunderabad",
    serviceRadiusKm: 60,
    badge: "Party Favorite",
    availability: "Available This Weekend",
    availabilityType: "available",
    image: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=800&q=80",
    basePriceDisplay: "₹22,000",
    priceUnit: "for 4 hours",
    pricingModel: "per_event",
    responseTime: "Responds in < 15 mins",
    description: {
      en: "Electrifying Tollywood, Bollywood, and EDM party DJs with high-output JBL line arrays, truss lighting, and live dhol players.",
      te: "హై-ఓల్టేజ్ టాలీవుడ్ & బాలీవుడ్ బీట్స్, జేబీఎల్ సౌండ్ సిస్టమ్, మూవింగ్ హెడ్ లైట్స్ మరియు పంజాబీ డోల్ ప్లేయర్స్.",
      hi: "हाई-एनर्जी टॉलीवुड और बॉलीवुड डीजे, जेबीएल लाइन ऐरे साउंड सिस्टम और लाइव ढोल टीम।"
    },
    itemizedPackages: [
      {
        name: "Sangeet / Reception DJ Essentials",
        price: 22000,
        inclusions: [
          "Professional Event DJ (Tollywood / Bollywood / Commercial)",
          "JBL 5000W Sound System (Up to 300 pax)",
          "4 LED Moving Head Intelligent Lights",
          "2 Wireless Microphones for Emcee / Family",
          "4 Hours Continuous Performance"
        ]
      }
    ],
    addOns: [
      { name: "Live Nasik Dhol Duo (2 Players for Baraat)", price: 8000 },
      { name: "High-Power CO2 Smoke Jet Canon", price: 4500 }
    ]
  }
];

export const eventCategories = [
  { id: "all", icon: "✨", labelEn: "All Services", labelTe: "అన్ని సేవలు", labelHi: "सभी सेवाएँ" },
  { id: "photography", icon: "📸", labelEn: "Photography", labelTe: "ఫోటోగ్రఫీ", labelHi: "फोटोग्राफी" },
  { id: "decorations", icon: "🌸", labelEn: "Decorations", labelTe: "డెకరేషన్స్", labelHi: "सजावट" },
  { id: "catering", icon: "🍲", labelEn: "Catering", labelTe: "క్యాటరింగ్", labelHi: "केटरिंग" },
  { id: "venues", icon: "🏛️", labelEn: "Venues", labelTe: "కళ్యాణ మండపాలు", labelHi: "वेन्यू एवं हॉल" },
  { id: "makeup", icon: "💄", labelEn: "Makeup & Mehendi", labelTe: "మేకప్ & మెహందీ", labelHi: "मेकअप और मेहंदी" },
  { id: "dj_music", icon: "🎵", labelEn: "Music & DJ", labelTe: "సంగీతం & డీజే", labelHi: "संगीत और डीजे" }
];

export const citiesList = [
  "All Cities",
  "Hyderabad",
  "Vijayawada",
  "Visakhapatnam",
  "Warangal",
  "Guntur",
  "Tirupati",
  "Bengaluru"
];
