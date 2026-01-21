import sqlite3

def view_db():
    print("--- 📂 Opening bot_data.db ---")
    try:
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        
        # Check Keywords
        print("\n--- 🔑 Keywords ---")
        cursor.execute("SELECT keyword, created_at FROM keywords")
        keywords = cursor.fetchall()
        if keywords:
            for k in keywords:
                print(f"• {k[0]} (Added: {k[1]})")
        else:
            print("(No keywords found)")

        # Check History
        print("\n--- 📚 History (Last 5 Entries) ---")
        cursor.execute("SELECT link, title, summary, category, tags, created_at FROM history ORDER BY created_at DESC LIMIT 5")
        history = cursor.fetchall()
        if history:
            for h in history:
                title = h[1] if h[1] else "(No Title)"
                category = h[3] if h[3] else "N/A"
                tags = h[4] if h[4] else "N/A"
                
                print(f"• {title}")
                print(f"  📂 {category} | 🏷 {tags}")
                print(f"  Link: {h[0]}")
                print(f"  (Sent: {h[5]})")
        else:
            print("(History is empty)")
            
        # Stats
        cursor.execute("SELECT COUNT(*) FROM history")
        count = cursor.fetchone()[0]
        print(f"\nTotal Articles Sent: {count}")
        
    except sqlite3.OperationalError:
        print("Error: 'bot_data.db' not found. Run 'python bot.py' first to create and migrate it.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    view_db()
