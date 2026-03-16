/* app.js — OpenTrip Frontend Application

Harita etkileşimi, API iletişimi, rota gösterimi ve POI arama.
*/

// ========== CONFIG ==========
const API_BASE = "/api";

// ========== STATE ==========
let selectedPoints = [];
let markers = [];
let routePolyline = null;
let routeGlowPolylines = [];  // Glow efektleri için ayrı takip
let poiMarkers = [];
let currentRouteData = null;
let alternativeRoutesCache = {};  // Alternatif rota verileri cache'i (BUG FIX 07.03.2026)
let currentNlpResult = null;

// ========== MAP INIT ==========
const map = L.map("map", {
    zoomControl: false,
}).setView([40.9903, 29.0291], 14); // Kadıköy merkez

// Custom zoom control (sağ üste)
L.control.zoom({ position: "topright" }).addTo(map);

// Tile Layer — OpenStreetMap Standard (Canlı, detaylı, dükkanlar görünür)
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
}).addTo(map);

// ========== DOM ELEMENTS ==========
const elPointCount = document.getElementById("pointCount");
const elPointsList = document.getElementById("pointsList");
const elBtnClearAll = document.getElementById("btnClearAll");
const elBtnCalculate = document.getElementById("btnCalculateRoute");
const elRouteInfo = document.getElementById("routeInfo");
const elStatDistance = document.getElementById("statDistance");
const elStatDuration = document.getElementById("statDuration");
const elStatStops = document.getElementById("statStops");
const elBtnGoogleMaps = document.getElementById("btnGoogleMaps");
const elRegionSelect = document.getElementById("regionSelect");
const elProvinceSelect = document.getElementById("provinceSelect");
const elDistrictSelect = document.getElementById("districtSelect");
const elLoadingOverlay = document.getElementById("loadingOverlay");
const elLoadingText = document.getElementById("loadingText");
const elBtnClearPois = document.getElementById("btnClearPois");
const elToastContainer = document.getElementById("toastContainer");
const elPlaceSearchInput = document.getElementById("placeSearchInput");
const elBtnSearchPlace = document.getElementById("btnSearchPlace");
const elSearchResults = document.getElementById("searchResults");
const elNlpInput = document.getElementById("nlpInput");
const elBtnNLP = document.getElementById("btnNLP");
const elNlpResults = document.getElementById("nlpResults");
const elNlpLoading = document.getElementById("nlpLoading");
const elBtnShowAlternatives = document.getElementById("btnShowAlternatives");
const elAlternativesPanel = document.getElementById("alternativesPanel");
const elAlternativesList = document.getElementById("alternativesList");
const elBtnSaveRoute = document.getElementById("btnSaveRoute");
const elSaveRouteModal = document.getElementById("saveRouteModal");
const elBtnCloseSaveModal = document.getElementById("btnCloseSaveModal");
const elBtnCancelSave = document.getElementById("btnCancelSave");
const elBtnConfirmSave = document.getElementById("btnConfirmSave");
const elSavedRoutesList = document.getElementById("savedRoutesList");
const elBtnRefreshRoutes = document.getElementById("btnRefreshRoutes");
const elBtnShowTimeline = document.getElementById("btnShowTimeline");
const elTimelinePanel = document.getElementById("timelinePanel");
const elBtnGenerateTimeline = document.getElementById("btnGenerateTimeline");
const elTimelineDisplay = document.getElementById("timelineDisplay");

// Saved Locations elements
const elSavedLocationsList = document.getElementById("savedLocationsList");
const elBtnToggleSavedLocations = document.getElementById("btnToggleSavedLocations");
const elBtnRefreshLocations = document.getElementById("btnRefreshLocations");
const elIconLocationVisible = document.getElementById("iconLocationVisible");

const elSaveLocationModal = document.getElementById("saveLocationModal");
const elBtnCloseLocationModal = document.getElementById("btnCloseLocationModal");
const elBtnCancelLocation = document.getElementById("btnCancelLocation");
const elBtnConfirmSaveLocation = document.getElementById("btnConfirmSaveLocation");
const elLocationName = document.getElementById("locationName");
const elLocationLat = document.getElementById("locationLat");
const elLocationLon = document.getElementById("locationLon");
const elLocationAddress = document.getElementById("locationAddress");
const locationIconBtns = document.querySelectorAll("#locationIconSelector .icon-btn");

let showSavedLocationsOnMap = true;
let customLocationMarkers = [];

// ========== CUSTOM MARKER ICON ==========
function createNumberedIcon(number) {
    return L.divIcon({
        className: "custom-marker-wrapper",
        html: `<div class="custom-marker"><span>${number}</span></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32],
    });
}

function createPoiIcon(emoji) {
    return L.divIcon({
        className: "poi-marker-wrapper",
        html: `<span class="poi-marker">${emoji}</span>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

// Helper: geçerli bir alan değeri mi? (undefined/null/''/'nan' ise geçersiz say)
function isValidField(v) {
    return v !== undefined && v !== null && String(v).trim() !== '' && String(v).toLowerCase() !== 'nan';
}

// ========== MAP CLICK HANDLER ==========
map.on("dblclick", function (e) {
    const { lat, lng } = e.latlng;
    addPoint(lat, lng);
});

function addPoint(lat, lng) {
    const index = selectedPoints.length;
    selectedPoints.push([lat, lng]);

    // Hava durumu widget'ını bu noktaya göre güncelle
    fetchWeatherWidget(lat, lng);

    // Marker ekle
    const marker = L.marker([lat, lng], {
        icon: createNumberedIcon(index + 1),
    }).addTo(map);

    // Sağ tıklama menüsü - Konumu Kaydet
    marker.on('contextmenu', function (e) {
        openSaveLocationModal(lat, lng, `Nokta ${index + 1}`);
    });

    marker.bindPopup(
        `<strong>Nokta ${index + 1}</strong><br>${lat.toFixed(5)}, ${lng.toFixed(5)}<br>
         <button class="btn btn-primary btn-sm" style="margin-top: 8px; width: 100%;"
            data-action-save-location
            data-lat="${lat}"
            data-lng="${lng}"
            data-label="Nokta ${index + 1}">
            📍 Konumu Kaydet
         </button>`
    );

    markers.push(marker);

    updatePointsList();
    updateButtons();

    showToast(`Nokta ${index + 1} eklendi`, "info");
}

function removePoint(index) {
    // Marker'ı kaldır
    map.removeLayer(markers[index]);
    markers.splice(index, 1);
    selectedPoints.splice(index, 1);

    // Marker numaralarını güncelle
    markers.forEach((m, i) => {
        m.setIcon(createNumberedIcon(i + 1));
        m.setPopupContent(
            `<strong>Nokta ${i + 1}</strong><br>${selectedPoints[i][0].toFixed(5)}, ${selectedPoints[i][1].toFixed(5)}`
        );
    });

    updatePointsList();
    updateButtons();
    clearRoute();

    // Son kalan noktanın hava durumunu göster, yoksa harita merkezi
    if (selectedPoints.length > 0) {
        const last = selectedPoints[selectedPoints.length - 1];
        fetchWeatherWidget(last[0], last[1]);
    } else {
        const center = map.getCenter();
        fetchWeatherWidget(center.lat, center.lng);
    }
}

function clearAllPoints() {
    markers.forEach((m) => map.removeLayer(m));
    markers = [];
    selectedPoints = [];
    updatePointsList();
    updateButtons();
    clearRoute();
    showToast("Tüm noktalar silindi", "info");

    // Noktalar temizlenince harita merkezine geri dön
    const center = map.getCenter();
    fetchWeatherWidget(center.lat, center.lng);
}

// ========== UI UPDATES ==========
// ========== DRAG & DROP VARIABLES ==========
let draggedIndex = null;

// ========== DRAG & DROP HANDLERS ==========
function handleDragStart(e, index) {
    draggedIndex = index;
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    setTimeout(() => e.target.style.opacity = '0.5', 0);
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    e.target.style.opacity = '1';
    document.querySelectorAll('.point-item').forEach(item => {
        item.classList.remove('drag-over');
    });
    draggedIndex = null;
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const targetItem = e.target.closest('.point-item');
    if (targetItem) {
        targetItem.classList.add('drag-over');
    }
}

function handleDragLeave(e) {
    const targetItem = e.target.closest('.point-item');
    if (targetItem) {
        targetItem.classList.remove('drag-over');
    }
}

function handleDrop(e, targetIndex) {
    e.preventDefault();
    const targetItem = e.target.closest('.point-item');
    if (targetItem) {
        targetItem.classList.remove('drag-over');
    }

    if (draggedIndex === null || draggedIndex === targetIndex) {
        return;
    }

    // Array'de yer değiştir
    const draggedPoint = selectedPoints.splice(draggedIndex, 1)[0];
    selectedPoints.splice(targetIndex, 0, draggedPoint);

    // Marker'ları da güncelle
    const draggedMarker = markers.splice(draggedIndex, 1)[0];
    markers.splice(targetIndex, 0, draggedMarker);

    // UI güncelle
    updatePointsList();

    // Eğer rota varsa, rota sırasını güncelle
    if (currentRouteData) {
        clearRoute();
        showToast('Nokta sırası değiştirildi. Rota için tekrar hesaplayın.', 'info');
    }
}

function updatePointsList() {
    elPointCount.textContent = selectedPoints.length;

    if (selectedPoints.length === 0) {
        elPointsList.innerHTML = `<div class="empty-state"><p>Haritaya tıklayarak nokta ekleyin</p></div>`;
        return;
    }

    let html = "";
    selectedPoints.forEach((p, i) => {
        html += `
            <div class="point-item" draggable="true"
                 ondragstart="handleDragStart(event, ${i})"
                 ondragend="handleDragEnd(event)"
                 ondragover="handleDragOver(event)"
                 ondragleave="handleDragLeave(event)"
                 ondrop="handleDrop(event, ${i})">
                <div class="drag-handle" title="Sıralamak için sürükle">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <circle cx="9" cy="6" r="1.5"/>
                        <circle cx="15" cy="6" r="1.5"/>
                        <circle cx="9" cy="12" r="1.5"/>
                        <circle cx="15" cy="12" r="1.5"/>
                        <circle cx="9" cy="18" r="1.5"/>
                        <circle cx="15" cy="18" r="1.5"/>
                    </svg>
                </div>
                <div class="point-label">
                    <span class="point-number">${i + 1}</span>
                    <span class="point-coords">${p[0].toFixed(4)}, ${p[1].toFixed(4)}</span>
                </div>
                <button class="btn-remove" data-action-remove-point data-index="${i}" title="Sil">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 6M6 6l12 12"/></svg>
                </button>
            </div>
        `;
    });
    elPointsList.innerHTML = html;
}

function updateButtons() {
    elBtnClearAll.disabled = selectedPoints.length === 0;
    elBtnCalculate.disabled = selectedPoints.length < 2;
    elBtnShowAlternatives.disabled = selectedPoints.length < 2;
    elBtnShowTimeline.disabled = selectedPoints.length < 2 || !currentRouteData;
}

// ========== ROUTE CALCULATION ==========
async function calculateRoute() {
    if (selectedPoints.length < 2) {
        showToast("En az 2 nokta seçmelisiniz!", "error");
        return;
    }

    showLoading("Rota hesaplanıyor...\nHarita verisi ilk kez indiriliyorsa biraz zaman alabilir.");

    const optimize = false; // TSP optimizasyonu devre dışı

    try {
        const response = await fetch(`${API_BASE}/get-route`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                points: selectedPoints,
                optimize: optimize,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Bilinmeyen hata");
        }

        currentRouteData = data;
        drawRoute(data);
        showRouteInfo(data);
        await fetchRouteSteps();
        updateButtons();  // Buton durumlarını güncelle
        showToast("Rota başarıyla hesaplandı! ✨", "success");

        // Hava durumu uyarılarını göster (arka planda, rotayı engelleme)
        checkRouteWeatherAndShowBanner(selectedPoints);

    } catch (error) {
        console.error("Rota hesaplama hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

function drawRoute(data) {
    clearRoute();

    if (!data.route_coords || data.route_coords.length === 0) return;

    // Rota çizgisini çiz — gradient efektli
    routePolyline = L.polyline(data.route_coords, {
        color: "#6c5ce7",
        weight: 5,
        opacity: 0.85,
        smoothFactor: 1,
        dashArray: null,
    }).addTo(map);

    // Rota çizgisi üstüne glow efekti
    const glow = L.polyline(data.route_coords, {
        color: "#a594f9",
        weight: 10,
        opacity: 0.2,
        smoothFactor: 1,
    }).addTo(map);
    routeGlowPolylines.push(glow);

    // Haritayı rotaya sığdır
    map.fitBounds(routePolyline.getBounds(), { padding: [60, 60] });
}

function clearRoute() {
    if (routePolyline) {
        map.removeLayer(routePolyline);
        routePolyline = null;
    }

    // Glow katmanlarını temizle (routeGlowPolylines takip listesiyle)
    routeGlowPolylines.forEach(layer => map.removeLayer(layer));
    routeGlowPolylines = [];

    elRouteInfo.style.display = "none";
    currentRouteData = null;
}

function showRouteInfo(data) {
    elRouteInfo.style.display = "block";
    elStatDistance.textContent = `${data.total_distance_km} km`;
    elStatDuration.textContent = `${data.estimated_walk_minutes} dk`;
    elStatStops.textContent = selectedPoints.length;

    if (data.google_maps_link) {
        elBtnGoogleMaps.href = data.google_maps_link;
        elBtnGoogleMaps.style.display = "flex";
    }
}

// ========== POI SEARCH ==========
async function searchPois(category) {
    // Yeni dropdown'lardan veri al
    const province = elProvinceSelect.value;
    const district = elDistrictSelect.value;
    
    // Eğer il seçilmemişse uyarı ver
    if (!province) {
        showToast('Lütfen önce bir il seçin', 'warning');
        return;
    }
    
    // İlçe seçilmişse ilçe, yoksa il kullan
    const place = district ? `${district}, ${province}, Turkey` : `${province}, Turkey`;

    showLoading(`"${category}" mekanları aranıyor...`);

    try {
        const response = await fetch(`${API_BASE}/search-pois`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ place, category }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "POI arama hatası");
        }

        clearPois();
        displayPois(data.pois, category);

        showToast(`${data.pois.length} adet "${category}" bulundu`, "success");

    } catch (error) {
        console.error("POI arama hatası:", error);
        showToast(`POI arama hatası: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

function displayPois(pois, category) {
    const emojiMap = {
        museum: "🏛️",
        cafe: "☕",
        park: "🌳",
        restaurant: "🍽️",
        mosque: "🕌",
        library: "📚",
        hotel: "🏨",
    };

    const categoryLabels = {
        museum: "Müze",
        cafe: "Kafe",
        park: "Park",
        restaurant: "Restoran",
        mosque: "Cami",
        library: "Kütüphane",
        hotel: "Otel",
    };

    const emoji = emojiMap[category] || "📍";
    const label = categoryLabels[category] || category;

    pois.forEach((poi) => {
        const marker = L.marker([poi.lat, poi.lon], {
            icon: createPoiIcon(emoji),
        }).addTo(map);

        // Zengin popup kartı oluştur
        const popupContent = buildPoiPopup(poi, emoji, label);
        marker.bindPopup(popupContent, {
            maxWidth: 280,
            minWidth: 220,
            className: "poi-popup",
        });

        poiMarkers.push(marker);
    });

    elBtnClearPois.style.display = "block";
}

function buildPoiPopup(poi, emoji, label) {
    let html = `<div class="poi-card">`;

    // Başlık
    html += `<div class="poi-card-header">`;
    html += `<span class="poi-card-emoji">${emoji}</span>`;
    html += `<div>`;
    html += `<h3 class="poi-card-title">${poi.name}</h3>`;
    html += `<span class="poi-card-category">${label}</span>`;
    html += `</div>`;
    html += `</div>`;

    // Açıklama
    if (poi.description) {
        html += `<p class="poi-card-desc">${poi.description}</p>`;
    }

    // Detaylar
    let hasDetails = false;
    html += `<div class="poi-card-details">`;

    if (isValidField(poi.opening_hours)) {
        html += `<div class="poi-detail"><span class="poi-detail-icon">🕐</span> ${poi.opening_hours}</div>`;
        hasDetails = true;
    }

    if (isValidField(poi.website)) {
        html += `<div class="poi-detail"><span class="poi-detail-icon">🌐</span> <a href="${poi.website}" target="_blank" rel="noopener">Web Sitesi</a></div>`;
        hasDetails = true;
    }

    if (poi.wikipedia_url) {
        html += `<div class="poi-detail"><span class="poi-detail-icon">📖</span> <a href="${poi.wikipedia_url}" target="_blank" rel="noopener">Wikipedia</a></div>`;
        hasDetails = true;
    }

    if (!hasDetails) {
        html += `<div class="poi-detail"><span class="poi-detail-icon">📍</span> ${poi.lat.toFixed(5)}, ${poi.lon.toFixed(5)}</div>`;
    }

    html += `</div>`;

    // Rotaya ekle butonu
    html += `<button class="poi-card-btn" data-action-add-point data-lat="${poi.lat}" data-lon="${poi.lon}">＋ Rotaya Ekle</button>`;

    html += `</div>`;
    return html;
}

function clearPois() {
    poiMarkers.forEach((m) => map.removeLayer(m));
    poiMarkers = [];
    elBtnClearPois.style.display = "none";

    // POI butonlarının active sınıfını kaldır
    document.querySelectorAll(".btn-poi").forEach((btn) => btn.classList.remove("active"));
}

// ========== LOADING ==========
function showLoading(text) {
    elLoadingText.textContent = text || "Yükleniyor...";
    elLoadingOverlay.style.display = "flex";
}

function hideLoading() {
    elLoadingOverlay.style.display = "none";
}

// ========== TOAST NOTIFICATIONS ==========
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    elToastContainer.appendChild(toast);

    // 3 saniye sonra kaldır
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(40px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ========== EVENT LISTENERS ==========
elBtnClearAll.addEventListener("click", clearAllPoints);
elBtnCalculate.addEventListener("click", calculateRoute);
elBtnClearPois.addEventListener("click", clearPois);
elBtnShowAlternatives.addEventListener("click", showAlternativeRoutes);
elBtnSaveRoute.addEventListener("click", openSaveRouteModal);
elBtnCloseSaveModal.addEventListener("click", closeSaveRouteModal);
elBtnCancelSave.addEventListener("click", closeSaveRouteModal);
elBtnConfirmSave.addEventListener("click", confirmSaveRoute);
elBtnRefreshRoutes.addEventListener("click", loadSavedRoutes);
elBtnShowTimeline.addEventListener("click", showTimelinePlanner);
elBtnGenerateTimeline.addEventListener("click", generateTimeline);
elBtnNLP.addEventListener("click", analyzeNaturalLanguageQuery);

// Saved Location event listeners
elBtnRefreshLocations.addEventListener("click", loadSavedLocations);
elBtnToggleSavedLocations.addEventListener("click", toggleSavedLocationsVisibility);
elBtnCloseLocationModal.addEventListener("click", closeSaveLocationModal);
elBtnCancelLocation.addEventListener("click", closeSaveLocationModal);
elBtnConfirmSaveLocation.addEventListener("click", confirmSaveLocation);

// Icon selector behavior
locationIconBtns.forEach(btn => {
    btn.addEventListener("click", function (e) {
        e.preventDefault();
        locationIconBtns.forEach(b => b.classList.remove("active"));
        this.classList.add("active");
    });
});

// POI butonları
document.querySelectorAll(".btn-poi").forEach((btn) => {
    btn.addEventListener("click", function () {
        const category = this.dataset.category;

        // Toggle active sınıfı
        document.querySelectorAll(".btn-poi").forEach((b) => b.classList.remove("active"));
        this.classList.add("active");

        searchPois(category);
    });
});

// İlk bildirim
showToast("Haritaya tıklayarak başlayın! 🗺️", "info");

// Kaydedilmiş rotaları ve yerleri yükle
loadSavedRoutes();
loadSavedLocations();

// Hava durumu widget'inı başlat
initWeatherWidget();

// ========== PLACE SEARCH (GEOCODING) ==========

// Debounce: yazmayı bitirdikten sonra öneri isteği at
// İyileştirme: Request cancellation + adaptive delay
let suggestDebounceTimer = null;
let suggestAbortController = null;
const SUGGEST_DELAY_MS = 400;
const SUGGEST_DELAY_MS_SHORT = 200;  // Kısa sorgular için daha hızlı

elPlaceSearchInput.addEventListener("input", function () {
    const query = elPlaceSearchInput.value.trim();

    if (query.length < 2) {
        elSearchResults.style.display = "none";
        clearTimeout(suggestDebounceTimer);
        if (suggestAbortController) {
            suggestAbortController.abort();  // Bekleyen isteği iptal et
        }
        return;
    }

    // Önceki isteği iptal et
    if (suggestAbortController) {
        suggestAbortController.abort();
    }

    // Yeni AbortController oluştur
    suggestAbortController = new AbortController();

    // Adaptive delay: kısa sorgular daha hızlı, uzun sorgular daha yavaş
    const delay = query.length < 4 ? SUGGEST_DELAY_MS_SHORT : SUGGEST_DELAY_MS;

    clearTimeout(suggestDebounceTimer);
    suggestDebounceTimer = setTimeout(
        () => fetchSuggestions(query, suggestAbortController.signal),
        delay
    );
});

// Enter tuşu ile tam arama
elPlaceSearchInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
        searchPlace();
    }
});

// Arama butonu
elBtnSearchPlace.addEventListener("click", searchPlace);
elNlpInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
        analyzeNaturalLanguageQuery();
    }
});

// Dışarı tıklanınca önerileri kapat
document.addEventListener("click", function (e) {
    if (!elPlaceSearchInput.contains(e.target) && !elSearchResults.contains(e.target)) {
        elSearchResults.style.display = "none";
    }
});

// ... (dosya devam ediyor; mevcut içerik korundu)
