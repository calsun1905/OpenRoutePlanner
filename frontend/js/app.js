/**
 * app.js — OpenTrip Frontend Application
 *
 * Harita etkileşimi, API iletişimi, rota gösterimi ve POI arama.
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

/**
 * Yazarken öneri listesi getirir (autocomplete)
 * İyileştirme: AbortController ile request cancellation
 */
async function fetchSuggestions(query, signal = null) {
    try {
        const options = signal ? { signal } : {};
        const response = await fetch(`${API_BASE}/geocode/suggest?q=${encodeURIComponent(query)}&limit=6`, options);
        const data = await response.json();

        if (data.status !== "success" || !data.suggestions || data.suggestions.length === 0) {
            elSearchResults.style.display = "none";
            return;
        }

        elSearchResults.style.display = "block";
        elSearchResults.innerHTML = data.suggestions.map((s) => `
            <div class="search-result-item search-suggestion-item" data-lat="${s.lat}" data-lon="${s.lon}">
                <div class="search-result-name">📍 ${escapeHtml(s.display_name)}</div>
                <div class="search-result-coords">${s.lat.toFixed(5)}, ${s.lon.toFixed(5)}</div>
            </div>
        `).join("");

        // Öneri tıklama
        elSearchResults.querySelectorAll(".search-suggestion-item").forEach((el) => {
            el.addEventListener("click", () => {
                const lat = parseFloat(el.dataset.lat);
                const lon = parseFloat(el.dataset.lon);
                const nameEl = el.querySelector(".search-result-name");
                const name = nameEl ? nameEl.textContent.replace(/^📍\s*/, "").trim() : "";
                selectSearchResult(lat, lon, name);
            });
        });
    } catch (err) {
        // AbortError ise sessizce geç (kullanıcı hala yazıyor)
        if (err.name === 'AbortError') {
            return;
        }
        console.error("Öneri hatası:", err);
        elSearchResults.style.display = "none";
    }
}

/**
 * Yer ismi ile arama yapar (Geocoding API)
 */
async function searchPlace() {
    const query = elPlaceSearchInput.value.trim();

    if (!query) {
        showToast("Lütfen bir yer ismi girin", "error");
        return;
    }

    if (query.length < 2) {
        showToast("Arama terimi çok kısa", "error");
        return;
    }

    showLoading("Yer aranıyor...");

    try {
        const response = await fetch(`${API_BASE}/geocode`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ place: query }),
        });

        const data = await response.json();

        if (!response.ok || data.status === "error") {
            throw new Error(data.message || "Yer bulunamadı");
        }

        displaySearchResult(data);
        showToast(`Bulundu: ${data.display_name}`, "success");

    } catch (error) {
        console.error("Geocoding hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
        elSearchResults.style.display = "none";
    } finally {
        hideLoading();
    }
}

/**
 * Arama sonucunu gösterir
 */
function displaySearchResult(data) {
    elSearchResults.style.display = "block";
    const displayName = data.display_name || "Bilinmeyen konum";
    const shortName = displayName.split(",")[0].trim();

    elSearchResults.innerHTML = `
        <div class="search-result-item">
            <div class="search-result-name">📍 ${escapeHtml(displayName)}</div>
            <div class="search-result-coords">${data.lat.toFixed(5)}, ${data.lon.toFixed(5)}</div>
            <button
                class="btn btn-ghost btn-sm"
                data-action="save-location"
                style="margin-top:5px; width: 100%; border: 1px solid rgba(255,255,255,0.1);"
            >
                💾 Bu Konumu Kaydet
            </button>
        </div>
    `;

    const resultItem = elSearchResults.querySelector(".search-result-item");
    const saveButton = elSearchResults.querySelector("[data-action='save-location']");

    resultItem.addEventListener("click", () => {
        selectSearchResult(data.lat, data.lon, displayName);
    });

    saveButton.addEventListener("click", (event) => {
        event.stopPropagation();
        openSaveLocationModal(data.lat, data.lon, shortName);
    });
}

/**
 * Arama sonucuna tıklanınca haritaya ekler
 */
function selectSearchResult(lat, lon, name) {
    // Haritayı o noktaya odakla
    map.setView([lat, lon], 16);

    // Noktayı ekle
    addPoint(lat, lon);

    // Input ve sonuçları temizle
    elPlaceSearchInput.value = "";
    elSearchResults.style.display = "none";

    showToast(`"${name}" rotaya eklendi`, "success");
}

/**
 * HTML kaçış karakterleri
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}


// ========== AI ASSISTANT (NLP) ==========

async function geocodePlaceName(placeName) {
    const response = await fetch(`${API_BASE}/geocode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ place: placeName }),
    });

    const data = await response.json();
    if (!response.ok || data.status === "error") {
        throw new Error(data.message || `"${placeName}" bulunamadı`);
    }

    return data;
}

function setNlpLoading(isLoading) {
    elBtnNLP.disabled = isLoading;
    elNlpLoading.style.display = isLoading ? "flex" : "none";
}

function buildNlpSummary(result) {
    if (result.type === "route") {
        return `${escapeHtml(result.origin || "?" )} → ${escapeHtml(result.destination || "?")}`;
    }
    if (result.type === "multi") {
        return (result.locations || []).map(escapeHtml).join(" → ");
    }
    if (result.type === "poi") {
        return `${escapeHtml(result.location || "Bilinmeyen konum")} için mekan araması`;
    }
    if (result.type === "single") {
        return `${escapeHtml(result.destination || "Bilinmeyen hedef")} hedef olarak algılandı`;
    }
    return escapeHtml(result.error || "Sorgu anlaşılamadı");
}

function renderNlpResults(result) {
    currentNlpResult = result;

    const confidence = typeof result.confidence === "number"
        ? `%${Math.round(result.confidence * 100)}`
        : "—";

    const detectedPlaces = Array.isArray(result.detected_places) ? result.detected_places : [];
    const placesHtml = detectedPlaces.length > 0
        ? `
            <div class="nlp-result-places">
                ${detectedPlaces.map((item) => `
                    <span class="nlp-place-tag">
                        📍 ${escapeHtml(item.place)}
                    </span>
                `).join("")}
            </div>
        `
        : "";

    const actions = [];
    if (result.type === "route" || result.type === "multi") {
        actions.push(`<button class="nlp-action-btn primary" data-action="apply-nlp">Haritaya Uygula</button>`);
    } else if ((result.type === "single" && result.destination) || (result.type === "poi" && result.location)) {
        actions.push(`<button class="nlp-action-btn primary" data-action="focus-nlp">Haritada Göster</button>`);
    }

    elNlpResults.innerHTML = `
        <div class="nlp-result-item">
            <div class="nlp-result-type">${escapeHtml(result.type || "unknown")}</div>
            <div class="nlp-result-content">${buildNlpSummary(result)}</div>
            <div class="nlp-result-confidence">Güven: ${confidence}</div>
            ${placesHtml}
            ${actions.length > 0 ? `<div class="nlp-actions">${actions.join("")}</div>` : ""}
        </div>
    `;
    elNlpResults.style.display = "block";

    elNlpResults.querySelectorAll("[data-action='apply-nlp']").forEach((button) => {
        button.addEventListener("click", applyNlpResult);
    });
    elNlpResults.querySelectorAll("[data-action='focus-nlp']").forEach((button) => {
        button.addEventListener("click", focusNlpLocation);
    });
}

async function analyzeNaturalLanguageQuery() {
    const query = elNlpInput.value.trim();

    if (!query) {
        showToast("Lütfen bir sorgu girin", "error");
        return;
    }

    setNlpLoading(true);
    elNlpResults.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/nlp/parse`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query, debug: true }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "NLP analizi başarısız");
        }

        renderNlpResults(data);
        showToast(`AI analiz tamamlandı (${data.engine || "nlp"})`, "success");
    } catch (error) {
        console.error("NLP analizi hatası:", error);
        elNlpResults.innerHTML = `<div class="nlp-error">${escapeHtml(error.message)}</div>`;
        elNlpResults.style.display = "block";
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        setNlpLoading(false);
    }
}

async function applyNlpResult() {
    if (!currentNlpResult) {
        return;
    }

    const targetPlaces = [];
    if (currentNlpResult.type === "route") {
        if (currentNlpResult.origin) targetPlaces.push(currentNlpResult.origin);
        if (currentNlpResult.destination) targetPlaces.push(currentNlpResult.destination);
    } else if (currentNlpResult.type === "multi") {
        targetPlaces.push(...(currentNlpResult.locations || []));
    }

    if (targetPlaces.length < 2) {
        showToast("Uygulanacak yeterli konum bulunamadı", "error");
        return;
    }

    showLoading("AI sonucu haritaya uygulanıyor...");

    try {
        clearAllPoints();

        for (const placeName of targetPlaces) {
            const place = await geocodePlaceName(placeName);
            addPoint(place.lat, place.lon);
        }

        await calculateRoute();
    } catch (error) {
        console.error("NLP uygulama hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

async function focusNlpLocation() {
    if (!currentNlpResult) {
        return;
    }

    const placeName = currentNlpResult.location || currentNlpResult.destination;
    if (!placeName) {
        showToast("Gösterilecek konum bulunamadı", "error");
        return;
    }

    showLoading("Konum bulunuyor...");

    try {
        const place = await geocodePlaceName(placeName);
        map.setView([place.lat, place.lon], 16);
        addPoint(place.lat, place.lon);
        showToast(`"${placeName}" haritada gösterildi`, "success");
    } catch (error) {
        console.error("NLP konum gösterme hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}


// ========== ALTERNATIVE ROUTES ==========

/**
 * Alternatif rotaları gösterir
 */
async function showAlternativeRoutes() {
    if (selectedPoints.length < 2) {
        showToast("En az 2 nokta seçmelisiniz!", "error");
        return;
    }

    showLoading("Alternatif rotalar hesaplanıyor...");

    const optimize = false; // TSP optimizasyonu devre dışı

    try {
        const response = await fetch(`${API_BASE}/get-alternative-routes`, {
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

        displayAlternativeRoutes(data.alternatives);
        showToast(`${data.alternatives.length} alternatif rota bulundu! 🔀`, "success");

    } catch (error) {
        console.error("Alternatif rota hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * Alternatif rotaları listeler
 */
function displayAlternativeRoutes(alternatives) {
    elAlternativesPanel.style.display = "block";
    
    // Cache'i doldur (BUG FIX: 07.03.2026 - alternativeRoutesCache init)
    alternativeRoutesCache = {};
    alternatives.forEach(alt => {
        alternativeRoutesCache[alt.type] = {
            distance_km: alt.distance_km,
            duration_minutes: alt.duration_minutes,
            route_coords: alt.route_coords,
            google_maps_link: alt.google_maps_link
        };
    });

    let html = "";

    alternatives.forEach((alt, index) => {
        const isActive = index === 0 ? "active" : "";

        html += `
            <div class="alternative-card ${isActive}" data-route-type="${alt.type}">
                <div class="alternative-header">
                    <span class="alternative-icon">${alt.icon}</span>
                    <div class="alternative-info">
                        <h3 class="alternative-name">${alt.name}</h3>
                        <p class="alternative-desc">${alt.description}</p>
                    </div>
                </div>
                <div class="alternative-stats">
                    <div class="alternative-stat">
                        <span class="stat-icon">📏</span>
                        <span class="stat-text">${alt.distance_km} km</span>
                    </div>
                    <div class="alternative-stat">
                        <span class="stat-icon">⏱️</span>
                        <span class="stat-text">${alt.duration_minutes} dk</span>
                    </div>
                </div>
                <button class="btn-select-route"
                    data-action-select-alt
                    data-type="${escapeHtml(alt.type)}"
                    data-coords='${JSON.stringify(alt.route_coords)}'>
                    Bu Rotayı Seç
                </button>
            </div>
        `;
    });

    elAlternativesList.innerHTML = html;

    // Panele scroll
    elAlternativesPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/**
 * Seçilen alternatif rotayı haritada gösterir
 */
function selectAlternativeRoute(routeType, routeCoords) {
    clearRoute();

    // Rota renklerini belirle - basit sistem
    const routeColors = {
        route_1: "#6c5ce7",     // Mor
        route_2: "#00cec9",     // Turkuaz
        route_3: "#feca57"      // Sarı
    };

    // Eski tip compatibility (shortest/fastest/balanced)
    if (routeType === "shortest") routeType = "route_1";
    else if (routeType === "fastest") routeType = "route_2";
    else if (routeType === "balanced") routeType = "route_3";

    const color = routeColors[routeType] || "#6c5ce7";

    // Rotayı çiz
    routePolyline = L.polyline(routeCoords, {
        color: color,
        weight: 5,
        opacity: 0.85,
        smoothFactor: 1,
    }).addTo(map);

    // Glow efekti - tracking listesine ekle
    const glow = L.polyline(routeCoords, {
        color: color,
        weight: 10,
        opacity: 0.2,
        smoothFactor: 1,
    }).addTo(map);
    routeGlowPolylines.push(glow);

    // Haritayı rotaya sığdır
    map.fitBounds(routePolyline.getBounds(), { padding: [60, 60] });

    // Active sınıfını güncelle
    document.querySelectorAll(".alternative-card").forEach(card => {
        card.classList.remove("active");
    });
    document.querySelector(`[data-route-type="${routeType}"]`).classList.add("active");

    // currentRouteData'yı seçilen alternatif rota ile güncelle
    if (alternativeRoutesCache[routeType]) {
        const altData = alternativeRoutesCache[routeType];
        currentRouteData = {
            route_coords: routeCoords,
            total_distance_km: altData.distance_km,
            estimated_walk_minutes: altData.duration_minutes,
            route_type: routeType,
            google_maps_link: altData.google_maps_link
        };
    }

    if (currentRouteData) {
        showRouteInfo(currentRouteData);
    }

    // Butonları güncelle
    updateButtons();

    const routeNames = {
        route_1: "Rota 1",
        route_2: "Rota 2",
        route_3: "Rota 3"
    };

    showToast(`${routeNames[routeType]} seçildi! 🎯`, "success");
}


// ========== SAVE ROUTE ==========

/**
 * Rota kaydetme modalını açar
 */
function openSaveRouteModal() {
    if (!currentRouteData) {
        showToast("Önce bir rota hesaplayın!", "error");
        return;
    }

    elSaveRouteModal.style.display = "flex";
    document.getElementById("routeName").focus();
}

/**
 * Rota kaydetme modalını kapatır
 */
function closeSaveRouteModal() {
    elSaveRouteModal.style.display = "none";
    // Formu temizle
    document.getElementById("routeName").value = "";
    document.getElementById("routeDescription").value = "";
    document.getElementById("routeTags").value = "";
}

/**
 * Rotayı kaydeder
 */
async function confirmSaveRoute() {
    const name = document.getElementById("routeName").value.trim();
    const description = document.getElementById("routeDescription").value.trim();
    const tagsInput = document.getElementById("routeTags").value.trim();

    if (!name) {
        showToast("Rota adı gerekli!", "error");
        return;
    }

    if (!currentRouteData) {
        showToast("Kaydedilecek rota bulunamadı!", "error");
        return;
    }

    // Etiketleri ayır
    const tags = tagsInput ? tagsInput.split(",").map(t => t.trim()).filter(t => t) : [];

    showLoading("Rota kaydediliyor...");

    try {
        const response = await fetch(`${API_BASE}/routes/save`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: name,
                description: description,
                points: selectedPoints,
                route_coords: currentRouteData.route_coords,
                distance_km: currentRouteData.total_distance_km,
                duration_minutes: currentRouteData.estimated_walk_minutes,
                route_type: currentRouteData.route_type || "route_1",
                tags: tags
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Kaydetme hatası");
        }

        closeSaveRouteModal();
        loadSavedRoutes(); // Listeyi yenile
        showToast(`"${name}" rotası kaydedildi! 💾`, "success");

    } catch (error) {
        console.error("Rota kaydetme hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * Kaydedilmiş rotaları yükler
 */
async function loadSavedRoutes() {
    try {
        const response = await fetch(`${API_BASE}/routes?sort_by=created_at&limit=10`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Rotalar yüklenemedi");
        }

        displaySavedRoutes(data.routes);

    } catch (error) {
        console.error("Rota yükleme hatası:", error);
        elSavedRoutesList.innerHTML = `<div class="empty-state"><p>Rotalar yüklenemedi</p></div>`;
    }
}

/**
 * Kaydedilmiş rotaları listeler
 */
function displaySavedRoutes(routes) {
    if (!routes || routes.length === 0) {
        elSavedRoutesList.innerHTML = `<div class="empty-state"><p>Henüz kaydedilmiş rota yok</p></div>`;
        return;
    }

    let html = "";

    routes.forEach(route => {
        const date = new Date(route.created_at).toLocaleDateString("tr-TR", {
            day: "numeric",
            month: "short"
        });

        const favoriteIcon = route.favorite ? "⭐" : "☆";

        html += `
            <div class="saved-route-card">
                <div class="saved-route-header">
                    <h3 class="saved-route-name">${escapeHtml(route.name)}</h3>
                    <button class="btn-favorite" data-action-toggle-route-fav data-id="${escapeHtml(route.id)}" title="Favori">
                        ${favoriteIcon}
                    </button>
                </div>
                ${route.description ? `<p class="saved-route-desc">${escapeHtml(route.description)}</p>` : ""}
                <div class="saved-route-stats">
                    <span>📏 ${route.distance_km} km</span>
                    <span>⏱️ ${route.duration_minutes} dk</span>
                    <span>📅 ${date}</span>
                </div>
                ${route.tags && route.tags.length > 0 ? `
                    <div class="saved-route-tags">
                        ${route.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
                    </div>
                ` : ""}
                <div class="saved-route-actions">
                    <button class="btn-load-route" data-action-load-route data-id="${escapeHtml(route.id)}">
                        📍 Yükle
                    </button>
                    <button class="btn-delete-route" data-action-delete-route data-id="${escapeHtml(route.id)}" title="Sil">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    });

    elSavedRoutesList.innerHTML = html;
}

/**
 * Kaydedilmiş rotayı yükler
 */
async function loadRoute(routeId) {
    showLoading("Rota yükleniyor...");

    try {
        const response = await fetch(`${API_BASE}/routes/${routeId}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Rota yüklenemedi");
        }

        const route = data.route;

        // Mevcut noktaları temizle
        clearAllPoints();

        // Rotanın noktalarını ekle
        route.points.forEach(([lat, lon]) => {
            addPoint(lat, lon);
        });

        // Rotayı çiz
        currentRouteData = {
            route_coords: route.route_coords,
            total_distance_km: route.distance_km,
            estimated_walk_minutes: route.duration_minutes,
            route_type: route.route_type
        };

        drawRoute(currentRouteData);
        showRouteInfo(currentRouteData);
        updateButtons();  // Buton durumlarını güncelle

        showToast(`"${route.name}" rotası yüklendi! 📍`, "success");

    } catch (error) {
        console.error("Rota yükleme hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * Rotayı favorilere ekler/çıkarır
 */
async function toggleRouteFavorite(routeId) {
    try {
        const response = await fetch(`${API_BASE}/routes/${routeId}/favorite`, {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Favori işlemi başarısız");
        }

        loadSavedRoutes(); // Listeyi yenile

        const message = data.is_favorite ? "Favorilere eklendi ⭐" : "Favorilerden çıkarıldı";
        showToast(message, "success");

    } catch (error) {
        console.error("Favori işlemi hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    }
}

/**
 * Rotayı siler
 */
async function deleteRoute(routeId) {
    if (!confirm("Bu rotayı silmek istediğinizden emin misiniz?")) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/routes/${routeId}`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Silme işlemi başarısız");
        }

        loadSavedRoutes(); // Listeyi yenile
        showToast("Rota silindi 🗑️", "success");

    } catch (error) {
        console.error("Rota silme hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    }
}


// ========== TIME PLANNING ==========

/**
 * Zaman planlama panelini gösterir
 */
function showTimelinePlanner() {
    if (!currentRouteData || selectedPoints.length < 2) {
        showToast("Önce bir rota hesaplayın!", "error");
        return;
    }

    elTimelinePanel.style.display = "block";
    elTimelinePanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/**
 * Zaman çizelgesi oluşturur
 */
async function generateTimeline() {
    if (!currentRouteData) {
        showToast("Önce bir rota hesaplayın!", "error");
        return;
    }

    const startTime = document.getElementById("startTime").value;
    const visitDuration = parseInt(document.getElementById("visitDuration").value);

    if (!startTime) {
        showToast("Başlangıç saati seçin!", "error");
        return;
    }

    showLoading("Zaman çizelgesi oluşturuluyor...");

    try {
        // Noktalar arası mesafeleri hesapla
        const segmentDistances = calculateSegmentDistances();

        // Nokta bilgilerini hazırla
        const points = selectedPoints.map((point, index) => ({
            name: `Nokta ${index + 1}`,
            lat: point[0],
            lon: point[1]
        }));

        const response = await fetch(`${API_BASE}/timeline/create`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                points: points,
                segment_distances: segmentDistances,
                start_time: startTime,
                visit_duration: visitDuration,
                transport_mode: "walking",
                include_weather: true
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Zaman çizelgesi oluşturulamadı");
        }

        displayTimeline(data);
        showToast("Zaman çizelgesi oluşturuldu! ⏰", "success");

    } catch (error) {
        console.error("Timeline hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * Segment mesafelerini hesaplar (basitleştirilmiş)
 */
function calculateSegmentDistances() {
    if (!currentRouteData || !currentRouteData.total_distance_km) {
        return [];
    }

    // Basit yaklaşım: toplam mesafeyi nokta sayısına böl
    const numSegments = selectedPoints.length - 1;
    const avgDistance = currentRouteData.total_distance_km / numSegments;

    return Array(numSegments).fill(avgDistance);
}

/**
 * Zaman çizelgesini görüntüler
 */
function displayTimeline(timeline) {
    elTimelineDisplay.style.display = "block";

    const totalHours = Math.floor(timeline.total_duration_minutes / 60);
    const totalMins = timeline.total_duration_minutes % 60;

    let html = `
        <div class="timeline-summary">
            <div class="timeline-stat">
                <span class="timeline-stat-label">Başlangıç</span>
                <span class="timeline-stat-value">🕐 ${timeline.start_time}</span>
            </div>
            <div class="timeline-stat">
                <span class="timeline-stat-label">Bitiş</span>
                <span class="timeline-stat-value">🕐 ${timeline.end_time}</span>
            </div>
            <div class="timeline-stat">
                <span class="timeline-stat-label">Toplam Süre</span>
                <span class="timeline-stat-value">⏱️ ${totalHours}s ${totalMins}dk</span>
            </div>
        </div>
        
        <div class="timeline-items">
    `;

    timeline.schedule.forEach((item, index) => {
        const isLast = index === timeline.schedule.length - 1;

        html += `
            <div class="timeline-item">
                <div class="timeline-marker">${index + 1}</div>
                <div class="timeline-content">
                    <div class="timeline-point-name">${escapeHtml(item.point_name)}</div>
                    <div class="timeline-times">
                        <span class="timeline-time">
                            <span class="timeline-time-label">Varış:</span>
                            <span class="timeline-time-value">${item.arrival_time}</span>
                        </span>
                        <span class="timeline-time">
                            <span class="timeline-time-label">Ayrılış:</span>
                            <span class="timeline-time-value">${item.departure_time}</span>
                        </span>
                    </div>
                    <div class="timeline-duration">
                        ⏱️ ${item.visit_duration_minutes} dakika kalış
                    </div>
                    ${item.weather ? `
                    <div class="timeline-weather">
                        <span class="tl-weather-emoji">${item.weather.weather_emoji || '🌡️'}</span>
                        <span class="tl-weather-temp">${item.weather.temperature != null ? Math.round(item.weather.temperature) + '°C' : ''}</span>
                        <span class="tl-weather-desc">${escapeHtml(item.weather.weather_tr || item.weather.weather_description || '')}</span>
                    </div>
                    ${item.weather.advice && item.weather.advice.items && item.weather.advice.items.length > 0 ? `
                    <div class="timeline-advice timeline-advice-${item.weather.advice.alert_level}">
                        ${item.weather.advice.items.map(a =>
                            `<span class="tl-advice-item"><span class="tl-advice-emoji">${a.emoji}</span><span class="tl-advice-text">${escapeHtml(a.text)}</span></span>`
                        ).join('')}
                    </div>` : ''}
                    ` : ''}
                    ${!isLast ? `
                        <div class="timeline-travel">
                            🚶‍♂️ ${item.next_travel_time_minutes} dakika yürüyüş
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    });

    html += `</div>`;

    elTimelineDisplay.innerHTML = html;
}

// ========== SAVED LOCATIONS (KAYITLI YERLER) ==========

// İkon haritası — Kayıtlı yerler için emoji eşlemesi
const locationEmojiMap = {
    marker: "📍",
    home: "🏠",
    work: "💼",
    school: "🎓",
    gym: "🏋️",
    market: "🛒",
    star: "⭐",
    coffee: "☕",
    restaurant: "🍽️",
    heart: "❤️",
    hospital: "🏥",
    park: "🌳",
    museum: "🏛️",
    plane: "✈️",
    car: "🚗",
    bike: "🚲",
    beach: "🏖️",
    mountain: "⛰️",
    bank: "🏦",
    gas: "⛽",
    pharmacy: "💊"
};

/**
 * Konum kaydetme modalını açar
 */
window.openSaveLocationModal = function (lat, lon, defaultName = "") {
    elLocationLat.value = lat;
    elLocationLon.value = lon;
    elLocationName.value = defaultName;
    elLocationAddress.value = ""; // Reverse geocoding ile de doldurulabilir (şimdilik boş kalsın)

    // Default marker'ı sıfırla
    locationIconBtns.forEach(b => b.classList.remove("active"));
    const defaultBtn = document.querySelector('#locationIconSelector [data-icon="marker"]');
    if (defaultBtn) defaultBtn.classList.add("active");

    elSaveLocationModal.style.display = "flex";
    elLocationName.focus();
};

function closeSaveLocationModal() {
    elSaveLocationModal.style.display = "none";
    elLocationName.value = "";
}

/**
 * Konumu sunucuya kaydeder
 */
async function confirmSaveLocation() {
    const name = elLocationName.value.trim();
    const lat = parseFloat(elLocationLat.value);
    const lon = parseFloat(elLocationLon.value);
    const address = elLocationAddress.value.trim();

    const activeIconBtn = document.querySelector('#locationIconSelector .icon-btn.active');
    const iconType = activeIconBtn ? activeIconBtn.dataset.icon : "marker";

    if (!name) {
        showToast("Konum adı gerekli!", "error");
        return;
    }

    if (isNaN(lat) || isNaN(lon)) {
        showToast("Geçersiz koordinatlar!", "error");
        return;
    }

    showLoading("Konum kaydediliyor...");

    try {
        const response = await fetch(`${API_BASE}/locations`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: name,
                lat: lat,
                lon: lon,
                icon_type: iconType,
                address: address
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Kaydetme hatası");
        }

        closeSaveLocationModal();
        loadSavedLocations(); // Listeyi yenile
        showToast(`"${name}" konumu kaydedildi! 📍`, "success");

    } catch (error) {
        console.error("Konum kaydetme hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * Sunucudan kayıtlı konumları getir ve ekrana çiz
 */
async function loadSavedLocations() {
    try {
        const response = await fetch(`${API_BASE}/locations?limit=20&sort_by=favorite`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Konumlar yüklenemedi");
        }

        displaySavedLocationsSidebar(data.locations);

        if (showSavedLocationsOnMap) {
            drawSavedLocationsOnMap(data.locations);
        }

    } catch (error) {
        console.error("Konum yükleme hatası:", error);
        elSavedLocationsList.innerHTML = `<div class="empty-state"><p>Yer imleri yüklenemedi</p></div>`;
    }
}

function displaySavedLocationsSidebar(locations) {
    if (!locations || locations.length === 0) {
        elSavedLocationsList.innerHTML = `<div class="empty-state"><p>Henüz kayıtlı yeriniz yok</p></div>`;
        return;
    }

    let html = "";
    locations.forEach(loc => {
        const emoji = locationEmojiMap[loc.icon_type] || "📍";
        const favoriteIcon = loc.favorite ? "⭐" : "☆";

        html += `
            <div class="saved-location-card"
                 data-zoom-location
                 data-lat="${loc.lat}"
                 data-lon="${loc.lon}"
                 data-name="${encodeURIComponent(loc.name)}">
                <div class="saved-location-icon">${emoji}</div>
                <div class="saved-location-info">
                    <h3 class="saved-location-name">${escapeHtml(loc.name)}</h3>
                    <p class="saved-location-address">Kullanım: ${loc.times_used || 0}</p>
                </div>
                <div class="saved-location-actions" data-stop-propagation>
                    <button class="ic-btn ic-btn-favorite" data-action-toggle-loc-fav data-id="${escapeHtml(loc.id)}" title="Favori">
                        ${favoriteIcon}
                    </button>
                    <button class="ic-btn ic-btn-route" data-action-add-point data-lat="${loc.lat}" data-lon="${loc.lon}" title="Rotaya Ekle">
                        ＋
                    </button>
                    <button class="ic-btn ic-btn-delete" data-action-delete-loc data-id="${escapeHtml(loc.id)}" title="Sil">
                        ✖
                    </button>
                </div>
            </div>
        `;
    });

    elSavedLocationsList.innerHTML = html;
}

window.zoomToLocation = function (lat, lon, name) {
    map.setView([lat, lon], 16);
};

/**
 * Kayıtlı konumun favori durumunu değiştirir
 */
async function toggleLocationFavorite(locationId) {
    try {
        const response = await fetch(`${API_BASE}/locations/${locationId}/favorite`, {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Favori işlemi başarısız");
        }

        loadSavedLocations();
        showToast(data.is_favorite ? "Favorilere eklendi ⭐" : "Favorilerden çıkarıldı", "success");

    } catch (error) {
        console.error("Favori işlemi hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    }
}

async function deleteSavedLocation(locationId) {
    if (!confirm("Bu konumu silmek istediğinizden emin misiniz?")) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/locations/${locationId}`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Silme işlemi başarısız");
        }

        loadSavedLocations(); // Backendi ve haritayı yenile
        showToast("Konum silindi 🗑️", "success");

    } catch (error) {
        console.error("Konum silme hatası:", error);
        showToast(`Hata: ${error.message}`, "error");
    }
}

/**
 * Haritadaki markerları çizer
 */
function drawSavedLocationsOnMap(locations) {
    clearSavedLocationMarkers();

    locations.forEach(loc => {
        const emoji = locationEmojiMap[loc.icon_type] || "📍";

        const icon = L.divIcon({
            className: "custom-marker-wrapper",
            html: `<div class="location-marker">${emoji}</div>`,
            iconSize: [36, 36],
            iconAnchor: [18, 18],
            popupAnchor: [0, -18],
        });

        const marker = L.marker([loc.lat, loc.lon], { icon: icon }).addTo(map);
        marker.bindPopup(`<strong>${escapeHtml(loc.name)}</strong><br>
                          <button class="btn btn-primary btn-sm" style="margin-top:8px;" data-action-add-point data-lat="${loc.lat}" data-lon="${loc.lon}">Rotaya Ekle</button>`);

        customLocationMarkers.push(marker);
    });
}

function clearSavedLocationMarkers() {
    customLocationMarkers.forEach(m => map.removeLayer(m));
    customLocationMarkers = [];
}

function toggleSavedLocationsVisibility() {
    showSavedLocationsOnMap = !showSavedLocationsOnMap;

    if (showSavedLocationsOnMap) {
        // İkonu aktif göz yap
        elIconLocationVisible.innerHTML = `
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
        `;
        elIconLocationVisible.style.stroke = "currentColor";
        loadSavedLocations(); // Yeniden yükleyip çizsin
    } else {
        // İkonu kapalı göz yap
        elIconLocationVisible.innerHTML = `
            <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
        `;
        elIconLocationVisible.style.stroke = "var(--text-muted)";
        clearSavedLocationMarkers();
    }
}

// ========== EVENT DELEGATION - XSS Güvenlik Düzeltmeleri ==========
// Tüm inline onclick handlers yerine tek bir event listener kullanılır
// Bu, XSS saldırılarını önler ve daha iyi performans sağlar

document.addEventListener("click", function(e) {
    // Find closest element with data attribute (handles nested clicks)
    const target = e.target.closest("[data-action-remove-point]");
    if (target) {
        const index = parseInt(target.dataset.index);
        removePoint(index);
        return;
    }

    // Add point from POI or saved locations
    if (e.target.matches("[data-action-add-point]")) {
        const lat = parseFloat(e.target.dataset.lat);
        const lon = parseFloat(e.target.dataset.lon);
        addPoint(lat, lon);
        return;
    }

    // Save location from marker popup
    if (e.target.matches("[data-action-save-location]")) {
        const lat = parseFloat(e.target.dataset.lat);
        const lng = parseFloat(e.target.dataset.lng);
        const label = e.target.dataset.label;
        openSaveLocationModal(lat, lng, label);
        return;
    }

    // Toggle route favorite
    if (e.target.matches("[data-action-toggle-route-fav]")) {
        const id = e.target.dataset.id;
        toggleRouteFavorite(id);
        return;
    }

    // Load saved route
    if (e.target.matches("[data-action-load-route]")) {
        const id = e.target.dataset.id;
        loadRoute(id);
        return;
    }

    // Delete saved route
    if (e.target.matches("[data-action-delete-route]")) {
        const id = e.target.dataset.id;
        deleteRoute(id);
        return;
    }

    // Select alternative route
    if (e.target.matches("[data-action-select-alt]")) {
        const type = e.target.dataset.type;
        const coords = JSON.parse(e.target.dataset.coords);
        selectAlternativeRoute(type, coords);
        return;
    }

    // Zoom to saved location (card click)
    const locationCard = e.target.closest("[data-zoom-location]");
    if (locationCard) {
        const lat = parseFloat(locationCard.dataset.lat);
        const lon = parseFloat(locationCard.dataset.lon);
        const name = decodeURIComponent(locationCard.dataset.name);
        zoomToLocation(lat, lon, name);
        return;
    }

    // Toggle location favorite
    if (e.target.matches("[data-action-toggle-loc-fav]")) {
        const id = e.target.dataset.id;
        toggleLocationFavorite(id);
        // Stop propagation is handled by data-stop-propagation on parent
        return;
    }

    // Delete saved location
    if (e.target.matches("[data-action-delete-loc]")) {
        const id = e.target.dataset.id;
        deleteSavedLocation(id);
        return;
    }
});

// Handle stopPropagation for action buttons inside cards
document.addEventListener("click", function(e) {
    if (e.target.closest("[data-stop-propagation]")) {
        e.stopPropagation();
    }
});

// ========== WEATHER WIDGET ==========

let _weatherWidgetTimer = null;
let _weatherHideTimer = null;

async function fetchWeatherWidget(lat, lon) {
    const el = document.getElementById("weatherWidget");
    if (!el) return;

    try {
        const resp = await fetch(`${API_BASE}/weather?lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;

        const cur = data.data.current;
        document.getElementById("weatherWidgetEmoji").textContent = cur.weather_emoji || "🌍";
        document.getElementById("weatherWidgetTemp").textContent = `${Math.round(cur.temperature)}°C`;
        document.getElementById("weatherWidgetDesc").textContent = cur.weather_tr || cur.weather_description || "—";

        // Göster ve 5 sn sonra otomatik kaybet
        el.style.display = "block";
        el.classList.remove("auto-hide");
        if (_weatherHideTimer) clearTimeout(_weatherHideTimer);
        _weatherHideTimer = setTimeout(() => {
            el.classList.add("auto-hide");
        }, 5000);
    } catch (e) {
        // fail silently — widget gösterilmez
    }
}

function initWeatherWidget() {
    // Sayfa açıldığında harita merkezinden başla
    const center = map.getCenter();
    fetchWeatherWidget(center.lat, center.lng);
    // Nokta eklenmediği sürece harita hareketiyle güncelleme yapma
}

// ========== WEATHER BANNER ==========

let _weatherBannerTimer = null;
let _weatherUseCustomStartTime = false;

function formatLocalDateISO(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
}

// Kullanıcı startTime alanını bilinçli değiştirdiyse forecast modunu aç
(function initWeatherStartTimePreference() {
    const startTimeInput = document.getElementById("startTime");
    if (!startTimeInput) return;

    const defaultValue = (startTimeInput.value || "09:00").trim();
    startTimeInput.dataset.defaultValue = defaultValue;

    const updatePreference = () => {
        const value = (startTimeInput.value || "").trim();
        _weatherUseCustomStartTime = /^\d{2}:\d{2}$/.test(value) && value !== defaultValue;
    };

    startTimeInput.addEventListener("input", updatePreference);
    startTimeInput.addEventListener("change", updatePreference);
})();

async function checkRouteWeatherAndShowBanner(points) {
    if (!points || points.length < 1) return;
    try {
        const pointsPayload = points.map((p, i) => ({
            lat: p[0], lon: p[1], name: `Nokta ${i + 1}`
        }));

        // Kullanıcı özel saat seçtiyse, route-weather için forecast modunu aç
        const startTimeInput = document.getElementById("startTime");
        const startTimeValue = (startTimeInput?.value || "").trim();

        let hasTime = _weatherUseCustomStartTime && /^\d{2}:\d{2}$/.test(startTimeValue);

        // Geçmiş saat seçildiyse (bugün için), anlık moda düş
        if (hasTime) {
            const now = new Date();
            const [hh, mm] = startTimeValue.split(":").map(Number);
            const selected = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hh, mm, 0, 0);
            if (selected <= now) {
                hasTime = false;
            }
        }

        const payload = {
            points: pointsPayload,
            transport_mode: "walking"
        };

        if (hasTime) {
            const today = formatLocalDateISO(new Date());
            payload.start_time = `${today}T${startTimeValue}:00`;
            payload.segment_distances = calculateSegmentDistances();
        }

        const resp = await fetch(`${API_BASE}/weather/check-route`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;

        const routeWeather = data.data.route_weather || [];
        const criticalAdvice = data.data.critical_advice || null;
        showWeatherBanner(routeWeather, criticalAdvice);
    } catch (e) {
        // sessiz hata – banner olmadan devam
    }
}

function showWeatherBanner(routeWeather, criticalAdvice = null) {
    // Tüm noktalardan tavsiye topla, tekrar edenleri filtrele
    const seenTypes = new Set();
    const allItems = [];
    let topLevel = "info";

    const levelOrder = { danger: 3, warning: 2, info: 1 };

    routeWeather.forEach(rw => {
        const advice = rw.advice;
        if (!advice || !advice.items) return;
        if (levelOrder[advice.alert_level] > levelOrder[topLevel]) {
            topLevel = advice.alert_level;
        }
        advice.items.forEach(item => {
            if (!seenTypes.has(item.type)) {
                seenTypes.add(item.type);
                allItems.push({ ...item, point: rw.point });
            }
        });
    });

    if (allItems.length === 0) {
        hideWeatherBanner();
        return;
    }

    const banner = document.getElementById("weatherBanner");
    if (!banner) return;

    const iconMap = { info: "ℹ️", warning: "⚠️", danger: "🚨" };
    const titleMap = { info: "Hava Durumu Bilgisi", warning: "Hava Durumu Uyarısı", danger: "Tehlikeli Hava Koşulları" };

    let html = `
        <div class="weather-banner-header">
            <span class="weather-banner-icon">${iconMap[topLevel]}</span>
            <span class="weather-banner-title">${titleMap[topLevel]}</span>
            <button class="weather-banner-close" onclick="hideWeatherBanner()">✕</button>
        </div>
    `;

    if (criticalAdvice) {
        html += `
        <div class="weather-banner-critical">
            <span class="wbc-icon">🕒</span>
            <span class="wbc-text">${escapeHtml(criticalAdvice)}</span>
        </div>`;
    }

    html += `<div class="weather-banner-items">`;
    allItems.forEach(item => {
        html += `<div class="weather-banner-item">
            <span class="wbi-emoji">${item.emoji}</span>
            <span class="wbi-text">${escapeHtml(item.text)}</span>
        </div>`;
    });
    html += `</div>`;

    banner.innerHTML = html;
    banner.className = `weather-banner weather-banner-${topLevel} visible`;

    // 12 saniye sonra otomatik kapat
    if (_weatherBannerTimer) clearTimeout(_weatherBannerTimer);
    _weatherBannerTimer = setTimeout(hideWeatherBanner, 12000);
}

function hideWeatherBanner() {
    const banner = document.getElementById("weatherBanner");
    if (banner) banner.classList.remove("visible");
}


// ========== TÜRKİYE VERİSİ YÖNETİMİ ==========
let turkiyeData = null;

// Türkiye verisini yükle
async function loadTurkiyeData() {
    try {
        const response = await fetch('data/turkiye-data.json');
        turkiyeData = await response.json();
        initializeRegionDropdown();
    } catch (error) {
        console.error('Türkiye verisi yüklenemedi:', error);
        showToast('Bölge verileri yüklenemedi', 'error');
    }
}

// Bölge dropdown'ını doldur
function initializeRegionDropdown() {
    if (!turkiyeData) return;
    
    elRegionSelect.innerHTML = '<option value="">Bölge Seçin</option>';
    Object.keys(turkiyeData).forEach(region => {
        const option = document.createElement('option');
        option.value = region;
        option.textContent = region;
        elRegionSelect.appendChild(option);
    });
}

// Bölge seçildiğinde illeri doldur
elRegionSelect.addEventListener('change', function() {
    const selectedRegion = this.value;
    
    if (!selectedRegion) {
        elProvinceSelect.disabled = true;
        elProvinceSelect.innerHTML = '<option value="">Önce Bölge Seçin</option>';
        elDistrictSelect.disabled = true;
        elDistrictSelect.innerHTML = '<option value="">Önce İl Seçin</option>';
        return;
    }
    
    const provinces = turkiyeData[selectedRegion];
    elProvinceSelect.innerHTML = '<option value="">İl Seçin</option>';
    
    Object.keys(provinces).forEach(province => {
        const option = document.createElement('option');
        option.value = province;
        option.textContent = province;
        elProvinceSelect.appendChild(option);
    });
    
    elProvinceSelect.disabled = false;
    elDistrictSelect.disabled = true;
    elDistrictSelect.innerHTML = '<option value="">Önce İl Seçin</option>';
});

// İl seçildiğinde ilçeleri doldur
elProvinceSelect.addEventListener('change', function() {
    const selectedRegion = elRegionSelect.value;
    const selectedProvince = this.value;
    
    if (!selectedProvince) {
        elDistrictSelect.disabled = true;
        elDistrictSelect.innerHTML = '<option value="">Önce İl Seçin</option>';
        return;
    }
    
    const districts = turkiyeData[selectedRegion][selectedProvince];
    elDistrictSelect.innerHTML = '<option value="">İlçe Seçin (Opsiyonel)</option>';
    
    districts.forEach(district => {
        const option = document.createElement('option');
        option.value = district;
        option.textContent = district;
        elDistrictSelect.appendChild(option);
    });
    
    elDistrictSelect.disabled = false;
});

// İlçe seçildiğinde haritayı oraya odakla
elDistrictSelect.addEventListener('change', async function() {
    const selectedProvince = elProvinceSelect.value;
    const selectedDistrict = this.value;
    
    if (selectedDistrict) {
        // Geocoding ile konumu bul
        const query = `${selectedDistrict}, ${selectedProvince}, Turkey`;
        try {
            const data = await geocodePlaceName(query);
            if (data && data.length > 0) {
                const { lat, lon } = data[0];
                map.setView([lat, lon], 14);
                showToast(`${selectedDistrict}, ${selectedProvince} konumuna odaklandı`, 'success');
            }
        } catch (error) {
            console.error('Konum bulunamadı:', error);
        }
    }
});

// Sayfa yüklendiğinde Türkiye verisini yükle
loadTurkiyeData();
