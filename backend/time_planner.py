"""
time_planner.py - Zaman Bazlı Rota Planlama

Rotalar için zaman çizelgesi oluşturur.
Başlangıç saati, ziyaret süreleri ve varış/ayrılış zamanlarını hesaplar.
"""

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
    custom_durations: Dict[int, int] = None
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
    
    Returns:
        dict: Zaman çizelgesi
        {
            "start_time": "09:00",
            "end_time": "14:30",
            "total_duration_minutes": 330,
            "total_travel_time_minutes": 90,
            "total_visit_time_minutes": 240,
            "schedule": [
                {
                    "point_index": 0,
                    "point_name": "Kadıköy",
                    "arrival_time": "09:00",
                    "departure_time": "09:30",
                    "visit_duration_minutes": 30,
                    "next_travel_time_minutes": 15
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
        
        schedule.append({
            "point_index": i,
            "point_name": point.get("name", f"Nokta {i + 1}"),
            "arrival_time": arrival_time,
            "departure_time": departure_time,
            "visit_duration_minutes": duration,
            "next_travel_time_minutes": next_travel_time,
            "coordinates": [point.get("lat"), point.get("lon")]
        })
        
        # Bir sonraki noktaya geçiş
        current_time += timedelta(minutes=duration + next_travel_time)
    
    # Bitiş zamanı (son noktadan ayrılış)
    end_time = current_time.strftime("%H:%M")
    
    # Toplam süre
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = current_time
    total_duration = int((end_dt - start_dt).total_seconds() / 60)
    
    return {
        "start_time": start_time,
        "end_time": end_time,
        "total_duration_minutes": total_duration,
        "total_travel_time_minutes": total_travel_time,
        "total_visit_time_minutes": total_visit_time,
        "transport_mode": transport_mode,
        "schedule": schedule
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
