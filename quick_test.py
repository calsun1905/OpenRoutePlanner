"""
Quick test to check if everything is working
"""

import os
import sys

def check_files():
    """Check if all required files exist"""
    print("=" * 60)
    print("📁 Dosya Kontrolü")
    print("=" * 60)
    
    files = [
        "backend/app.py",
        "frontend/index.html",
        "frontend/css/style.css",
        "frontend/js/app.js"
    ]
    
    all_ok = True
    for file in files:
        exists = os.path.exists(file)
        status = "✅" if exists else "❌"
        print(f"{status} {file}")
        if not exists:
            all_ok = False
    
    return all_ok

def check_backend():
    """Check if backend can be imported"""
    print("\n" + "=" * 60)
    print("🔧 Backend Kontrolü")
    print("=" * 60)
    
    try:
        sys.path.insert(0, 'backend')
        from app import app
        print("✅ Backend import edildi")
        print(f"✅ Frontend klasörü: {app.static_folder}")
        return True
    except Exception as e:
        print(f"❌ Backend import hatası: {e}")
        return False

def check_frontend_structure():
    """Check frontend HTML structure"""
    print("\n" + "=" * 60)
    print("📄 Frontend Yapı Kontrolü")
    print("=" * 60)
    
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            content = f.read()
        
        checks = [
            ("<!DOCTYPE html>", "DOCTYPE"),
            ("<body>", "Body tag"),
            ("</body>", "Body kapanış"),
            ("</html>", "HTML kapanış"),
            ('id="map"', "Harita container"),
            ('id="sidebar"', "Sidebar"),
            ("css/style.css", "CSS linki"),
            ("js/app.js", "JS linki")
        ]
        
        all_ok = True
        for check, name in checks:
            exists = check in content
            status = "✅" if exists else "❌"
            print(f"{status} {name}")
            if not exists:
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f"❌ HTML okuma hatası: {e}")
        return False

def main():
    print("\n🔍 OpenRoutePlanner Hızlı Test\n")
    
    results = []
    
    # Test 1: Files
    results.append(("Dosyalar", check_files()))
    
    # Test 2: Backend
    results.append(("Backend", check_backend()))
    
    # Test 3: Frontend
    results.append(("Frontend", check_frontend_structure()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ÖZET")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ BAŞARILI" if passed else "❌ BAŞARISIZ"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✅ TÜM TESTLER BAŞARILI!")
        print("\nBackend'i başlatmak için:")
        print("  cd backend")
        print("  python app.py")
        print("\nSonra tarayıcıda:")
        print("  http://localhost:5000")
    else:
        print("❌ BAZI TESTLER BAŞARISIZ!")
        print("\nLütfen yukarıdaki hataları düzeltin.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
