import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.app import app

def main():
    port = int(os.environ.get("PORT", 3000))
    print("=" * 65)
    print("  VEDUKA AI - ALL-IN-ONE AI EVENT MARKETPLACE")
    print(f">> Server Running at: http://localhost:{port}")
    print(f">> Network Access:   http://127.0.0.1:{port}")
    print(">> SQLite Database:  veduka.db (ACID Persistent Relational)")
    print(">> Multilingual:     Telugu (te) • Hindi (hi) • English (en)")
    print("=" * 65)
    sys.stdout.flush()
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == '__main__':
    main()
