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
const elPlaceSelect = document.getElementById("placeSelect");
const elLoadingOverlay = document.getElementById("loadingOverlay");
const elLoadingText = document.getElementById("loadingText");
const elBtnClearPois = document.getElementById("btnClearPois");
const elToastContainer = document.getElementById("toastContainer");
const elPlaceSearchInput = document.getElementById("placeSearchInput");
const elBtnSearchPlace = document.getElementById("btnSearchPlace");
const elSearchResults = document.getElementById("searchResults");
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

// ========== MAP CLICK HANDLER ==========
map.on("click", function (e) {
    const { lat, lng } = e.latlng;
    addPoint(lat, lng);
});

function addPoint(lat, lng) {
    const index = selectedPoints.length;
    selectedPoints.push([lat, lng]);

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
            onclick="openSaveLocationModal(${lat}, ${lng}, 'Nokta ${index + 1}')">
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
}

function clearAllPoints() {
    markers.forEach((m) => map.removeLayer(m));
    markers = [];
    selectedPoints = [];
    updatePointsList();
    updateButtons();
    clearRoute();
    showToast("Tüm noktalar silindi", "info");
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
                <button class="btn-remove" onclick="removePoint(${i})" title="Sil">
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

    const optimize = document.getElementById("chkOptimize").checked;

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
    L.polyline(data.route_coords, {
        color: "#a594f9",
        weight: 10,
        opacity: 0.2,
        smoothFactor: 1,
    }).addTo(map);

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
    const place = elPlaceSelect.value;

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

    if (poi.opening_hours) {
        html += `<div class="poi-detail"><span class="poi-detail-icon">🕐</span> ${poi.opening_hours}</div>`;
        hasDetails = true;
    }

    if (poi.website) {
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
    html += `<button class="poi-card-btn" onclick="addPoint(${poi.lat}, ${poi.lon})">＋ Rotaya Ekle</button>`;

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

// ========== PLACE SEARCH (GEOCODING) ==========

// Enter tuşu ile arama
elPlaceSearchInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
        searchPlace();
    }
});

// Arama butonu
elBtnSearchPlace.addEventListener("click", searchPlace);

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

    elSearchResults.innerHTML = `
        <div class="search-result-item" onclick="selectSearchResult(${data.lat}, ${data.lon}, '${escapeHtml(data.display_name)}')">
            <div class="search-result-name">📍 ${escapeHtml(data.display_name)}</div>
            <div class="search-result-coords">${data.lat.toFixed(5)}, ${data.lon.toFixed(5)}</div>
            <button class="btn btn-ghost btn-sm" style="margin-top:5px; width: 100%; border: 1px solid rgba(255,255,255,0.1);" 
                onclick="event.stopPropagation(); openSaveLocationModal(${data.lat}, ${data.lon}, '${escapeHtml(data.display_name).split(',')[0]}')">
                💾 Bu Konumu Kaydet
            </button>
        </div>
    `;
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

    const optimize = document.getElementById("chkOptimize").checked;

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
                <button class="btn-select-route" onclick="selectAlternativeRoute('${alt.type}', ${JSON.stringify(alt.route_coords).replace(/"/g, '&quot;')})">
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

    // Rota renklerini belirle
    const routeColors = {
        shortest: "#6c5ce7",    // Mor
        fastest: "#00cec9",     // Turkuaz
        balanced: "#feca57"     // Sarı
    };

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
            route_type: routeType
        };
    }

    // Butonları güncelle
    updateButtons();

    const routeNames = {
        shortest: "En Kısa Rota",
        fastest: "En Hızlı Rota",
        balanced: "Dengeli Rota"
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
                route_type: currentRouteData.route_type || "shortest",
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
                    <button class="btn-favorite" onclick="toggleRouteFavorite('${route.id}')" title="Favori">
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
                    <button class="btn-load-route" onclick="loadRoute('${route.id}')">
                        📍 Yükle
                    </button>
                    <button class="btn-delete-route" onclick="deleteRoute('${route.id}')" title="Sil">
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
                transport_mode: "walking"
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
            <div class="saved-location-card" onclick="zoomToLocation(${loc.lat}, ${loc.lon}, '${escapeHtml(loc.name)}')">
                <div class="saved-location-icon">${emoji}</div>
                <div class="saved-location-info">
                    <h3 class="saved-location-name">${escapeHtml(loc.name)}</h3>
                    <p class="saved-location-address">Kullanım: ${loc.times_used || 0}</p>
                </div>
                <div class="saved-location-actions" onclick="event.stopPropagation()">
                    <button class="ic-btn ic-btn-favorite" onclick="toggleLocationFavorite('${loc.id}')" title="Favori">
                        ${favoriteIcon}
                    </button>
                    <button class="ic-btn ic-btn-route" onclick="addPoint(${loc.lat}, ${loc.lon})" title="Rotaya Ekle">
                        ＋
                    </button>
                    <button class="ic-btn ic-btn-delete" onclick="deleteSavedLocation('${loc.id}')" title="Sil">
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
                          <button class="btn btn-primary btn-sm" style="margin-top:8px;" onclick="addPoint(${loc.lat}, ${loc.lon})">Rotaya Ekle</button>`);

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
