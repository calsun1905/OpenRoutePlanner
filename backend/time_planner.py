"""
time_planner.py - Zaman Bazlı Rota Planlama

Rotalar için zaman çizelgesi oluşturur.
Başlangıç saati, ziyaret süreleri ve varış/ayrılış zamanlarını hesaplar.
"""

import sys
import io
# UTF-8 encoding için stdout ayarla (Windows terminal desteği)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from datetime import datetime, timedelta
from typing import List, Dict, Optional


def calculate_travel_time(distance_km: float, transport_mode: str = "walking") -> int:
    """
    Mesafeye ve ulaşım moduna göre seyahat süresini hesaplar.
    
    Args:
        distance_km: Mesafe (km)
        transport_mode: Ulaşım modu (walking, cycling, driving)
    
    Returns:
        int: Seyahat süresi (dakika)
    """
    # Ortalama hızlar (km/saat)
    speeds = {
        "walking": 5.0,
        "cycling": 15.0,
        "driving": 30.0
    }
    
    speed = speeds.get(transport_mode, 5.0)
    travel_hours = distance_km / speed
    travel_minutes = int(travel_hours * 60)
    
    return travel_minutes


def create_timeline(
    points: List[Dict],
    segment_distances: List[float],
    start_time: str = "09:00",
    visit_duration: int = 30,
    transport_mode: str = "walking",
    custom_durations: Dict[int, int] = None,
    include_weather: bool = False
) -> Dict:
    """
    Rota için zaman çizelgesi oluşturur.
    
    Args:
        points: Nokta listesi [{"name": "...", "lat": ..., "lon": ...}, ...]
        segment_distances: Noktalar arası mesafeler (km) [1.2, 0.8, ...]
        start_time: Başlangıç saati (HH:MM formatında)
        visit_duration: Varsayılan ziyaret süresi (dakika)
        transport_mode: Ulaşım modu
        custom_durations: Özel ziyaret süreleri {point_index: duration_minutes}
        include_weather: True ise her noktaya varış saatindeki hava durumu eklenir
    
    Returns:
        dict: Zaman çizelgesi
        {
            "start_time": "09:00",
            "end_time": "14:30",
            "total_duration_minutes": 330,
            "total_travel_time_minutes": 90,
            "total_visit_time_minutes": 240,
            "weather_summary": {...},   # include_weather=True ise
            "schedule": [
                {
                    "point_index": 0,
                    "point_name": "Kadıköy",
                    "arrival_time": "09:00",
                    "departure_time": "09:30",
                    "visit_duration_minutes": 30,
                    "next_travel_time_minutes": 15,
                    "weather": {...}    # include_weather=True ise
                },
                ...
            ]
        }
    """
    if not points:
        return {
            "error": "En az bir nokta gerekli"
        }
    
    # Başlangıç zamanını parse et
    try:
        current_time = datetime.strptime(start_time, "%H:%M")
    except ValueError:
        return {
            "error": "Geçersiz saat formatı. HH:MM kullanın (örn: 09:00)"
        }
    
    # Hava durumu modülünü lazy import et (circular import ve opsiyonel bağımlılık)
    _get_weather_at_time = None
    _get_weather_advice = None
    if include_weather:
        try:
            from weather_service import get_weather_at_time as _gwat
            from weather_utils import get_weather_advice as _gwa
            _get_weather_at_time = _gwat
            _get_weather_advice = _gwa
        except ImportError:
            include_weather = False
    
    schedule = []
    total_travel_time = 0
    total_visit_time = 0
    
    custom_durations = custom_durations or {}
    
    for i, point in enumerate(points):
        # Bu noktada kalma süresi
        duration = custom_durations.get(i, visit_duration)
        
        # Varış zamanı
        arrival_time = current_time.strftime("%H:%M")
        
        # Ayrılış zamanı
        departure_time = (current_time + timedelta(minutes=duration)).strftime("%H:%M")
        
        # Bir sonraki noktaya seyahat süresi
        next_travel_time = 0
        if i < len(segment_distances):
            next_travel_time = calculate_travel_time(
                segment_distances[i],
                transport_mode
            )
            total_travel_time += next_travel_time
        
        total_visit_time += duration
        
        entry = {
            "point_index": i,
            "point_name": point.get("name", f"Nokta {i + 1}"),
            "arrival_time": arrival_time,
            "departure_time": departure_time,
            "visit_duration_minutes": duration,
            "next_travel_time_minutes": next_travel_time,
            "coordinates": [point.get("lat"), point.get("lon")]
        }
        
        # Hava durumu bilgisi ekle
        if include_weather and _get_weather_at_time:
            lat = point.get("lat")
            lon = point.get("lon")
            if lat is not None and lon is not None:
                try:
                    w = _get_weather_at_time(lat, lon, arrival_time)
                    if w:
                        advice = {}
                        if _get_weather_advice:
                            try:
                                advice = _get_weather_advice(w)
                            except Exception:
                                pass
                        entry["weather"] = {
                            "temperature": w.get("temperature"),
                            "weather_emoji": w.get("weather_emoji", "🌤️"),
                            "weather_tr": w.get("weather_tr", ""),
                            "weather_description": w.get("weather_description", ""),
                            "precipitation_probability": w.get("precipitation_probability"),
                            "wind_speed": w.get("wind_speed"),
                            "advice": advice
                        }
                except Exception:
                    entry["weather"] = None
        
        schedule.append(entry)
        
        # Bir sonraki noktaya geçiş
        current_time += timedelta(minutes=duration + next_travel_time)
    
    # Bitiş zamanı (son noktadan ayrılış)
    end_time = current_time.strftime("%H:%M")
    
    # Toplam süre
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = current_time
    total_duration = int((end_dt - start_dt).total_seconds() / 60)
    
    result = {
        "start_time": start_time,
        "end_time": end_time,
        "total_duration_minutes": total_duration,
        "total_travel_time_minutes": total_travel_time,
        "total_visit_time_minutes": total_visit_time,
        "transport_mode": transport_mode,
        "schedule": schedule
    }
    
    # Genel rota hava özeti
    if include_weather:
        result["weather_summary"] = generate_route_weather_summary(schedule)
    
    return result


def generate_route_weather_summary(schedule: List[Dict]) -> Dict:
    """
    Tüm timeline noktalarından genel rota hava özeti çıkarır.
    
    Returns:
        dict: {
            "alert_level": "none" | "low" | "medium" | "high",
            "summary_text": "Bu rotada yağmur riski yüksek...",
            "emoji": "⚠️",
            "max_temp": 28.0,
            "min_temp": 14.0,
            "max_precip_prob": 70,
            "max_wind": 35.0
        }
    """
    weather_entries = [
        entry["weather"]
        for entry in schedule
        if entry.get("weather")
    ]
    
    if not weather_entries:
        return {
            "alert_level": "none",
            "summary_text": "Hava durumu bilgisi alınamadı.",
            "emoji": "❓"
        }
    
    temps = [w["temperature"] for w in weather_entries if w.get("temperature") is not None]
    precip_probs = [w["precipitation_probability"] for w in weather_entries if w.get("precipitation_probability") is not None]
    winds = [w["wind_speed"] for w in weather_entries if w.get("wind_speed") is not None]
    alert_levels = [w.get("advice", {}).get("alert_level", "none") for w in weather_entries]
    
    max_precip = max(precip_probs) if precip_probs else 0
    max_wind = max(winds) if winds else 0
    max_temp = max(temps) if temps else None
    min_temp = min(temps) if temps else None
    
    # En yüksek alert seviyesini belirle
    level_order = {"none": 0, "low": 1, "medium": 2, "high": 3}
    overall_level = max(alert_levels, key=lambda x: level_order.get(x, 0))
    
    # Özet metin ve emoji üret
    messages = []
    if max_precip >= 70:
        messages.append(f"Yağmur riski yüksek (%{int(max_precip)})")
    elif max_precip >= 40:
        messages.append(f"Hafif yağmur ihtimali (%{int(max_precip)})")
    
    if max_wind >= 40:
        messages.append(f"Kuvvetli rüzgar ({int(max_wind)} km/s)")
    elif max_wind >= 25:
        messages.append(f"Orta rüzgar ({int(max_wind)} km/s)")
    
    if max_temp is not None and max_temp >= 35:
        messages.append(f"Öğle sıcağına dikkat ({int(max_temp)}°C)")
    
    if not messages and min_temp is not None:
        messages.append(f"Genel hava iyi ({int(min_temp)}-{int(max_temp)}°C)")
    
    emoji_map = {"none": "✅", "low": "🌤️", "medium": "⚠️", "high": "🚨"}
    
    return {
        "alert_level": overall_level,
        "summary_text": " · ".join(messages) if messages else "Hava koşulları uygun.",
        "emoji": emoji_map.get(overall_level, "🌤️"),
        "max_temp": max_temp,
        "min_temp": min_temp,
        "max_precip_prob": int(max_precip) if max_precip else 0,
        "max_wind": max_wind
    }


def format_duration(minutes: int) -> str:
    """
    Dakikayı okunabilir formata çevirir.
    
    Args:
        minutes: Dakika
    
    Returns:
        str: Formatlanmış süre (örn: "2s 30dk")
    """
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        return f"{hours}s {mins}dk"
    return f"{mins}dk"


def check_time_conflicts(
    schedule: List[Dict],
    opening_hours: Dict[int, Dict] = None
) -> List[Dict]:
    """
    Zaman çizelgesinde çakışmaları kontrol eder.
    
    Args:
        schedule: Zaman çizelgesi
        opening_hours: Açılış saatleri {point_index: {"open": "09:00", "close": "18:00"}}
    
    Returns:
        list[dict]: Uyarılar
        [
            {
                "point_index": 2,
                "point_name": "Müze",
                "warning": "Bu saat kapalı olabilir",
                "arrival_time": "20:00",
                "opening_hours": "09:00-18:00"
            }
        ]
    """
    warnings = []
    opening_hours = opening_hours or {}
    
    for item in schedule:
        point_idx = item["point_index"]
        
        if point_idx in opening_hours:
            hours = opening_hours[point_idx]
            arrival = datetime.strptime(item["arrival_time"], "%H:%M")
            open_time = datetime.strptime(hours["open"], "%H:%M")
            close_time = datetime.strptime(hours["close"], "%H:%M")
            
            if arrival < open_time or arrival > close_time:
                warnings.append({
                    "point_index": point_idx,
                    "point_name": item["point_name"],
                    "warning": "Bu saat kapalı olabilir",
                    "arrival_time": item["arrival_time"],
                    "opening_hours": f"{hours['open']}-{hours['close']}"
                })
    
    return warnings


def optimize_schedule(
    schedule: List[Dict],
    max_duration_minutes: int = None,
    preferred_end_time: str = None
) -> Dict:
    """
    Zaman çizelgesini optimize eder.
    
    Args:
        schedule: Mevcut zaman çizelgesi
        max_duration_minutes: Maksimum toplam süre
        preferred_end_time: Tercih edilen bitiş saati (HH:MM)
    
    Returns:
        dict: Optimizasyon önerileri
    """
    suggestions = []
    
    if not schedule:
        return {"suggestions": []}
    
    total_duration = sum(
        item["visit_duration_minutes"] + item["next_travel_time_minutes"]
        for item in schedule
    )
    
    # Maksimum süre kontrolü
    if max_duration_minutes and total_duration > max_duration_minutes:
        excess = total_duration - max_duration_minutes
        suggestions.append({
            "type": "duration_exceeded",
            "message": f"Toplam süre {format_duration(excess)} fazla",
            "suggestion": "Ziyaret sürelerini azaltın veya bazı noktaları çıkarın"
        })
    
    # Bitiş saati kontrolü
    if preferred_end_time:
        last_item = schedule[-1]
        actual_end = datetime.strptime(last_item["departure_time"], "%H:%M")
        preferred_end = datetime.strptime(preferred_end_time, "%H:%M")
        
        if actual_end > preferred_end:
            diff = int((actual_end - preferred_end).total_seconds() / 60)
            suggestions.append({
                "type": "late_finish",
                "message": f"Bitiş saati {format_duration(diff)} geç",
                "suggestion": "Daha erken başlayın veya ziyaret sürelerini kısaltın"
            })
    
    # Çok uzun ziyaret süreleri
    for item in schedule:
        if item["visit_duration_minutes"] > 120:
            suggestions.append({
                "type": "long_visit",
                "point_name": item["point_name"],
                "message": f"{item['point_name']} için {format_duration(item['visit_duration_minutes'])} çok uzun olabilir"
            })
    
    return {
        "suggestions": suggestions,
        "total_duration_minutes": total_duration
    }
