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
const elBtnCompareRoutes = document.getElementById("btnCompareRoutes");
const elMultimodalPanel = document.getElementById("multimodalPanel");
const elMultimodalResults = document.getElementById("multimodalResults");

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

    marker.bindPopup(
        `<strong>Nokta ${index + 1}</strong><br>${lat.toFixed(5)}, ${lng.toFixed(5)}`
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
function updatePointsList() {
    elPointCount.textContent = selectedPoints.length;

    if (selectedPoints.length === 0) {
        elPointsList.innerHTML = `<div class="empty-state"><p>Haritaya tıklayarak nokta ekleyin</p></div>`;
        return;
    }

    let html = "";
    selectedPoints.forEach((p, i) => {
        html += `
            <div class="point-item">
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
    if (elBtnCompareRoutes) {
        elBtnCompareRoutes.disabled = selectedPoints.length < 2;
    }
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

// Kaydedilmiş rotaları yükle
loadSavedRoutes();


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

    // Glow efekti
    L.polyline(routeCoords, {
        color: color,
        weight: 10,
        opacity: 0.2,
        smoothFactor: 1,
    }).addTo(map);

    // Haritayı rotaya sığdır
    map.fitBounds(routePolyline.getBounds(), { padding: [60, 60] });

    // Active sınıfını güncelle
    document.querySelectorAll(".alternative-card").forEach(card => {
        card.classList.remove("active");
    });
    document.querySelector(`[data-route-type="${routeType}"]`).classList.add("active");

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


// ========== TRANSIT (TOPLU ULASIM) ==========

// Transit state
let transitStopMarkers = null;  // MarkerClusterGroup
let transitEnabled = false;
let _transitDebounceTimer = null;

// Transit DOM elements
const elChkShowStops = document.getElementById("chkShowStops");
const elTransitPanel = document.getElementById("transitPanel");
const elTransitSearchInput = document.getElementById("transitSearchInput");
const elBtnSearchTransit = document.getElementById("btnSearchTransit");
const elTransitSearchResults = document.getElementById("transitSearchResults");
const elNearbyStopsList = document.getElementById("nearbyStopsList");

// Transit stop icon
function createStopIcon() {
    return L.divIcon({
        className: "transit-stop-icon",
        html: '<div class="stop-marker">&#x1F68F;</div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -12],
    });
}

// Toggle transit stops
if (elChkShowStops) {
    elChkShowStops.addEventListener("change", function () {
        transitEnabled = this.checked;
        elTransitPanel.style.display = transitEnabled ? "block" : "none";

        if (transitEnabled) {
            // Initialize cluster group
            if (!transitStopMarkers) {
                transitStopMarkers = L.markerClusterGroup({
                    maxClusterRadius: 50,
                    disableClusteringAtZoom: 16,
                    spiderfyOnMaxZoom: true,
                    showCoverageOnHover: false,
                    iconCreateFunction: function (cluster) {
                        const count = cluster.getChildCount();
                        let size = "small";
                        if (count > 50) size = "large";
                        else if (count > 20) size = "medium";
                        return L.divIcon({
                            html: `<div class="transit-cluster transit-cluster-${size}"><span>${count}</span></div>`,
                            className: "transit-cluster-wrapper",
                            iconSize: [40, 40],
                        });
                    },
                });
                map.addLayer(transitStopMarkers);
            }
            loadNearbyStops();
        } else {
            if (transitStopMarkers) {
                transitStopMarkers.clearLayers();
            }
            elNearbyStopsList.innerHTML = '<div class="empty-state"><p>Toplu ulasim kapali</p></div>';
        }
    });
}

// Load nearby stops when map moves
map.on("moveend", function () {
    if (transitEnabled) {
        // Debounce
        clearTimeout(_transitDebounceTimer);
        _transitDebounceTimer = setTimeout(loadNearbyStops, 300);
    }
});

/**
 * Haritanin merkezine yakin duraklari yukler
 */
async function loadNearbyStops() {
    if (!transitEnabled) return;

    const center = map.getCenter();
    const zoom = map.getZoom();

    // Zoom seviyesine gore yaricap hesapla
    let radius = 500;
    if (zoom >= 16) radius = 300;
    else if (zoom >= 14) radius = 600;
    else if (zoom >= 12) radius = 1500;
    else radius = 3000;

    try {
        const response = await fetch(
            `${API_BASE}/transit/stops?lat=${center.lat}&lon=${center.lng}&radius=${radius}`
        );
        const data = await response.json();

        if (!response.ok) {
            console.error("Transit API hatasi:", data.error);
            return;
        }

        // Marker cluster guncelle
        if (transitStopMarkers) {
            transitStopMarkers.clearLayers();
        }

        const stops = data.stops || [];

        stops.forEach((stop) => {
            const marker = L.marker([stop.lat, stop.lon], {
                icon: createStopIcon(),
            });

            const popupContent = buildStopPopup(stop);
            marker.bindPopup(popupContent, {
                maxWidth: 280,
                minWidth: 200,
                className: "transit-popup",
            });

            transitStopMarkers.addLayer(marker);
        });

        // Sidebar listesini guncelle
        updateNearbyStopsList(stops);

    } catch (error) {
        console.error("Nearby stops hatasi:", error);
    }
}

/**
 * Durak popup olusturur
 */
function buildStopPopup(stop) {
    let html = '<div class="stop-popup-card">';
    html += `<div class="stop-popup-header">`;
    html += `<span class="stop-popup-emoji">&#x1F68F;</span>`;
    html += `<div>`;
    html += `<h3 class="stop-popup-name">${stop.name || "Durak"}</h3>`;
    html += `<span class="stop-popup-district">${stop.district || ""}</span>`;
    html += `</div></div>`;

    html += `<div class="stop-popup-details">`;
    html += `<div class="stop-detail"><span class="stop-detail-label">Kod:</span> ${stop.code}</div>`;
    if (stop.direction) {
        html += `<div class="stop-detail"><span class="stop-detail-label">Yon:</span> ${stop.direction}</div>`;
    }
    if (stop.distance_m !== undefined) {
        html += `<div class="stop-detail"><span class="stop-detail-label">Mesafe:</span> ${stop.distance_m}m</div>`;
    }
    if (stop.accessible && stop.accessible !== "Uygun Degil") {
        html += `<div class="stop-detail"><span class="stop-detail-label">Engelli:</span> Uygun</div>`;
    }
    html += `</div>`;

    // Rotaya ekle butonu
    html += `<button class="stop-popup-btn" onclick="addPoint(${stop.lat}, ${stop.lon})">+ Rotaya Ekle</button>`;

    html += `</div>`;
    return html;
}

/**
 * Sidebar yakin duraklar listesini gunceller
 */
function updateNearbyStopsList(stops) {
    if (!stops || stops.length === 0) {
        elNearbyStopsList.innerHTML = '<div class="empty-state"><p>Bu alanda durak bulunamadi</p></div>';
        return;
    }

    // Max 10 durak goster
    const displayStops = stops.slice(0, 10);

    let html = "";
    displayStops.forEach((stop) => {
        html += `
            <div class="nearby-stop-item" onclick="map.setView([${stop.lat}, ${stop.lon}], 17)">
                <div class="nearby-stop-info">
                    <span class="nearby-stop-name">${stop.name || "Durak"}</span>
                    <span class="nearby-stop-district">${stop.district || ""}</span>
                </div>
                <span class="nearby-stop-distance">${stop.distance_m}m</span>
            </div>
        `;
    });

    if (stops.length > 10) {
        html += `<div class="nearby-stop-more">${stops.length - 10} durak daha...</div>`;
    }

    elNearbyStopsList.innerHTML = html;
}

/**
 * Transit durak arama
 */
async function searchTransitStops() {
    const query = elTransitSearchInput.value.trim();

    if (!query || query.length < 2) {
        showToast("En az 2 karakter girin", "error");
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/transit/search?q=${encodeURIComponent(query)}&limit=10`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Arama hatasi");
        }

        displayTransitSearchResults(data.stops);

    } catch (error) {
        console.error("Transit arama hatasi:", error);
        showToast(`Arama hatasi: ${error.message}`, "error");
    }
}

/**
 * Transit arama sonuclarini gosterir
 */
function displayTransitSearchResults(stops) {
    elTransitSearchResults.style.display = "block";

    if (!stops || stops.length === 0) {
        elTransitSearchResults.innerHTML = '<div class="empty-state"><p>Sonuc bulunamadi</p></div>';
        return;
    }

    let html = "";
    stops.forEach((stop) => {
        html += `
            <div class="transit-result-item" onclick="selectTransitStop(${stop.lat}, ${stop.lon}, '${(stop.name || '').replace(/'/g, "\\'")}')">
                <span class="transit-result-icon">&#x1F68F;</span>
                <div class="transit-result-info">
                    <span class="transit-result-name">${stop.name || "Durak"}</span>
                    <span class="transit-result-district">${stop.district || ""} - Kod: ${stop.code}</span>
                </div>
            </div>
        `;
    });

    elTransitSearchResults.innerHTML = html;
}

/**
 * Transit arama sonucuna tiklaninca haritaya gider
 */
function selectTransitStop(lat, lon, name) {
    map.setView([lat, lon], 17);
    elTransitSearchInput.value = "";
    elTransitSearchResults.style.display = "none";
    showToast(`${name} duragi konumuna gidildi`, "info");
}

// Transit event listeners
if (elBtnSearchTransit) {
    elBtnSearchTransit.addEventListener("click", searchTransitStops);
}
if (elTransitSearchInput) {
    elTransitSearchInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") searchTransitStops();
    });
}


// ========== MULTIMODAL ROUTE COMPARISON ==========

if (elBtnCompareRoutes) {
    elBtnCompareRoutes.addEventListener("click", compareMultimodalRoutes);
}

/**
 * Yuruyus ve toplu tasima seceneklerini karsilastirir
 */
async function compareMultimodalRoutes() {
    if (selectedPoints.length < 2) {
        showToast("En az 2 nokta secmelisiniz!", "error");
        return;
    }

    // Ilk ve son nokta arasini karsilastir
    const origin = selectedPoints[0];
    const destination = selectedPoints[selectedPoints.length - 1];

    showLoading("Toplu tasima secenekleri hesaplaniyor...");

    try {
        const response = await fetch(`${API_BASE}/multimodal/compare`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                origin: origin,
                destination: destination,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Bilinmeyen hata");
        }

        displayMultimodalResults(data);
        showToast("Rota secenekleri hesaplandi!", "success");

    } catch (error) {
        console.error("Multimodal hatasi:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

// Transit route polyline layer
let transitRouteLayers = [];
let _multimodalData = null;

/**
 * Multimodal sonuclarini gosterir ve ilk secili rotayi haritada cizer
 */
function displayMultimodalResults(data) {
    elMultimodalPanel.style.display = "block";
    _multimodalData = data;

    const options = data.options || [];
    const recommended = data.recommended;

    let html = "";

    // Recommendation banner
    if (data.recommendation_reason) {
        const recClass = recommended === "transit" ? "rec-transit" : "rec-walking";
        const recIcon = recommended === "transit" ? "&#x1F68C;" : "&#x1F6B6;";
        html += `
            <div class="multimodal-rec ${recClass}">
                <span class="rec-icon">${recIcon}</span>
                <span class="rec-text">${data.recommendation_reason}</span>
            </div>
        `;
    }

    // Nearby routes info
    const nr = data.nearby_routes;
    if (nr && (nr.origin?.length || nr.destination?.length)) {
        html += `<div class="nearby-routes-info">`;
        if (nr.origin?.length) {
            html += `<div class="nearby-route-line"><span class="nearby-label">Baslangic hatlari:</span> ${nr.origin.map(r => `<span class="route-badge">${r.route_code}</span>`).join(" ")}</div>`;
        }
        if (nr.destination?.length) {
            html += `<div class="nearby-route-line"><span class="nearby-label">Hedef hatlari:</span> ${nr.destination.map(r => `<span class="route-badge">${r.route_code}</span>`).join(" ")}</div>`;
        }
        html += `</div>`;
    }

    options.forEach((opt, index) => {
        const isRec = (opt.type === recommended);
        const iconHtml = opt.type === "transit" ? "&#x1F68C;" : "&#x1F6B6;";

        html += `
            <div class="multimodal-option ${isRec ? 'recommended' : ''}" onclick="showTransitRoute(${index})" style="cursor:pointer;">
                <div class="multimodal-option-header">
                    <span class="multimodal-icon">${iconHtml}</span>
                    <div class="multimodal-option-info">
                        <h3 class="multimodal-option-name">${opt.name}</h3>
                        <p class="multimodal-option-desc">${opt.description}</p>
                    </div>
                    <div class="multimodal-option-time">
                        <span class="multimodal-time-value">${opt.total_time_min}</span>
                        <span class="multimodal-time-unit">dk</span>
                    </div>
                </div>
                <div class="multimodal-segments">
        `;

        // Segments (walk, bus, walk)
        if (opt.segments) {
            opt.segments.forEach((seg) => {
                const segIcon = seg.mode === "bus" ? "&#x1F68C;" : "&#x1F6B6;";
                const segClass = seg.mode === "bus" ? "seg-bus" : "seg-walk";

                html += `
                    <div class="multimodal-segment ${segClass}">
                        <span class="seg-icon">${segIcon}</span>
                        <span class="seg-desc">${seg.description || seg.mode}</span>
                        <span class="seg-time">${seg.duration_min} dk</span>
                    </div>
                `;

                if (seg.mode === "bus" && seg.wait_min) {
                    html += `
                        <div class="multimodal-segment seg-wait">
                            <span class="seg-icon">&#x23F3;</span>
                            <span class="seg-desc">Bekleme</span>
                            <span class="seg-time">~${seg.wait_min} dk</span>
                        </div>
                    `;
                }
            });
        }

        html += `
                    <div class="multimodal-show-map">
                        &#x1F5FA; Haritada Goster
                    </div>
                </div>
            </div>
        `;
    });

    if (options.length === 0) {
        html = '<div class="empty-state"><p>Secenek bulunamadi</p></div>';
    }

    elMultimodalResults.innerHTML = html;

    // Otomatik olarak onerilen rotayi haritada goster
    const recIndex = options.findIndex(o => o.type === recommended);
    if (recIndex >= 0) {
        showTransitRoute(recIndex);
    }

    // Scroll to panel
    elMultimodalPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/**
 * Secilen transit rotasini haritada cizer.
 * Tam yolculuk gosterilir: Yuru -> Otobuse bin -> Otobus guzergahi -> In -> Yuru
 * Mevcut graf rotasina dokunmaz.
 */
function showTransitRoute(optionIndex) {
    if (!_multimodalData || !_multimodalData.options) return;

    const opt = _multimodalData.options[optionIndex];
    if (!opt || !opt.segments) return;

    // Onceki transit cizimlerini temizle
    clearTransitRoute();

    const allBounds = [];
    let stepNum = 1;

    // Her segment icin ciz
    opt.segments.forEach((seg) => {
        if (!seg.coords || seg.coords.length < 2) return;

        const latlngs = seg.coords.map(c => [c[0], c[1]]);
        latlngs.forEach(ll => allBounds.push(ll));

        if (seg.mode === "walk") {
            // ---- YURUME SEGMENTI ----
            // Turuncu kesikli ince cizgi
            const walkLine = L.polyline(latlngs, {
                color: "#e17055",
                weight: 4,
                opacity: 0.85,
                dashArray: "6, 10",
                lineCap: "round",
            });
            walkLine.addTo(map);
            transitRouteLayers.push(walkLine);

            // Baslangic noktasi icin numarali marker
            const startCoord = latlngs[0];
            const startLabel = stepNum === 1 ? "Baslangic" : "Hedefe yuru";
            const startMarker = L.marker(startCoord, {
                icon: L.divIcon({
                    className: "transit-step-icon",
                    html: `<div class="step-circle step-walk">${stepNum}</div>`,
                    iconSize: [28, 28],
                    iconAnchor: [14, 14],
                }),
            });
            startMarker.bindTooltip(startLabel, {
                direction: "top",
                offset: [0, -16],
                className: "transit-route-tooltip",
            });
            startMarker.addTo(map);
            transitRouteLayers.push(startMarker);
            stepNum++;

        } else if (seg.mode === "bus") {
            // ---- OTOBUS SEGMENTI ----

            // 1. Glow efekti
            const busGlow = L.polyline(latlngs, {
                color: "#00cec9",
                weight: 14,
                opacity: 0.2,
                lineCap: "round",
                lineJoin: "round",
            });
            busGlow.addTo(map);
            transitRouteLayers.push(busGlow);

            // 2. Ana otobus cizgisi
            const busLine = L.polyline(latlngs, {
                color: "#00b894",
                weight: 5,
                opacity: 0.95,
                lineCap: "round",
                lineJoin: "round",
            });
            busLine.addTo(map);
            transitRouteLayers.push(busLine);

            // 3. Ara durak noktalari (kucuk beyaz daireler)
            seg.coords.forEach((coord, i) => {
                const isEndpoint = (i === 0 || i === seg.coords.length - 1);
                if (!isEndpoint) {
                    const stopDot = L.circleMarker([coord[0], coord[1]], {
                        radius: 3,
                        color: "#00cec9",
                        fillColor: "white",
                        fillOpacity: 1,
                        weight: 1,
                    });
                    stopDot.addTo(map);
                    transitRouteLayers.push(stopDot);
                }
            });

            // 4. BINIS duragi (buyuk yesil numarali marker)
            const boardCoord = latlngs[0];
            const boardMarker = L.marker(boardCoord, {
                icon: L.divIcon({
                    className: "transit-step-icon",
                    html: `<div class="step-circle step-board">${stepNum}</div>`,
                    iconSize: [28, 28],
                    iconAnchor: [14, 14],
                }),
            });
            boardMarker.bindTooltip(`Bin: ${seg.from_stop || "Durak"}`, {
                permanent: true,
                direction: "top",
                offset: [0, -16],
                className: "transit-route-tooltip transit-tooltip-board",
            });
            boardMarker.addTo(map);
            transitRouteLayers.push(boardMarker);
            stepNum++;

            // 5. INIS duragi (buyuk kirmizi numarali marker)
            const alightCoord = latlngs[latlngs.length - 1];
            const alightMarker = L.marker(alightCoord, {
                icon: L.divIcon({
                    className: "transit-step-icon",
                    html: `<div class="step-circle step-alight">${stepNum}</div>`,
                    iconSize: [28, 28],
                    iconAnchor: [14, 14],
                }),
            });
            alightMarker.bindTooltip(`In: ${seg.to_stop || "Durak"}`, {
                permanent: true,
                direction: "top",
                offset: [0, -16],
                className: "transit-route-tooltip transit-tooltip-alight",
            });
            alightMarker.addTo(map);
            transitRouteLayers.push(alightMarker);
            stepNum++;

            // 6. Hat kodu etiketi (ortada)
            if (seg.route_code && latlngs.length > 2) {
                const midIdx = Math.floor(latlngs.length / 2);
                const routeLabel = L.marker(latlngs[midIdx], {
                    icon: L.divIcon({
                        className: "transit-route-label",
                        html: `<div class="route-label-tag">${seg.route_code}</div>`,
                        iconSize: [60, 24],
                        iconAnchor: [30, 12],
                    }),
                });
                routeLabel.addTo(map);
                transitRouteLayers.push(routeLabel);
            }
        }
    });

    // Son segment'in bitis noktasina hedef marker ekle
    const lastSeg = opt.segments[opt.segments.length - 1];
    if (lastSeg && lastSeg.coords && lastSeg.coords.length > 0) {
        const endCoord = lastSeg.coords[lastSeg.coords.length - 1];
        const endMarker = L.marker([endCoord[0], endCoord[1]], {
            icon: L.divIcon({
                className: "transit-step-icon",
                html: `<div class="step-circle step-end">${stepNum}</div>`,
                iconSize: [28, 28],
                iconAnchor: [14, 14],
            }),
        });
        endMarker.bindTooltip("Hedef", {
            direction: "top",
            offset: [0, -16],
            className: "transit-route-tooltip",
        });
        endMarker.addTo(map);
        transitRouteLayers.push(endMarker);
    }

    // Haritayi tum rotaya sigdir
    if (allBounds.length > 0) {
        selectedPoints.forEach(p => allBounds.push(p));
        const bounds = L.latLngBounds(allBounds);
        map.fitBounds(bounds, { padding: [50, 50] });
    }

    // Aktif karti vurgula
    document.querySelectorAll(".multimodal-option").forEach((el, i) => {
        el.classList.toggle("active-route", i === optionIndex);
    });

    showToast(`${opt.name} - tam guzergah haritada`, "info");
}

/**
 * Transit rota cizimlerini temizler (mevcut yuruyus rotasina dokunmaz)
 */
function clearTransitRoute() {
    transitRouteLayers.forEach(layer => {
        map.removeLayer(layer);
    });
    transitRouteLayers = [];
}
