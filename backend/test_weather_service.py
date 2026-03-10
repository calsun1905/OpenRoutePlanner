"""
test_weather_service.py - Hava durumu servisi test script'i

OpenMeteo API entegrasyonunu test eder.
Faz 1 endpoint'lerini dogrular.

Author: OpenRoutePlanner
Created: 2026-03-10
"""

import sys
import os

# Backend klasorunu path'e ekle
sys.path.insert(0, os.path.dirname(__file__))

from weather_utils import (
    validate_coordinates,
    validate_hours,
    parse_weather_code,
    get_weather_emoji,
    build_cache_key,
    format_temperature,
    get_weather_alert,
    get_activity_suggestion
)


# =============================================================================
# TEST UTILITIES
# =============================================================================

def print_test_header(test_name: str):
    """Test basligi yazdirir."""
    print("\n" + "=" * 60)
    print(f"  TEST: {test_name}")
    print("=" * 60)


def print_result(passed: bool, message: str = ""):
    """Test sonucunu yazdirir."""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}" + (f": {message}" if message else ""))
    return passed


# =============================================================================
# WEATHER UTILS TESTS
# =============================================================================

def test_validate_coordinates():
    """Koordinat validasyonunu test eder."""
    print_test_header("Coordinate Validation")

    results = []

    # Gecerli koordinatlar
    results.append(print_result(
        validate_coordinates(41.0082, 28.9784),
        "Istanbul koordinatlari gecerli"
    ))
    results.append(print_result(
        validate_coordinates(0, 0),
        "Ekvator koordinatlari gecerli"
    ))
    results.append(print_result(
        validate_coordinates(-90, -180),
        "Min koordinatlar gecerli"
    ))
    results.append(print_result(
        validate_coordinates(90, 180),
        "Max koordinatlar gecerli"
    ))

    # Gecersiz koordinatlar
    results.append(print_result(
        not validate_coordinates(91, 0),
        "Lat > 90 gecersiz"
    ))
    results.append(print_result(
        not validate_coordinates(-91, 0),
        "Lat < -90 gecersiz"
    ))
    results.append(print_result(
        not validate_coordinates(0, 181),
        "Lon > 180 gecersiz"
    ))
    results.append(print_result(
        not validate_coordinates(0, -181),
        "Lon < -180 gecersiz"
    ))

    return all(results)


def test_validate_hours():
    """Saat validasyonunu test eder."""
    print_test_header("Hours Validation")

    results = []

    # Gecerli saatler
    results.append(print_result(
        validate_hours(1),
        "Min saat (1) gecerli"
    ))
    results.append(print_result(
        validate_hours(24),
        "Varsayilan saat (24) gecerli"
    ))
    results.append(print_result(
        validate_hours(168),
        "Max saat (168) gecerli"
    ))

    # Gecersiz saatler
    results.append(print_result(
        not validate_hours(0),
        "0 saat gecersiz"
    ))
    results.append(print_result(
        not validate_hours(169),
        "169 saat gecersiz (max 168)"
    ))
    results.append(print_result(
        not validate_hours(-1),
        "Negatif saat gecersiz"
    ))

    return all(results)


def test_parse_weather_code():
    """WMO weather code parse etmeyi test eder."""
    print_test_header("Weather Code Parsing")

    results = []

    # Clear sky
    parsed = parse_weather_code(0)
    results.append(print_result(
        parsed["description"] == "Clear sky",
        f"Code 0: {parsed['description']}"
    ))
    results.append(print_result(
        parsed["icon"] == "sun",
        "Icon: sun"
    ))

    # Rain
    parsed = parse_weather_code(61)
    results.append(print_result(
        parsed["description"] == "Slight rain",
        f"Code 61: {parsed['description']}"
    ))
    results.append(print_result(
        parsed["category"] == "rain",
        "Category: rain"
    ))

    # Snow
    parsed = parse_weather_code(71)
    results.append(print_result(
        parsed["description"] == "Slight snow fall",
        f"Code 71: {parsed['description']}"
    ))

    # Thunderstorm
    parsed = parse_weather_code(95)
    results.append(print_result(
        parsed["description"] == "Thunderstorm",
        f"Code 95: {parsed['description']}"
    ))

    # Unknown code
    parsed = parse_weather_code(999)
    results.append(print_result(
        parsed["description"] == "Unknown",
        "Bilinmeyen kod: Unknown"
    ))

    return all(results)


def test_get_weather_emoji():
    """Emoji donusumunu test eder."""
    print_test_header("Weather Emoji")

    results = []

    emoji_map = {
        0: "sun_icon",
        3: "cloud_icon",
        61: "rain_icon",
        71: "snow_icon",
        95: "storm_icon"
    }

    for code, _ in emoji_map.items():
        emoji = get_weather_emoji(code)
        results.append(print_result(
            emoji is not None and len(emoji) > 0,
            f"Code {code}: emoji exists"
        ))

    return all(results)


def test_build_cache_key():
    """Cache key olusturmayi test eder."""
    print_test_header("Cache Key Building")

    results = []

    # Current weather key
    key = build_cache_key("current", 41.0082, 28.9784)
    expected = "current:41.0082:28.9784"
    results.append(print_result(
        key == expected,
        f"Current key: {key}"
    ))

    # Hourly forecast key
    key = build_cache_key("hourly", 41.0082, 28.9784, hours=24)
    expected = "hourly:41.0082:28.9784:24"
    results.append(print_result(
        key == expected,
        f"Hourly key: {key}"
    ))

    # Farkli parametreler
    key1 = build_cache_key("current", 41.0082, 28.9784)
    key2 = build_cache_key("current", 41.0082, 28.9785)
    results.append(print_result(
        key1 != key2,
        "Farkli lon farkli key"
    ))

    return all(results)


def test_format_temperature():
    """Sicaklik formatlamayi test eder."""
    print_test_header("Temperature Formatting")

    results = []

    # Celsius
    temp_str = format_temperature(15.5)
    results.append(print_result(
        temp_str == "15.5°C",
        f"15.5°C: {temp_str}"
    ))

    # Fahrenheit
    temp_str = format_temperature(15.5, "fahrenheit")
    results.append(print_result(
        "59.9°F" in temp_str,
        f"Fahrenheit: {temp_str}"
    ))

    # Negatif sicaklik
    temp_str = format_temperature(-5.2)
    results.append(print_result(
        "-5.2°C" in temp_str,
        f"Negatif: {temp_str}"
    ))

    return all(results)


def test_weather_alerts():
    """Hava durumu uyarilarini test eder."""
    print_test_header("Weather Alerts")

    results = []

    # Yagmur uyarisi
    weather = {"temperature": 20, "precipitation": 3.0, "wind_gusts": 10}
    alert = get_weather_alert(weather)
    results.append(print_result(
        alert is not None and "yagmur" in alert.lower(),
        f"Yagmur uyarisi: {alert}"
    ))

    # Sicaklik uyarisi
    weather = {"temperature": 38, "precipitation": 0, "wind_gusts": 10}
    alert = get_weather_alert(weather)
    results.append(print_result(
        alert is not None and "sicak" in alert.lower(),
        f"Sicaklik uyarisi: {alert}"
    ))

    # Ruzgar uyarisi
    weather = {"temperature": 20, "precipitation": 0, "wind_gusts": 55}
    alert = get_weather_alert(weather)
    results.append(print_result(
        alert is not None and "ruzgar" in alert.lower(),
        f"Ruzgar uyarisi: {alert}"
    ))

    # Uyari yok
    weather = {"temperature": 22, "precipitation": 0, "wind_gusts": 10}
    alert = get_weather_alert(weather)
    results.append(print_result(
        alert is None,
        "Uyari yok (hafif hava)"
    ))

    return all(results)


def test_activity_suggestions():
    """Aktivite onerilerini test eder."""
    print_test_header("Activity Suggestions")

    results = []

    # Yagmurlu hava
    weather = {"temperature": 15, "precipitation": 2.0, "weather_code": 61}
    suggestions = get_activity_suggestion(weather)
    results.append(print_result(
        "kapali" in suggestions["outdoor"].lower(),
        f"Yagmurda kapali mekan onerisi: {suggestions['outdoor']}"
    ))

    # Cok sicak
    weather = {"temperature": 35, "precipitation": 0, "weather_code": 0}
    suggestions = get_activity_suggestion(weather)
    results.append(print_result(
        "klimali" in suggestions["outdoor"].lower() or "golge" in suggestions["outdoor"].lower(),
        f"Sicakta soguk oneri: {suggestions['outdoor']}"
    ))

    # Normal hava
    weather = {"temperature": 20, "precipitation": 0, "weather_code": 0}
    suggestions = get_activity_suggestion(weather)
    results.append(print_result(
        len(suggestions["general"]) > 0,
        f"Normal hava onerisi: {suggestions['general']}"
    ))

    return all(results)


# =============================================================================
# WEATHER SERVICE API TESTS
# =============================================================================

def test_weather_service_import():
    """Weather service import'unu test eder."""
    print_test_header("Weather Service Import")

    try:
        from weather_service import (
            get_current_weather,
            get_hourly_forecast,
            check_route_weather,
            get_service_status
        )
        print_result(True, "Weather service basariyla import edildi")
        return True
    except ImportError as e:
        print_result(False, f"Import hatasi: {str(e)}")
        return False


def test_service_status():
    """Servis durumunu test eder."""
    print_test_header("Service Status")

    try:
        from weather_service import get_service_status

        status = get_service_status()

        print(f"Service: {status.get('service')}")
        print(f"Status: {status.get('status')}")
        print(f"Cache TTL: {status['config'].get('cache_ttl_seconds')}s")

        results = [
            print_result(
                status.get("service") == "weather_service",
                "Service dogru"
            ),
            print_result(
                status.get("status") == "operational",
                "Status operational"
            ),
            print_result(
                status["config"].get("cache_ttl_seconds") == 900,
                "Cache TTL 900s"
            )
        ]

        return all(results)

    except Exception as e:
        print_result(False, f"Hata: {str(e)}")
        return False


def test_cache_operations():
    """Cache operasyonlarini test eder."""
    print_test_header("Cache Operations")

    try:
        from weather_service import (
            _save_to_cache,
            _get_from_cache,
            get_cache_stats,
            clear_cache
        )

        # Cache'e kaydet
        test_key = "test:41.0082:28.9784"
        test_data = {"location": "Istanbul", "temp": 15}

        _save_to_cache(test_key, test_data)
        print_result(True, "Cache'e kaydedildi")

        # Cache'ten oku
        cached = _get_from_cache(test_key)
        result1 = print_result(
            cached is not None,
            f"Cache'ten okundu: {cached is not None}"
        )

        # Cache istatistikleri
        stats = get_cache_stats()
        result2 = print_result(
            stats.get("total_entries", 0) > 0,
            f"Cache stat: {stats['total_entries']} entries"
        )

        # Cache temizle
        count = clear_cache()
        result3 = print_result(
            count > 0,
            f"Cache temizlendi: {count} entries"
        )

        return all([result1, result2, result3])

    except Exception as e:
        print_result(False, f"Hata: {str(e)}")
        return False


# =============================================================================
# API INTEGRATION TESTS (requires network)
# =============================================================================

def test_openmeteo_api_call():
    """OpenMeteo API cagrisini test eder (network gerekli)."""
    print_test_header("OpenMeteo API Call")

    try:
        import requests

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 41.0082,
            "longitude": 28.9784,
            "current": "temperature_2m,weather_code",
            "timezone": "auto"
        }

        print("API cagrisi yapiliyor...")
        response = requests.get(url, params=params, timeout=10)

        results = [
            print_result(
                response.status_code == 200,
                f"HTTP {response.status_code}"
            )
        ]

        if response.status_code == 200:
            data = response.json()
            has_current = "current" in data
            results.append(print_result(
                has_current,
                f"Response'ta 'current' var: {has_current}"
            ))

            if has_current:
                temp = data["current"].get("temperature_2m")
                print(f"   Istanbul sicakligi: {temp}°C")

        return all(results)

    except Exception as e:
        print_result(False, f"Hata: {str(e)}")
        return False


def test_current_weather_live():
    """Canli hava durumu cekme testi."""
    print_test_header("Current Weather (Live)")

    try:
        from weather_service import get_current_weather

        print("Istanbul icin hava durumu cekiliyor...")
        result = get_current_weather(41.0082, 28.9784, use_cache=False)

        results = [
            print_result(
                result.get("success"),
                "Basarili"
            )
        ]

        if result.get("success"):
            data = result.get("data", {})
            location = data.get("location", {})
            current = data.get("current", {})

            print(f"   Lokasyon: {location.get('lat')}, {location.get('lon')}")
            print(f"   Sicaklik: {current.get('temperature')}°C")
            print(f"   Durum: {current.get('weather_description')}")
            print(f"   Emoji: {current.get('weather_emoji')}")

            results.append(print_result(
                current.get("temperature") is not None,
                "Sicaklik var"
            ))
            results.append(print_result(
                current.get("weather_code") is not None,
                "Weather code var"
            ))

        return all(results)

    except Exception as e:
        print_result(False, f"Hata: {str(e)}")
        return False


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests(skip_live: bool = False):
    """Tum testleri calistirir.

    Args:
        skip_live: Canli API testlerini atla
    """
    print("\n")
    print("=" * 60)
    print("  WEATHER SERVICE TEST SUITE")
    print("=" * 60)

    test_results = []

    # Unit tests
    test_results.append(("Coordinate Validation", test_validate_coordinates()))
    test_results.append(("Hours Validation", test_validate_hours()))
    test_results.append(("Weather Code Parsing", test_parse_weather_code()))
    test_results.append(("Weather Emoji", test_get_weather_emoji()))
    test_results.append(("Cache Key Building", test_build_cache_key()))
    test_results.append(("Temperature Formatting", test_format_temperature()))
    test_results.append(("Weather Alerts", test_weather_alerts()))
    test_results.append(("Activity Suggestions", test_activity_suggestions()))

    # Service tests
    test_results.append(("Service Import", test_weather_service_import()))
    test_results.append(("Service Status", test_service_status()))
    test_results.append(("Cache Operations", test_cache_operations()))

    # Live API tests
    if not skip_live:
        test_results.append(("OpenMeteo API Call", test_openmeteo_api_call()))
        test_results.append(("Current Weather Live", test_current_weather_live()))
    else:
        print("\n" + "=" * 60)
        print("  LIVE API TESTS SKIPPED (use --live to enable)")
        print("=" * 60)

    # Summary
    print("\n")
    print("=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        icon = "[PASS]" if result else "[FAIL]"
        print(f"{icon} {test_name}")

    print("=" * 60)
    print(f"  TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Weather Service Test Suite")
    parser.add_argument("--skip-live", action="store_true",
                       help="Canli API testlerini atla")
    parser.add_argument("--live-only", action="store_true",
                       help="Sadece canli API testlerini calistir")

    args = parser.parse_args()

    if args.live_only:
        print("\n" + "=" * 60)
        print("  LIVE API TESTS ONLY")
        print("=" * 60)
        test_openmeteo_api_call()
        test_current_weather_live()
    else:
        success = run_all_tests(skip_live=args.skip_live)
        sys.exit(0 if success else 1)
