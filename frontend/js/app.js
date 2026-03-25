/**
 * app.js Ã¢â‚¬â€ OpenTrip Frontend Application
 *
 * Harita etkileÃ…Å¸imi, API iletiÃ…Å¸imi, rota gÃƒÂ¶sterimi ve POI arama.
 */

// ========== CONFIG ==========
const API_BASE = "/api";

// ========== STATE ==========
let selectedPoints = [];
let markers = [];
let routePolyline = null;
let routeGlowPolylines = [];  // Glow efektleri iÃƒÂ§in ayrÃ„Â± takip
let poiMarkers = [];
let lastPoiSearch = null;
let currentRouteData = null;
let alternativeRoutesCache = {};  // Alternatif rota verileri cache'i (BUG FIX 07.03.2026)
let currentNlpResult = null;

// ========== MAP INIT ==========
const map = L.map("map", {
    zoomControl: false,
}).setView([40.9903, 29.0291], 14); // KadÃ„Â±kÃƒÂ¶y merkez

// Custom zoom control (saÃ„Å¸ ÃƒÂ¼ste)
L.control.zoom({ position: "topright" }).addTo(map);

// Tile Layer Ã¢â‚¬â€ OpenStreetMap Standard (CanlÃ„Â±, detaylÃ„Â±, dÃƒÂ¼kkanlar gÃƒÂ¶rÃƒÂ¼nÃƒÂ¼r)
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
const elBtnRefreshPois = document.getElementById("btnRefreshPois");
const elBtnClearPois = document.getElementById("btnClearPois");
const elPoiMetaInfo = document.getElementById("poiMetaInfo");
const elToastContainer = document.getElementById("toastContainer");
const elPlaceSearchInput = document.getElementById("placeSearchInput");
const elBtnSearchPlace = document.getElementById("btnSearchPlace");
const elSearchResults = document.getElementById("searchResults");
const elNlpInput = document.getElementById("nlpInput");
const elBtnNLP = document.getElementById("btnNLP");
const elNlpResults = document.getElementById("nlpResults");
const elNlpLoading = document.getElementById("nlpLoading");
const elMainLlmBox = document.getElementById("mainLlmBox");
const elMainLlmProviderRadios = Array.from(document.querySelectorAll("input[name='mainLlmProvider']"));
const elMainLlmModeRadios = Array.from(document.querySelectorAll("input[name='mainLlmMode']"));
const elMainLlmAutoPanel = document.getElementById("mainLlmAutoPanel");
const elMainLlmManualPanel = document.getElementById("mainLlmManualPanel");
const elMainLlmCategory = document.getElementById("mainLlmCategory");
const elMainLlmModelSelect = document.getElementById("mainLlmModelSelect");
const elMainLlmCustomModel = document.getElementById("mainLlmCustomModel");
const elMainLlmStatusText = document.getElementById("mainLlmStatusText");
const elMainLlmActiveModel = document.getElementById("mainLlmActiveModel");
const elMainLlmChatLog = document.getElementById("mainLlmChatLog");
const elMainLlmInput = document.getElementById("mainLlmInput");
const elMainLlmSend = document.getElementById("mainLlmSend");
const elMainLlmClear = document.getElementById("mainLlmClear");
const elMainLlmSessionSelect = document.getElementById("mainLlmSessionSelect");
const elMainLlmNewSession = document.getElementById("mainLlmNewSession");
const elMainLlmArchiveSession = document.getElementById("mainLlmArchiveSession");
const elRightChatPanel = document.getElementById("rightChatPanel");
const elRightChatCollapse = document.getElementById("rightChatCollapse");
const elRightChatExpand = document.getElementById("rightChatExpand");
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

// Helper: geÃƒÂ§erli bir alan deÃ„Å¸eri mi? (undefined/null/''/'nan' ise geÃƒÂ§ersiz say)
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

    // Hava durumu widget'Ã„Â±nÃ„Â± bu noktaya gÃƒÂ¶re gÃƒÂ¼ncelle
    fetchWeatherWidget(lat, lng);

    // Marker ekle
    const marker = L.marker([lat, lng], {
        icon: createNumberedIcon(index + 1),
    }).addTo(map);

    // SaÃ„Å¸ tÃ„Â±klama menÃƒÂ¼sÃƒÂ¼ - Konumu Kaydet
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
            \u{1F4BE} Konumu Kaydet
         </button>`
    );

    markers.push(marker);

    updatePointsList();
    updateButtons();

    showToast(`Nokta ${index + 1} eklendi`, "info");
}

function removePoint(index) {
    // Marker'Ã„Â± kaldÃ„Â±r
    map.removeLayer(markers[index]);
    markers.splice(index, 1);
    selectedPoints.splice(index, 1);

    // Marker numaralarÃ„Â±nÃ„Â± gÃƒÂ¼ncelle
    markers.forEach((m, i) => {
        m.setIcon(createNumberedIcon(i + 1));
        m.setPopupContent(
            `<strong>Nokta ${i + 1}</strong><br>${selectedPoints[i][0].toFixed(5)}, ${selectedPoints[i][1].toFixed(5)}`
        );
    });

    updatePointsList();
    updateButtons();
    clearRoute();

    // Son kalan noktanÃ„Â±n hava durumunu gÃƒÂ¶ster, yoksa harita merkezi
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
    showToast("TÃƒÂ¼m noktalar silindi", "info");

    // Noktalar temizlenince harita merkezine geri dÃƒÂ¶n
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

    // Array'de yer deÃ„Å¸iÃ…Å¸tir
    const draggedPoint = selectedPoints.splice(draggedIndex, 1)[0];
    selectedPoints.splice(targetIndex, 0, draggedPoint);

    // Marker'larÃ„Â± da gÃƒÂ¼ncelle
    const draggedMarker = markers.splice(draggedIndex, 1)[0];
    markers.splice(targetIndex, 0, draggedMarker);

    // UI gÃƒÂ¼ncelle
    updatePointsList();

    // EÃ„Å¸er rota varsa, rota sÃ„Â±rasÃ„Â±nÃ„Â± gÃƒÂ¼ncelle
    if (currentRouteData) {
        clearRoute();
        showToast('Nokta sÃ„Â±rasÃ„Â± deÃ„Å¸iÃ…Å¸tirildi. Rota iÃƒÂ§in tekrar hesaplayÃ„Â±n.', 'info');
    }
}

function updatePointsList() {
    elPointCount.textContent = selectedPoints.length;

    if (selectedPoints.length === 0) {
        elPointsList.innerHTML = `<div class="empty-state"><p>Haritaya tÃ„Â±klayarak nokta ekleyin</p></div>`;
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
                <div class="drag-handle" title="SÃ„Â±ralamak iÃƒÂ§in sÃƒÂ¼rÃƒÂ¼kle">
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
    if (elBtnCompareRoutes) {
        elBtnCompareRoutes.disabled = selectedPoints.length < 2;
    }
}

// ========== ROUTE CALCULATION ==========
async function calculateRoute() {
    if (selectedPoints.length < 2) {
        showToast("En az 2 nokta seÃƒÂ§melisiniz!", "error");
        return;
    }

    showLoading("Rota hesaplanÃ„Â±yor...\nHarita verisi ilk kez indiriliyorsa biraz zaman alabilir.");

    const optimize = false; // TSP optimizasyonu devre dÃ„Â±Ã…Å¸Ã„Â±

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
        updateButtons();  // Buton durumlarÃ„Â±nÃ„Â± gÃƒÂ¼ncelle
        showToast("Rota baÃ…Å¸arÃ„Â±yla hesaplandÃ„Â±! \u{2705}", "success");

        // Hava durumu uyarÃ„Â±larÃ„Â±nÃ„Â± gÃƒÂ¶ster (arka planda, rotayÃ„Â± engelleme)
        checkRouteWeatherAndShowBanner(selectedPoints);

    } catch (error) {
        console.error("Rota hesaplama hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

function drawRoute(data) {
    clearRoute();

    if (!data.route_coords || data.route_coords.length === 0) return;

    // Rota ÃƒÂ§izgisini ÃƒÂ§iz Ã¢â‚¬â€ gradient efektli
    routePolyline = L.polyline(data.route_coords, {
        color: "#6c5ce7",
        weight: 5,
        opacity: 0.85,
        smoothFactor: 1,
        dashArray: null,
    }).addTo(map);

<<<<<<< Updated upstream
    // Rota ÃƒÂ§izgisi ÃƒÂ¼stÃƒÂ¼ne glow efekti
    const glow = L.polyline(data.route_coords, {
=======
    // Rota çizgisi üstüne glow efekti
    const glowLine = L.polyline(data.route_coords, {
>>>>>>> Stashed changes
        color: "#a594f9",
        weight: 10,
        opacity: 0.2,
        smoothFactor: 1,
    }).addTo(map);
<<<<<<< Updated upstream
    routeGlowPolylines.push(glow);
=======
    routeGlowPolylines.push(glowLine);
>>>>>>> Stashed changes

    // HaritayÃ„Â± rotaya sÃ„Â±Ã„Å¸dÃ„Â±r
    map.fitBounds(routePolyline.getBounds(), { padding: [60, 60] });
}

function clearRoute() {
    clearTransitRoute();

    if (routePolyline) {
        map.removeLayer(routePolyline);
        routePolyline = null;
    }

    // Glow katmanlarÃ„Â±nÃ„Â± temizle (routeGlowPolylines takip listesiyle)
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
/**
 * POI buton metninden (ÃƒÂ¶rn. "ÄŸÅ¸Ââ€ºÃ¯Â¸Â Belediye") harita iÃ…Å¸areti emojisi ve TÃƒÂ¼rkÃƒÂ§e etiket ÃƒÂ¼retir.
 * index.html'deki data-category API'ye gider; emoji/etiket butonun ilk satÃ„Â±rÃ„Â±ndan okunur.
 */
function parsePoiButtonLabel(buttonText) {
    const raw = (buttonText || "").trim();
    if (!raw) {
        return { emoji: "\u{1F4CD}", label: "" };
    }
    const parts = raw.split(/\s+/);
    const emoji = parts[0] || "\u{1F4CD}";
    const label = parts.length > 1 ? parts.slice(1).join(" ") : "";
    return { emoji, label };
}

function formatPoiAge(ageSeconds) {
    if (ageSeconds === null || ageSeconds === undefined || Number.isNaN(Number(ageSeconds))) {
        return "-";
    }
    const sec = Math.max(0, Number(ageSeconds));
    if (sec < 60) return `${Math.round(sec)} sn`;
    if (sec < 3600) return `${Math.round(sec / 60)} dk`;
    if (sec < 86400) return `${(sec / 3600).toFixed(1)} saat`;
    return `${(sec / 86400).toFixed(1)} gun`;
}

function renderPoiMeta(info) {
    if (!elPoiMetaInfo) return;
    const cache = (info && info.cache) || {};
    const statusMap = {
        fresh_cache_hit: "Cache (guncel)",
        empty_cache_hit: "Cache (bos sonuc)",
        stale_cache_served: "Cache (eski, arka planda yenileniyor)",
        live_fetch: "Canli sorgu",
        forced_live_refresh: "Canli zorunlu yenileme",
        live_refresh_after_expiry: "Canli sorgu (cache suresi dolmus)",
        fallback_on_error: "Canli hata, cache geri dondu",
        error_live_fetch: "Canli hata",
        legacy_no_meta: "Cache durumu bilinmiyor",
    };

    let lastUpdatedText = "-";
    if (cache.last_updated) {
        const dt = new Date(cache.last_updated);
        if (!Number.isNaN(dt.getTime())) {
            lastUpdatedText = dt.toLocaleString("tr-TR");
        }
    }

    const statusText = statusMap[cache.status] || cache.status || "-";
    const ageText = formatPoiAge(cache.age_seconds);
    const bgText = cache.background_refresh ? "acik" : "kapali";
    const countText = Number.isFinite(info?.count) ? info.count : "-";
    elPoiMetaInfo.textContent = `Durum: ${statusText} | Son guncelleme: ${lastUpdatedText} | Yas: ${ageText} | Sonuc: ${countText} | Arka plan yenileme: ${bgText}`;
}

async function searchPois(category, markerEmoji, markerLabel, opts = {}) {
    const forceRefresh = Boolean(opts.forceRefresh);

    // Yeni dropdown'lardan veri al
    const province = elProvinceSelect.value;
    const districtRaw = (elDistrictSelect.value || "").trim();
    const districtNorm = districtRaw.toLocaleLowerCase("tr-TR").replace(/ÃƒÂ§/g, "c").replace(/Ã…Å¸/g, "s").replace(/Ã„Â±/g, "i").replace(/Ã„Â°/g, "i");
    const district = districtNorm.includes("ilce secin") ? "" : districtRaw;

    // Eger il secilmemisse uyari ver
    if (!province && !opts.placeOverride) {
        showToast('Lutfen once bir il secin', 'warning');
        return;
    }

    // Ilce secilmisse ilce, yoksa il kullan
    const place = (opts.placeOverride && String(opts.placeOverride).trim())
        ? String(opts.placeOverride).trim()
        : (district ? `${district}, ${province}, Turkey` : `${province}, Turkey`);

    // POI'de il/ilce secimi daima idari sinir (place boundary) uzerinden taransin.
    const searchMode = "place_boundary_only";

    lastPoiSearch = {
        category,
        markerEmoji,
        markerLabel,
        place,
    };

    const loadingText = forceRefresh
        ? `"${category}" mekanlari canli yenileniyor...`
        : `"${category}" mekanlari araniyor...`;
    showLoading(loadingText);

    try {
        const response = await fetch(`${API_BASE}/search-pois`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                place,
                category,
                search_mode: searchMode,
                force_refresh: forceRefresh,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "POI arama hatasi");
        }

        clearPois();
        displayPois(data.pois, category, markerEmoji, markerLabel);
        renderPoiMeta({
            cache: data.poi_cache,
            count: data.pois.length,
        });

        const toastPrefix = forceRefresh ? "Canli yenileme: " : "";
        showToast(`${toastPrefix}${data.pois.length} adet "${category}" bulundu`, "success");

    } catch (error) {
        console.error("POI arama hatasi:", error);
        if (elPoiMetaInfo) {
            elPoiMetaInfo.textContent = `POI arama hatasi: ${error.message}`;
        }
        showToast(`POI arama hatasi: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}
function displayPois(pois, category, markerEmoji, markerLabel) {
    const pin = "\u{1F4CD}";
    const emoji = markerEmoji || pin;
    const label = (markerLabel && String(markerLabel).trim()) || category;

    pois.forEach((poi) => {
        const marker = L.marker([poi.lat, poi.lon], {
            icon: createPoiIcon(emoji),
        }).addTo(map);

        // Zengin popup kartÃ„Â± oluÃ…Å¸tur
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

    // BaÃ…Å¸lÃ„Â±k
    html += `<div class="poi-card-header">`;
    html += `<span class="poi-card-emoji">${emoji}</span>`;
    html += `<div>`;
    html += `<h3 class="poi-card-title">${poi.name}</h3>`;
    html += `<span class="poi-card-category">${label}</span>`;
    html += `</div>`;
    html += `</div>`;

    // AÃƒÂ§Ã„Â±klama
    if (poi.description) {
        html += `<p class="poi-card-desc">${poi.description}</p>`;
    }

    // Detaylar
    let hasDetails = false;
    html += `<div class="poi-card-details">`;

    if (isValidField(poi.opening_hours)) {
        html += `<div class="poi-detail"><span class="poi-detail-icon">\u{1F550}</span> ${poi.opening_hours}</div>`;
        hasDetails = true;
    }

    if (isValidField(poi.website)) {
        html += `<div class="poi-detail"><span class="poi-detail-icon">\u{1F310}</span> <a href="${poi.website}" target="_blank" rel="noopener">Web Sitesi</a></div>`;
        hasDetails = true;
    }

    if (poi.wikipedia_url) {
        html += `<div class="poi-detail"><span class="poi-detail-icon">\u{1F4D5}</span> <a href="${poi.wikipedia_url}" target="_blank" rel="noopener">Wikipedia</a></div>`;
        hasDetails = true;
    }

    if (!hasDetails) {
        html += `<div class="poi-detail"><span class="poi-detail-icon">\u{1F4CD}</span> ${poi.lat.toFixed(5)}, ${poi.lon.toFixed(5)}</div>`;
    }

    html += `</div>`;

    // Rotaya ekle butonu
    html += `<button class="poi-card-btn" data-action-add-point data-lat="${poi.lat}" data-lon="${poi.lon}">+ Rotaya Ekle</button>`;

    html += `</div>`;
    return html;
}

function clearPois() {
    poiMarkers.forEach((m) => map.removeLayer(m));
    poiMarkers = [];
    elBtnClearPois.style.display = "none";

    // POI butonlarÃ„Â±nÃ„Â±n active sÃ„Â±nÃ„Â±fÃ„Â±nÃ„Â± kaldÃ„Â±r
    document.querySelectorAll(".btn-poi").forEach((btn) => btn.classList.remove("active"));
}

// ========== LOADING ==========
function showLoading(text) {
    elLoadingText.textContent = text || "YÃƒÂ¼kleniyor...";
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

    // 3 saniye sonra kaldÃ„Â±r
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
if (elBtnRefreshPois) {
    elBtnRefreshPois.addEventListener("click", function () {
        if (!lastPoiSearch) {
            showToast("Once bir POI aramasi yap", "warning");
            return;
        }
        searchPois(
            lastPoiSearch.category,
            lastPoiSearch.markerEmoji,
            lastPoiSearch.markerLabel,
            { forceRefresh: true, placeOverride: lastPoiSearch.place }
        );
    });
}
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

// POI butonlarÃ„Â±
document.querySelectorAll(".btn-poi").forEach((btn) => {
    btn.addEventListener("click", function () {
        const category = this.dataset.category;
        const { emoji: markerEmoji, label: markerLabel } = parsePoiButtonLabel(this.textContent);

        // Toggle active sÃ„Â±nÃ„Â±fÃ„Â±
        document.querySelectorAll(".btn-poi").forEach((b) => b.classList.remove("active"));
        this.classList.add("active");

        searchPois(category, markerEmoji, markerLabel || category);
    });
});

// Ã„Â°lk bildirim
showToast("Haritaya tÃ„Â±klayarak baÃ…Å¸layÃ„Â±n! \u{1F5FA}\u{FE0F}", "info");

// KaydedilmiÃ…Å¸ rotalarÃ„Â± ve yerleri yÃƒÂ¼kle
loadSavedRoutes();
loadSavedLocations();

// Hava durumu widget'inÃ„Â± baÃ…Å¸lat
initWeatherWidget();

// ========== PLACE SEARCH (GEOCODING) ==========

// Debounce: yazmayÃ„Â± bitirdikten sonra ÃƒÂ¶neri isteÃ„Å¸i at
// Ã„Â°yileÃ…Å¸tirme: Request cancellation + adaptive delay
let suggestDebounceTimer = null;
let suggestAbortController = null;
const SUGGEST_DELAY_MS = 400;
const SUGGEST_DELAY_MS_SHORT = 200;  // KÃ„Â±sa sorgular iÃƒÂ§in daha hÃ„Â±zlÃ„Â±

elPlaceSearchInput.addEventListener("input", function () {
    const query = elPlaceSearchInput.value.trim();

    if (query.length < 2) {
        elSearchResults.style.display = "none";
        clearTimeout(suggestDebounceTimer);
        if (suggestAbortController) {
            suggestAbortController.abort();  // Bekleyen isteÃ„Å¸i iptal et
        }
        return;
    }

    // Ãƒâ€“nceki isteÃ„Å¸i iptal et
    if (suggestAbortController) {
        suggestAbortController.abort();
    }

    // Yeni AbortController oluÃ…Å¸tur
    suggestAbortController = new AbortController();

    // Adaptive delay: kÃ„Â±sa sorgular daha hÃ„Â±zlÃ„Â±, uzun sorgular daha yavaÃ…Å¸
    const delay = query.length < 4 ? SUGGEST_DELAY_MS_SHORT : SUGGEST_DELAY_MS;

    clearTimeout(suggestDebounceTimer);
    suggestDebounceTimer = setTimeout(
        () => fetchSuggestions(query, suggestAbortController.signal),
        delay
    );
});

// Enter tuÃ…Å¸u ile tam arama
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

// DÃ„Â±Ã…Å¸arÃ„Â± tÃ„Â±klanÃ„Â±nca ÃƒÂ¶nerileri kapat
document.addEventListener("click", function (e) {
    if (!elPlaceSearchInput.contains(e.target) && !elSearchResults.contains(e.target)) {
        elSearchResults.style.display = "none";
    }
});

/**
 * Yazarken ÃƒÂ¶neri listesi getirir (autocomplete)
 * Ã„Â°yileÃ…Å¸tirme: AbortController ile request cancellation
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
                <div class="search-result-name">\u{1F4CD} ${escapeHtml(s.display_name)}</div>
                <div class="search-result-coords">${s.lat.toFixed(5)}, ${s.lon.toFixed(5)}</div>
            </div>
        `).join("");

        // Ãƒâ€“neri tÃ„Â±klama
        elSearchResults.querySelectorAll(".search-suggestion-item").forEach((el) => {
            el.addEventListener("click", () => {
                const lat = parseFloat(el.dataset.lat);
                const lon = parseFloat(el.dataset.lon);
                const nameEl = el.querySelector(".search-result-name");
                // Basliktaki ikon/emoji prefix'ini temizle
                const name = nameEl ? nameEl.textContent.replace(/^[^\p{L}\p{N}]+\s*/u, "").trim() : "";
                selectSearchResult(lat, lon, name);
            });
        });
    } catch (err) {
        // AbortError ise sessizce geÃƒÂ§ (kullanÃ„Â±cÃ„Â± hala yazÃ„Â±yor)
        if (err.name === 'AbortError') {
            return;
        }
        console.error("Ãƒâ€“neri hatasÃ„Â±:", err);
        elSearchResults.style.display = "none";
    }
}

/**
 * Yer ismi ile arama yapar (Geocoding API)
 */
async function searchPlace() {
    const query = elPlaceSearchInput.value.trim();

    if (!query) {
        showToast("LÃƒÂ¼tfen bir yer ismi girin", "error");
        return;
    }

    if (query.length < 2) {
        showToast("Arama terimi ÃƒÂ§ok kÃ„Â±sa", "error");
        return;
    }

    showLoading("Yer aranÃ„Â±yor...");

    try {
        const response = await fetch(`${API_BASE}/geocode`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ place: query }),
        });

        const data = await response.json();

        if (!response.ok || data.status === "error") {
            throw new Error(data.message || "Yer bulunamadÃ„Â±");
        }

        displaySearchResult(data);
        showToast(`Bulundu: ${data.display_name}`, "success");

    } catch (error) {
        console.error("Geocoding hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
        elSearchResults.style.display = "none";
    } finally {
        hideLoading();
    }
}

/**
 * Arama sonucunu gÃƒÂ¶sterir
 */
function displaySearchResult(data) {
    elSearchResults.style.display = "block";
    const displayName = data.display_name || "Bilinmeyen konum";
    const shortName = displayName.split(",")[0].trim();

    elSearchResults.innerHTML = `
        <div class="search-result-item">
            <div class="search-result-name">\u{1F4CD} ${escapeHtml(displayName)}</div>
            <div class="search-result-coords">${data.lat.toFixed(5)}, ${data.lon.toFixed(5)}</div>
            <button
                class="btn btn-ghost btn-sm"
                data-action="save-location"
                style="margin-top:5px; width: 100%; border: 1px solid rgba(255,255,255,0.1);"
            >
                \u{1F4BE} Bu Konumu Kaydet
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
 * Arama sonucuna tÃ„Â±klanÃ„Â±nca haritaya ekler
 */
function selectSearchResult(lat, lon, name) {
    // HaritayÃ„Â± o noktaya odakla
    map.setView([lat, lon], 16);

    // NoktayÃ„Â± ekle
    addPoint(lat, lon);

    // Input ve sonuÃƒÂ§larÃ„Â± temizle
    elPlaceSearchInput.value = "";
    elSearchResults.style.display = "none";

    showToast(`"${name}" rotaya eklendi`, "success");
}

/**
 * HTML kaÃƒÂ§Ã„Â±Ã…Å¸ karakterleri
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
        throw new Error(data.message || `"${placeName}" bulunamadÃ„Â±`);
    }

    return data;
}

function setNlpLoading(isLoading) {
    elBtnNLP.disabled = isLoading;
    elNlpLoading.style.display = isLoading ? "flex" : "none";
}

function buildNlpSummary(result) {
    if (result.type === "route") {
        return `${escapeHtml(result.origin || "?" )} Ã¢â‚¬Âº ${escapeHtml(result.destination || "?")}`;
    }
    if (result.type === "multi") {
        return (result.locations || []).map(escapeHtml).join(" Ã¢â‚¬Âº ");
    }
    if (result.type === "poi") {
        return `${escapeHtml(result.location || "Bilinmeyen konum")} iÃƒÂ§in mekan aramasÃ„Â±`;
    }
    if (result.type === "single") {
        return `${escapeHtml(result.destination || "Bilinmeyen hedef")} hedef olarak algÃ„Â±landÃ„Â±`;
    }
    return escapeHtml(result.error || "Sorgu anlaÃ…Å¸Ã„Â±lamadÃ„Â±");
}

function renderNlpResults(result) {
    currentNlpResult = result;

    const confidence = typeof result.confidence === "number"
        ? `%${Math.round(result.confidence * 100)}`
        : "Ã¢â‚¬â€";

    const detectedPlaces = Array.isArray(result.detected_places) ? result.detected_places : [];
    const placesHtml = detectedPlaces.length > 0
        ? `
            <div class="nlp-result-places">
                ${detectedPlaces.map((item) => `
                    <span class="nlp-place-tag">
                        \u{1F4CD} ${escapeHtml(item.place)}
                    </span>
                `).join("")}
            </div>
        `
        : "";

    const actions = [];
    if (result.type === "route" || result.type === "multi") {
        actions.push(`<button class="nlp-action-btn primary" data-action="apply-nlp">Haritaya Uygula</button>`);
    } else if ((result.type === "single" && result.destination) || (result.type === "poi" && result.location)) {
        actions.push(`<button class="nlp-action-btn primary" data-action="focus-nlp">Haritada GÃƒÂ¶ster</button>`);
    }

    elNlpResults.innerHTML = `
        <div class="nlp-result-item">
            <div class="nlp-result-type">${escapeHtml(result.type || "unknown")}</div>
            <div class="nlp-result-content">${buildNlpSummary(result)}</div>
            <div class="nlp-result-confidence">GÃƒÂ¼ven: ${confidence}</div>
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
        showToast("LÃƒÂ¼tfen bir sorgu girin", "error");
        return;
    }

    setNlpLoading(true);
    elNlpResults.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/nlp/parse`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "NLP analizi baÃ…Å¸arÃ„Â±sÃ„Â±z");
        }

        renderNlpResults(data);
        showToast(`AI analiz tamamlandÃ„Â± (${data.engine || "nlp"})`, "success");
    } catch (error) {
        console.error("NLP analizi hatasÃ„Â±:", error);
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
        showToast("Uygulanacak yeterli konum bulunamadÃ„Â±", "error");
        return;
    }

    showLoading("AI sonucu haritaya uygulanÃ„Â±yor...");

    try {
        clearAllPoints();

        for (const placeName of targetPlaces) {
            const place = await geocodePlaceName(placeName);
            addPoint(place.lat, place.lon);
        }

        await calculateRoute();
    } catch (error) {
        console.error("NLP uygulama hatasÃ„Â±:", error);
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
        showToast("GÃƒÂ¶sterilecek konum bulunamadÃ„Â±", "error");
        return;
    }

    showLoading("Konum bulunuyor...");

    try {
        const place = await geocodePlaceName(placeName);
        map.setView([place.lat, place.lon], 16);
        addPoint(place.lat, place.lon);
        showToast(`"${placeName}" haritada gÃƒÂ¶sterildi`, "success");
    } catch (error) {
        console.error("NLP konum gÃƒÂ¶sterme hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}


// ========== MAIN LLM CHAT (OPENROUTER/GEMINI) ==========

let mainLlmMessages = [];
let mainLlmSessions = [];
let mainLlmActiveSessionId = "";
let mainLlmStreaming = false;
let mainLlmStatusInfo = null;
let mainLlmCurrentAttemptModel = "";
const mainLlmManualCandidates = [];
const MAIN_LLM_ACTIVE_SESSION_KEY = "opentrip.main_llm.active_session";

const mainLlmKnownOkModels = new Set([
    "arcee-ai/trinity-mini:free",
    "arcee-ai/trinity-mini-20251201:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-super-120b-a12b-20230311:free",
    "stepfun/step-3.5-flash:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-3-12b-it:free",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
]);

const mainLlmKnownLimitModels = new Set([
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "minimax/minimax-m2.5:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "google/gemma-3n-e2b-it:free",
    "google/gemma-3n-e4b-it:free",
    "google/gemma-3-4b-it:free",
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-120b:free",
    "qwen/qwen3-coder:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "z-ai/glm-4.5-air:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "qwen/qwen3-4b:free",
]);

const mainLlmKnownStalledModels = new Set([
    "liquid/lfm-2.5-1.2b-thinking:free",
    "liquid/lfm-2.5-1.2b-thinking-20260120:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
]);

const mainLlmKnownCreditModels = new Set([
    "sourceful/riverflow-v2-pro",
    "sourceful/riverflow-v2-fast",
    "sourceful/riverflow-v2-max-preview",
    "sourceful/riverflow-v2-standard-preview",
    "sourceful/riverflow-v2-fast-preview",
    "black-forest-labs/flux.2-klein-4b",
    "black-forest-labs/flux.2-max",
    "black-forest-labs/flux.2-flex",
    "black-forest-labs/flux.2-pro",
    "bytedance-seed/seedream-4.5",
]);

const mainLlmKnownEmbeddingModels = new Set([
    "nvidia/llama-nemotron-embed-vl-1b-v2:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
]);

const mainLlmExtraKnownModels = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "qwen/qwen3-4b:free",
    "qwen/qwen3-coder:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "google/gemma-3-12b-it:free",
    "google/gemma-3-4b-it:free",
    "google/gemma-3n-e2b-it:free",
    "google/gemma-3n-e4b-it:free",
    "stepfun/step-3.5-flash:free",
    "arcee-ai/trinity-mini:free",
    "arcee-ai/trinity-mini-20251201:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "nvidia/llama-nemotron-embed-vl-1b-v2:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
];

const mainLlmMojibakeReplacements = {
    "ÃƒÂ¼": "Ã¼",
    "ÃƒÅ“": "Ãœ",
    "ÃƒÂ¶": "Ã¶",
    "Ãƒâ€“": "Ã–",
    "ÃƒÂ§": "Ã§",
    "Ãƒâ€¡": "Ã‡",
    "Ã„Â±": "Ä±",
    "Ã„Â°": "Ä°",
    "Ã…Å¸": "ÅŸ",
    "Ã…Å¾": "Å",
    "Ã„Å¸": "ÄŸ",
    "Ã„Å¾": "Ä",
    "Ã¢â‚¬â„¢": "'",
    "Ã¢â‚¬Ëœ": "'",
    "Ã¢â‚¬Å“": '"',
    "Ã¢â‚¬Â": '"',
    "Ã¢â‚¬â€œ": "-",
    "Ã¢â‚¬â€": "-",
    "Ã¢â‚¬Â¦": "...",
};

function mainLlmRepairText(text) {
    if (text === undefined || text === null) return "";
    let out = String(text);
    if (/[ÃÄÅâ]/.test(out)) {
        try {
            out = decodeURIComponent(escape(out));
        } catch (_) {
            // ignore
        }
    }
    for (const [bad, good] of Object.entries(mainLlmMojibakeReplacements)) {
        out = out.split(bad).join(good);
    }
    return out.replace(/Â/g, "").trim();
}

function mainLlmGetProvider() {
    const checked = elMainLlmProviderRadios.find((radio) => radio.checked);
    return checked ? checked.value : "openrouter";
}

function mainLlmGetMode() {
    const checked = elMainLlmModeRadios.find((radio) => radio.checked);
    return checked ? checked.value : "auto";
}

function mainLlmLocalCacheKey(sessionId) {
    return `opentrip.main_llm.messages.${sessionId}`;
}

function mainLlmSaveLocalCache(sessionId) {
    if (!sessionId) return;
    try {
        localStorage.setItem(mainLlmLocalCacheKey(sessionId), JSON.stringify(mainLlmMessages));
        localStorage.setItem(MAIN_LLM_ACTIVE_SESSION_KEY, sessionId);
    } catch (_) {
        // ignore
    }
}

function mainLlmLoadLocalCache(sessionId) {
    if (!sessionId) return [];
    try {
        const raw = localStorage.getItem(mainLlmLocalCacheKey(sessionId));
        const parsed = raw ? JSON.parse(raw) : [];
        if (!Array.isArray(parsed)) return [];
        return parsed
            .filter((item) => item && (item.role === "user" || item.role === "assistant"))
            .map((item) => ({
                role: item.role,
                content: mainLlmRepairText(item.content || ""),
                model: mainLlmRepairText(item.model || ""),
                token_total: item.token_total ?? null,
                error_type: mainLlmRepairText(item.error_type || ""),
                created_at: item.created_at || "",
            }));
    } catch (_) {
        return [];
    }
}

function mainLlmSetStatus(text) {
    if (elMainLlmStatusText) {
        elMainLlmStatusText.textContent = mainLlmRepairText(text || "-");
    }
}

function mainLlmSetActiveModel(model, triedModels) {
    if (!elMainLlmActiveModel) return;
    const cleanedModel = mainLlmRepairText(model || "-");
    const cleanedTried = Array.isArray(triedModels) ? triedModels.map((m) => mainLlmRepairText(m)) : [];
    const tried = cleanedTried.length ? ` | denenen: ${cleanedTried.join(" -> ")}` : "";
    elMainLlmActiveModel.textContent = `Aktif model: ${cleanedModel}${tried}`;
}

function mainLlmClassifyModel(model) {
    const m = String(model || "").trim();
    if (!m) return "other";
    if (mainLlmKnownStalledModels.has(m)) return "stalled";
    if (mainLlmKnownEmbeddingModels.has(m) || m.includes("embed")) return "embedding";
    if (mainLlmKnownCreditModels.has(m)) return "credit";
    if (mainLlmKnownOkModels.has(m)) return "ok";
    if (mainLlmKnownLimitModels.has(m)) return "limit";
    return "other";
}

function mainLlmSelectedManualModel() {
    const customModel = String(elMainLlmCustomModel?.value || "").trim();
    if (customModel) return customModel;
    return String(elMainLlmModelSelect?.value || "").trim();
}

function mainLlmClassifyError(errorText) {
    const txt = String(errorText || "").toLowerCase();
    if (txt.includes("(429)") || txt.includes("rate-limit") || txt.includes("temporarily rate-limited")) return "limit";
    if (txt.includes("(402)") || txt.includes("insufficient credits")) return "credit";
    if (txt.includes("(400)") && (txt.includes("embedding model") || txt.includes("chat/completions endpoint"))) return "incompat";
    if (txt.includes("(404)") && txt.includes("guardrail restrictions")) return "privacy";
    return "other";
}

function mainLlmAppendMeta(target, text) {
    if (!target || !text) return;
    const meta = document.createElement("div");
    meta.className = "llm-msg-meta";
    meta.textContent = mainLlmRepairText(text);
    target.appendChild(meta);
}

function mainLlmAddMessage(role, text) {
    if (!elMainLlmChatLog) return null;
    const msg = document.createElement("div");
    msg.className = `llm-msg ${role === "user" ? "llm-msg-user" : "llm-msg-assistant"}`;
    msg.textContent = mainLlmRepairText(text || "");
    elMainLlmChatLog.appendChild(msg);
    elMainLlmChatLog.scrollTop = elMainLlmChatLog.scrollHeight;
    return msg;
}

function mainLlmRenderMessages() {
    if (!elMainLlmChatLog) return;
    elMainLlmChatLog.innerHTML = "";
    mainLlmMessages.forEach((msg) => {
        const box = mainLlmAddMessage(msg.role, msg.content || "");
        if (box && (msg.model || msg.token_total !== null && msg.token_total !== undefined)) {
            const model = mainLlmRepairText(msg.model || "-");
            const token = msg.token_total === null || msg.token_total === undefined ? "-" : msg.token_total;
            mainLlmAppendMeta(box, `model: ${model} | token: ${token}`);
        }
    });
}

function mainLlmUpdateModeUi() {
    if (!elMainLlmBox) return;
    const isManual = mainLlmGetMode() === "manual";

    if (elMainLlmAutoPanel) {
        elMainLlmAutoPanel.classList.toggle("active", !isManual);
    }
    if (elMainLlmManualPanel) {
        elMainLlmManualPanel.classList.toggle("active", isManual);
    }
    elMainLlmProviderRadios.forEach((radio) => {
        radio.disabled = mainLlmStreaming;
    });
    if (elMainLlmCategory) {
        elMainLlmCategory.disabled = !isManual || mainLlmStreaming;
    }
    if (elMainLlmModelSelect) {
        elMainLlmModelSelect.disabled = !isManual || mainLlmStreaming;
    }
    if (elMainLlmCustomModel) {
        elMainLlmCustomModel.disabled = !isManual || mainLlmStreaming;
    }
    if (elMainLlmSessionSelect) {
        elMainLlmSessionSelect.disabled = mainLlmStreaming;
    }
    if (elMainLlmNewSession) {
        elMainLlmNewSession.disabled = mainLlmStreaming;
    }
    if (elMainLlmArchiveSession) {
        elMainLlmArchiveSession.disabled = mainLlmStreaming || !mainLlmActiveSessionId;
    }
}

function mainLlmRefreshModelOptions() {
    if (!elMainLlmModelSelect || !elMainLlmCategory) return;

    const currentSelected = elMainLlmModelSelect.value;
    elMainLlmModelSelect.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Model sec...";
    elMainLlmModelSelect.appendChild(placeholder);

    const selectedCategory = elMainLlmCategory.value || "all";
    const groups = {
        ok: [],
        stalled: [],
        limit: [],
        credit: [],
        embedding: [],
        other: [],
    };
    const labels = {
        ok: "Sorunsuz Calisanlar",
        stalled: "Tikananlar",
        limit: "Limit Hatasi (429)",
        credit: "Para/Kredi Gerektiren (402)",
        embedding: "Embedding/VL (chat uyumsuz)",
        other: "Diger/Belirsiz",
    };

    const unique = new Set();
    const addModel = (model) => {
        const m = String(model || "").trim();
        if (!m || unique.has(m)) return;
        unique.add(m);
        groups[mainLlmClassifyModel(m)].push(m);
    };

    mainLlmManualCandidates.forEach(addModel);
    mainLlmExtraKnownModels.forEach(addModel);
    if (mainLlmStatusInfo) {
        addModel(mainLlmStatusInfo.default_model);
        (mainLlmStatusInfo.fallback_models || []).forEach(addModel);
    }

    ["ok", "stalled", "limit", "credit", "embedding", "other"].forEach((category) => {
        if (selectedCategory !== "all" && selectedCategory !== category) return;
        const items = groups[category];
        if (!items.length) return;
        items.sort();
        const optGroup = document.createElement("optgroup");
        optGroup.label = labels[category];
        items.forEach((model) => {
            const option = document.createElement("option");
            option.value = model;
            option.textContent = model;
            optGroup.appendChild(option);
        });
        elMainLlmModelSelect.appendChild(optGroup);
    });

    if (currentSelected && [...elMainLlmModelSelect.options].some((o) => o.value === currentSelected)) {
        elMainLlmModelSelect.value = currentSelected;
    }
}

function mainLlmSortSessions(sessions) {
    return [...sessions].sort((a, b) => {
        const ad = Date.parse(a.updated_at || a.created_at || "") || 0;
        const bd = Date.parse(b.updated_at || b.created_at || "") || 0;
        return bd - ad;
    });
}

function mainLlmPopulateSessionSelect() {
    if (!elMainLlmSessionSelect) return;
    elMainLlmSessionSelect.innerHTML = "";
    mainLlmSortSessions(mainLlmSessions).forEach((session) => {
        const option = document.createElement("option");
        option.value = session.id;
        const count = Number(session.message_count || 0);
        const title = mainLlmRepairText(session.title || "Yeni Sohbet");
        option.textContent = `${title} (${count})`;
        elMainLlmSessionSelect.appendChild(option);
    });
    if (mainLlmActiveSessionId) {
        elMainLlmSessionSelect.value = mainLlmActiveSessionId;
    }
}

async function mainLlmLoadSessions(includeArchived = false) {
    const url = `/api/llm/chat/sessions?include_archived=${includeArchived ? 1 : 0}&limit=500`;
    const response = await fetch(url);
    const payload = await response.json();
    if (!response.ok || !payload?.ok) {
        throw new Error(payload?.error || "Oturumlar yuklenemedi");
    }
    mainLlmSessions = Array.isArray(payload.sessions) ? payload.sessions : [];
    mainLlmPopulateSessionSelect();
}

async function mainLlmCreateSession(title = "") {
    const response = await fetch("/api/llm/chat/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
    });
    const payload = await response.json();
    if (!response.ok || !payload?.ok || !payload?.session?.id) {
        throw new Error(payload?.error || "Yeni sohbet olusturulamadi");
    }
    mainLlmSessions = [payload.session, ...mainLlmSessions.filter((s) => s.id !== payload.session.id)];
    return payload.session;
}

async function mainLlmLoadSessionMessages(sessionId) {
    const response = await fetch(`/api/llm/chat/sessions/${encodeURIComponent(sessionId)}/messages`);
    const payload = await response.json();
    if (!response.ok || !payload?.ok) {
        throw new Error(payload?.error || "Mesaj gecmisi yuklenemedi");
    }
    const rows = Array.isArray(payload.messages) ? payload.messages : [];
    mainLlmMessages = rows.map((msg) => ({
        role: msg.role,
        content: mainLlmRepairText(msg.content || ""),
        model: mainLlmRepairText(msg.model || ""),
        token_total: msg.token_total ?? null,
        error_type: mainLlmRepairText(msg.error_type || ""),
        created_at: msg.created_at || "",
    }));
    mainLlmRenderMessages();
    mainLlmSaveLocalCache(sessionId);
}

async function mainLlmSetActiveSession(sessionId) {
    mainLlmActiveSessionId = sessionId;
    if (elMainLlmSessionSelect) {
        elMainLlmSessionSelect.value = sessionId;
    }
    try {
        await mainLlmLoadSessionMessages(sessionId);
    } catch (error) {
        mainLlmMessages = mainLlmLoadLocalCache(sessionId);
        mainLlmRenderMessages();
        throw error;
    } finally {
        mainLlmSaveLocalCache(sessionId);
        mainLlmUpdateModeUi();
    }
}

async function mainLlmEnsureActiveSession() {
    await mainLlmLoadSessions(false);
    const savedSession = localStorage.getItem(MAIN_LLM_ACTIVE_SESSION_KEY) || "";
    let targetSession = "";
    if (savedSession && mainLlmSessions.some((s) => s.id === savedSession)) {
        targetSession = savedSession;
    } else if (mainLlmSessions.length > 0) {
        targetSession = mainLlmSortSessions(mainLlmSessions)[0].id;
    } else {
        const created = await mainLlmCreateSession("Yeni Sohbet");
        targetSession = created.id;
    }
    await mainLlmSetActiveSession(targetSession);
}

async function mainLlmCreateAndSwitchSession(title = "") {
    const created = await mainLlmCreateSession(title);
    mainLlmPopulateSessionSelect();
    await mainLlmSetActiveSession(created.id);
}

async function mainLlmArchiveCurrentSession() {
    if (!mainLlmActiveSessionId) return;
    const response = await fetch(
        `/api/llm/chat/sessions/${encodeURIComponent(mainLlmActiveSessionId)}/archive`,
        { method: "POST" }
    );
    const payload = await response.json();
    if (!response.ok || !payload?.ok) {
        throw new Error(payload?.error || "Oturum arsivlenemedi");
    }
    mainLlmSessions = mainLlmSessions.filter((s) => s.id !== mainLlmActiveSessionId);
    if (mainLlmSessions.length === 0) {
        await mainLlmCreateAndSwitchSession("Yeni Sohbet");
    } else {
        const nextSessionId = mainLlmSortSessions(mainLlmSessions)[0].id;
        mainLlmPopulateSessionSelect();
        await mainLlmSetActiveSession(nextSessionId);
    }
}

function mainLlmToggleBusy(isBusy) {
    mainLlmStreaming = isBusy;
    if (elMainLlmInput) elMainLlmInput.disabled = isBusy;
    if (elMainLlmSend) elMainLlmSend.disabled = isBusy;
    if (elMainLlmClear) elMainLlmClear.disabled = isBusy;
    elMainLlmModeRadios.forEach((radio) => {
        radio.disabled = isBusy;
    });
    mainLlmUpdateModeUi();
}

function mainLlmPanelSetOpen(open) {
    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    if (isMobile) {
        document.body.classList.toggle("chat-panel-mobile-open", Boolean(open));
    } else {
        document.body.classList.toggle("chat-panel-collapsed", !open);
    }
    if (elRightChatExpand) {
        elRightChatExpand.style.display = open ? "none" : "";
    }
}

async function mainLlmCheckStatus() {
    if (!elMainLlmBox) return;
    const provider = mainLlmGetProvider();
    const statusUrl = provider === "gemini"
        ? "/api/llm/gemini/status"
        : "/api/llm/openrouter/status";
    try {
        const response = await fetch(statusUrl);
        const data = await response.json();
        mainLlmStatusInfo = data;

        mainLlmManualCandidates.length = 0;
        if (data?.default_model) {
            mainLlmManualCandidates.push(data.default_model);
        }
        if (Array.isArray(data?.fallback_models)) {
            mainLlmManualCandidates.push(...data.fallback_models);
        }
        mainLlmRefreshModelOptions();

        if (response.ok && data.available && data.configured) {
            mainLlmSetStatus("Hazir");
            mainLlmSetActiveModel(data.default_model, data.fallback_models || []);
            if (elMainLlmModelSelect && !elMainLlmModelSelect.value && data.default_model) {
                elMainLlmModelSelect.value = data.default_model;
            }
        } else if (response.ok && data.available && !data.configured) {
            const msg = provider === "gemini"
                ? "GEMINI_API_KEY / GOOGLE_API_KEY tanimli degil"
                : "OPENROUTER_API_KEY tanimli degil";
            mainLlmSetStatus(msg);
            mainLlmSetActiveModel("-", []);
        } else {
            const svc = provider === "gemini" ? "Gemini" : "OpenRouter";
            mainLlmSetStatus(`${svc} servisi hazir degil`);
        }
    } catch (error) {
        mainLlmSetStatus("Sunucuya baglanilamadi");
    }
}

async function mainLlmSendMessage() {
    if (!elMainLlmBox || mainLlmStreaming) return;

    const prompt = mainLlmRepairText(elMainLlmInput?.value || "");
    if (!prompt) return;
    if (!mainLlmActiveSessionId) {
        await mainLlmEnsureActiveSession();
    }

    const isManual = mainLlmGetMode() === "manual";
    const forcedModel = isManual ? mainLlmSelectedManualModel() : "";

    if (isManual && !forcedModel) {
        showToast("Manuel modda model sec veya yaz", "warning");
        return;
    }

    if (elMainLlmInput) elMainLlmInput.value = "";
    mainLlmAddMessage("user", prompt);
    mainLlmMessages.push({ role: "user", content: prompt, model: "", token_total: null });
    mainLlmSaveLocalCache(mainLlmActiveSessionId);

    const assistantBox = mainLlmAddMessage("assistant", "");
    mainLlmToggleBusy(true);
    mainLlmSetStatus("Canli akis devam ediyor...");
    mainLlmCurrentAttemptModel = forcedModel || "";

    const streamPath = mainLlmGetProvider() === "gemini"
        ? "/api/llm/gemini/chat/stream"
        : "/api/llm/openrouter/chat/stream";

    try {
        const response = await fetch(streamPath, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: mainLlmActiveSessionId,
                query: prompt,
                model: forcedModel || undefined,
                use_fallback: !isManual,
            }),
        });

        if (!response.ok || !response.body) {
            let errText = `HTTP ${response.status}`;
            try {
                const payload = await response.json();
                if (payload?.error) errText = payload.error;
            } catch (_) {
                // ignore
            }
            if (assistantBox) assistantBox.textContent = `[Hata] ${mainLlmRepairText(errText)}`;
            mainLlmSetStatus("Istek hatasi");
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        let output = "";
        let usageMeta = "";
        let usageModel = "";
        let usageToken = null;
        let streamError = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;

                let payload = null;
                try {
                    payload = JSON.parse(trimmed);
                } catch (_) {
                    continue;
                }

                if (payload.type === "token") {
                    const tokenText = mainLlmRepairText(payload.text || "");
                    output += tokenText;
                    if (assistantBox) assistantBox.textContent = output;
                    if (elMainLlmChatLog) {
                        elMainLlmChatLog.scrollTop = elMainLlmChatLog.scrollHeight;
                    }
                } else if (payload.type === "meta") {
                    if (payload.model) {
                        mainLlmCurrentAttemptModel = mainLlmRepairText(payload.model);
                        mainLlmSetActiveModel(payload.model, payload.tried_models || []);
                    }

                    if (payload.phase === "start") {
                        mainLlmSetStatus(`Model deneniyor: ${mainLlmRepairText(payload.model || "")}`);
                        if (mainLlmGetMode() === "auto") {
                            mainLlmAppendMeta(assistantBox, `Deneniyor: ${mainLlmRepairText(payload.model || "")}`);
                        }
                    } else if (payload.phase === "fallback") {
                        mainLlmSetStatus(`Fallback: ${mainLlmRepairText(payload.model || "")} basarisiz`);
                        mainLlmAppendMeta(
                            assistantBox,
                            `Basarisiz: ${mainLlmRepairText(payload.model || "")} | ${mainLlmRepairText(payload.error || "hata")}`
                        );
                    } else if (payload.phase === "success") {
                        mainLlmSetStatus("Hazir");
                        if (mainLlmGetMode() === "auto") {
                            mainLlmAppendMeta(assistantBox, `Basarili model: ${mainLlmRepairText(payload.model || "")}`);
                        }
                    }

                    const usage = payload.usage || {};
                    usageModel = mainLlmRepairText(payload.model || usageModel || "-");
                    usageToken = usage.total_tokens ?? usageToken;
                    usageMeta = `model: ${usageModel || "-"} | token: ${usageToken ?? "-"}`;
                } else if (payload.type === "error") {
                    streamError = mainLlmRepairText(payload.error || "Bilinmeyen hata");
                    if (assistantBox) {
                        assistantBox.textContent = `[Hata] ${streamError}`;
                    }
                    const kind = mainLlmClassifyError(streamError);
                    if (kind === "limit") {
                        mainLlmSetStatus("Limit hatasi (429)");
                    } else if (kind === "credit") {
                        mainLlmSetStatus("Kredi hatasi (402)");
                    } else if (kind === "incompat") {
                        mainLlmSetStatus("Model endpoint uyumsuz (400)");
                    } else if (kind === "privacy") {
                        mainLlmSetStatus("Privacy/Guardrail kisiti (404)");
                    } else {
                        mainLlmSetStatus("Akis hatasi");
                    }
                }
            }
        }

        const finalOutput = mainLlmRepairText(output);
        const finalAssistantText = finalOutput || (streamError ? `[Hata] ${streamError}` : "[Bos yanit]");
        if (assistantBox) {
            assistantBox.textContent = finalAssistantText;
        }
        mainLlmMessages.push({
            role: "assistant",
            content: finalAssistantText,
            model: usageModel || mainLlmCurrentAttemptModel || "",
            token_total: usageToken,
            error_type: streamError ? mainLlmClassifyError(streamError) : "",
        });
        mainLlmSaveLocalCache(mainLlmActiveSessionId);

        if (assistantBox && usageMeta) {
            mainLlmAppendMeta(assistantBox, usageMeta);
        }

        mainLlmSetStatus("Hazir");
        await mainLlmLoadSessions(false);
        mainLlmPopulateSessionSelect();
    } catch (error) {
        if (assistantBox) {
            assistantBox.textContent = `[Hata] ${mainLlmRepairText(error.message || error)}`;
        }
        mainLlmSetStatus("Baglanti hatasi");
    } finally {
        mainLlmToggleBusy(false);
        if (elMainLlmInput) elMainLlmInput.focus();
    }
}

function initMainLlmChat() {
    if (!elMainLlmBox) return;

    elMainLlmModeRadios.forEach((radio) => {
        radio.addEventListener("change", mainLlmUpdateModeUi);
    });

    if (elMainLlmCategory) {
        elMainLlmCategory.addEventListener("change", mainLlmRefreshModelOptions);
    }
    if (elMainLlmSend) {
        elMainLlmSend.addEventListener("click", mainLlmSendMessage);
    }
    if (elMainLlmClear) {
        elMainLlmClear.addEventListener("click", async () => {
            try {
                await mainLlmCreateAndSwitchSession("Yeni Sohbet");
                mainLlmSetStatus("Yeni sohbet acildi");
            } catch (error) {
                showToast(mainLlmRepairText(error.message || "Yeni sohbet acilamadi"), "error");
            }
        });
    }
    if (elMainLlmInput) {
        elMainLlmInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                mainLlmSendMessage();
            }
        });
    }

    elMainLlmProviderRadios.forEach((radio) => {
        radio.addEventListener("change", () => {
            if (elMainLlmModelSelect) elMainLlmModelSelect.value = "";
            if (elMainLlmCustomModel) elMainLlmCustomModel.value = "";
            mainLlmCheckStatus();
        });
    });

    if (elMainLlmSessionSelect) {
        elMainLlmSessionSelect.addEventListener("change", async () => {
            const sessionId = elMainLlmSessionSelect.value;
            if (!sessionId || sessionId === mainLlmActiveSessionId) return;
            try {
                await mainLlmSetActiveSession(sessionId);
                mainLlmSetStatus("Oturum degisti");
            } catch (error) {
                showToast(mainLlmRepairText(error.message || "Oturum degistirilemedi"), "error");
            }
        });
    }

    if (elMainLlmNewSession) {
        elMainLlmNewSession.addEventListener("click", async () => {
            try {
                await mainLlmCreateAndSwitchSession("Yeni Sohbet");
                mainLlmSetStatus("Yeni sohbet olusturuldu");
            } catch (error) {
                showToast(mainLlmRepairText(error.message || "Yeni sohbet olusturulamadi"), "error");
            }
        });
    }

    if (elMainLlmArchiveSession) {
        elMainLlmArchiveSession.addEventListener("click", async () => {
            try {
                await mainLlmArchiveCurrentSession();
                mainLlmSetStatus("Oturum arsivlendi");
            } catch (error) {
                showToast(mainLlmRepairText(error.message || "Oturum arsivlenemedi"), "error");
            }
        });
    }

    if (elRightChatCollapse) {
        elRightChatCollapse.addEventListener("click", () => mainLlmPanelSetOpen(false));
    }
    if (elRightChatExpand) {
        elRightChatExpand.addEventListener("click", () => mainLlmPanelSetOpen(true));
    }

    if (window.matchMedia("(max-width: 768px)").matches) {
        mainLlmPanelSetOpen(false);
    } else {
        mainLlmPanelSetOpen(true);
    }

    mainLlmUpdateModeUi();
    mainLlmCheckStatus();
    mainLlmEnsureActiveSession().catch((error) => {
        mainLlmMessages = [];
        mainLlmRenderMessages();
        mainLlmSetStatus("Sohbet oturumu yuklenemedi");
        showToast(mainLlmRepairText(error.message || "Sohbet oturumu yuklenemedi"), "error");
    });
}
// ========== ALTERNATIVE ROUTES ==========

/**
 * Alternatif rotalarÃ„Â± gÃƒÂ¶sterir
 */
async function showAlternativeRoutes() {
    if (selectedPoints.length < 2) {
        showToast("En az 2 nokta seÃƒÂ§melisiniz!", "error");
        return;
    }

    showLoading("Alternatif rotalar hesaplanÃ„Â±yor...");

    const optimize = false; // TSP optimizasyonu devre dÃ„Â±Ã…Å¸Ã„Â±

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
        showToast(`${data.alternatives.length} alternatif rota bulundu! \u{2728}`, "success");

    } catch (error) {
        console.error("Alternatif rota hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * Alternatif rotalarÃ„Â± listeler
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
                        <span class="stat-icon">\u{1F4CF}</span>
                        <span class="stat-text">${alt.distance_km} km</span>
                    </div>
                    <div class="alternative-stat">
                        <span class="stat-icon">\u{23F1}\u{FE0F}</span>
                        <span class="stat-text">${alt.duration_minutes} dk</span>
                    </div>
                </div>
                <button class="btn-select-route"
                    data-action-select-alt
                    data-type="${escapeHtml(alt.type)}"
                    data-coords='${JSON.stringify(alt.route_coords)}'>
                    Bu RotayÃ„Â± SeÃƒÂ§
                </button>
            </div>
        `;
    });

    elAlternativesList.innerHTML = html;

    // Panele scroll
    elAlternativesPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/**
 * SeÃƒÂ§ilen alternatif rotayÃ„Â± haritada gÃƒÂ¶sterir
 */
function selectAlternativeRoute(routeType, routeCoords) {
    const prevRouteData = currentRouteData ? { ...currentRouteData } : null;
    clearRoute();

    // Rota renklerini belirle - basit sistem
    const routeColors = {
        route_1: "#6c5ce7",     // Mor
        route_2: "#00cec9",     // Turkuaz
        route_3: "#feca57"      // SarÃ„Â±
    };

    // Eski tip compatibility (shortest/fastest/balanced)
    if (routeType === "shortest") routeType = "route_1";
    else if (routeType === "fastest") routeType = "route_2";
    else if (routeType === "balanced") routeType = "route_3";

    const color = routeColors[routeType] || "#6c5ce7";

    // RotayÃ„Â± ÃƒÂ§iz
    routePolyline = L.polyline(routeCoords, {
        color: color,
        weight: 5,
        opacity: 0.85,
        smoothFactor: 1,
    }).addTo(map);

<<<<<<< Updated upstream
    // Glow efekti - tracking listesine ekle
    const glow = L.polyline(routeCoords, {
=======
    // Glow efekti
    const glowLine = L.polyline(routeCoords, {
>>>>>>> Stashed changes
        color: color,
        weight: 10,
        opacity: 0.2,
        smoothFactor: 1,
    }).addTo(map);
<<<<<<< Updated upstream
    routeGlowPolylines.push(glow);
=======
    routeGlowPolylines.push(glowLine);

    currentRouteData = {
        ...(prevRouteData || {}),
        route_coords: routeCoords,
        route_type: routeType,
    };
>>>>>>> Stashed changes

    // HaritayÃ„Â± rotaya sÃ„Â±Ã„Å¸dÃ„Â±r
    map.fitBounds(routePolyline.getBounds(), { padding: [60, 60] });

    // Active sÃ„Â±nÃ„Â±fÃ„Â±nÃ„Â± gÃƒÂ¼ncelle
    document.querySelectorAll(".alternative-card").forEach(card => {
        card.classList.remove("active");
    });
    document.querySelector(`[data-route-type="${routeType}"]`).classList.add("active");

    // currentRouteData'yÃ„Â± seÃƒÂ§ilen alternatif rota ile gÃƒÂ¼ncelle
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

    // ButonlarÃ„Â± gÃƒÂ¼ncelle
    updateButtons();

    const routeNames = {
        route_1: "Rota 1",
        route_2: "Rota 2",
        route_3: "Rota 3"
    };

    showToast(`${routeNames[routeType]} seÃƒÂ§ildi! \u{2705}`, "success");
}


// ========== SAVE ROUTE ==========

/**
 * Rota kaydetme modalÃ„Â±nÃ„Â± aÃƒÂ§ar
 */
function openSaveRouteModal() {
    if (!currentRouteData) {
        showToast("Ãƒâ€“nce bir rota hesaplayÃ„Â±n!", "error");
        return;
    }

    elSaveRouteModal.style.display = "flex";
    document.getElementById("routeName").focus();
}

/**
 * Rota kaydetme modalÃ„Â±nÃ„Â± kapatÃ„Â±r
 */
function closeSaveRouteModal() {
    elSaveRouteModal.style.display = "none";
    // Formu temizle
    document.getElementById("routeName").value = "";
    document.getElementById("routeDescription").value = "";
    document.getElementById("routeTags").value = "";
}

/**
 * RotayÃ„Â± kaydeder
 */
async function confirmSaveRoute() {
    const name = document.getElementById("routeName").value.trim();
    const description = document.getElementById("routeDescription").value.trim();
    const tagsInput = document.getElementById("routeTags").value.trim();

    if (!name) {
        showToast("Rota adÃ„Â± gerekli!", "error");
        return;
    }

    if (!currentRouteData) {
        showToast("Kaydedilecek rota bulunamadÃ„Â±!", "error");
        return;
    }

    // Etiketleri ayÃ„Â±r
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
            throw new Error(data.error || "Kaydetme hatasÃ„Â±");
        }

        closeSaveRouteModal();
        loadSavedRoutes(); // Listeyi yenile
        showToast(`"${name}" rotasÃ„Â± kaydedildi! \u{2705}`, "success");

    } catch (error) {
        console.error("Rota kaydetme hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * KaydedilmiÃ…Å¸ rotalarÃ„Â± yÃƒÂ¼kler
 */
async function loadSavedRoutes() {
    try {
        const response = await fetch(`${API_BASE}/routes?sort_by=created_at&limit=10`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Rotalar yÃƒÂ¼klenemedi");
        }

        displaySavedRoutes(data.routes);

    } catch (error) {
        console.error("Rota yÃƒÂ¼kleme hatasÃ„Â±:", error);
        elSavedRoutesList.innerHTML = `<div class="empty-state"><p>Rotalar yÃƒÂ¼klenemedi</p></div>`;
    }
}

/**
 * KaydedilmiÃ…Å¸ rotalarÃ„Â± listeler
 */
function displaySavedRoutes(routes) {
    if (!routes || routes.length === 0) {
        elSavedRoutesList.innerHTML = `<div class="empty-state"><p>HenÃƒÂ¼z kaydedilmiÃ…Å¸ rota yok</p></div>`;
        return;
    }

    let html = "";

    routes.forEach(route => {
        const date = new Date(route.created_at).toLocaleDateString("tr-TR", {
            day: "numeric",
            month: "short"
        });

        const favoriteIcon = route.favorite ? "\u{2B50}" : "\u{2606}";

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
                    <span>\u{1F4CF} ${route.distance_km} km</span>
                    <span>\u{23F1}\u{FE0F} ${route.duration_minutes} dk</span>
                    <span>\u{1F4C5} ${date}</span>
                </div>
                ${route.tags && route.tags.length > 0 ? `
                    <div class="saved-route-tags">
                        ${route.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
                    </div>
                ` : ""}
                <div class="saved-route-actions">
                    <button class="btn-load-route" data-action-load-route data-id="${escapeHtml(route.id)}">
                        \u{1F4E5} YÃƒÂ¼kle
                    </button>
                    <button class="btn-delete-route" data-action-delete-route data-id="${escapeHtml(route.id)}" title="Sil">
                        \u{1F5D1}\u{FE0F}
                    </button>
                </div>
            </div>
        `;
    });

    elSavedRoutesList.innerHTML = html;
}

/**
 * KaydedilmiÃ…Å¸ rotayÃ„Â± yÃƒÂ¼kler
 */
async function loadRoute(routeId) {
    showLoading("Rota yÃƒÂ¼kleniyor...");

    try {
        const response = await fetch(`${API_BASE}/routes/${routeId}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Rota yÃƒÂ¼klenemedi");
        }

        const route = data.route;

        // Mevcut noktalarÃ„Â± temizle
        clearAllPoints();

        // RotanÃ„Â±n noktalarÃ„Â±nÃ„Â± ekle
        route.points.forEach(([lat, lon]) => {
            addPoint(lat, lon);
        });

        // RotayÃ„Â± ÃƒÂ§iz
        currentRouteData = {
            route_coords: route.route_coords,
            total_distance_km: route.distance_km,
            estimated_walk_minutes: route.duration_minutes,
            route_type: route.route_type
        };

        drawRoute(currentRouteData);
        showRouteInfo(currentRouteData);
        updateButtons();  // Buton durumlarÃ„Â±nÃ„Â± gÃƒÂ¼ncelle

        showToast(`"${route.name}" rotasÃ„Â± yÃƒÂ¼klendi! \u{2705}`, "success");

    } catch (error) {
        console.error("Rota yÃƒÂ¼kleme hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * RotayÃ„Â± favorilere ekler/ÃƒÂ§Ã„Â±karÃ„Â±r
 */
async function toggleRouteFavorite(routeId) {
    try {
        const response = await fetch(`${API_BASE}/routes/${routeId}/favorite`, {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Favori iÃ…Å¸lemi baÃ…Å¸arÃ„Â±sÃ„Â±z");
        }

        loadSavedRoutes(); // Listeyi yenile

        const message = data.is_favorite ? "Favorilere eklendi \u{2B50}" : "Favorilerden ÃƒÂ§Ã„Â±karÃ„Â±ldÃ„Â±";
        showToast(message, "success");

    } catch (error) {
        console.error("Favori iÃ…Å¸lemi hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    }
}

/**
 * RotayÃ„Â± siler
 */
async function deleteRoute(routeId) {
    if (!confirm("Bu rotayÃ„Â± silmek istediÃ„Å¸inizden emin misiniz?")) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/routes/${routeId}`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Silme iÃ…Å¸lemi baÃ…Å¸arÃ„Â±sÃ„Â±z");
        }

        loadSavedRoutes(); // Listeyi yenile
        showToast("Rota silindi \u{1F5D1}\u{FE0F}", "success");

    } catch (error) {
        console.error("Rota silme hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    }
}


// ========== TIME PLANNING ==========

/**
 * Zaman planlama panelini gÃƒÂ¶sterir
 */
function showTimelinePlanner() {
    if (!currentRouteData || selectedPoints.length < 2) {
        showToast("Ãƒâ€“nce bir rota hesaplayÃ„Â±n!", "error");
        return;
    }

    elTimelinePanel.style.display = "block";
    elTimelinePanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/**
 * Zaman ÃƒÂ§izelgesi oluÃ…Å¸turur
 */
async function generateTimeline() {
    if (!currentRouteData) {
        showToast("Ãƒâ€“nce bir rota hesaplayÃ„Â±n!", "error");
        return;
    }

    const startTime = document.getElementById("startTime").value;
    const visitDuration = parseInt(document.getElementById("visitDuration").value);

    if (!startTime) {
        showToast("BaÃ…Å¸langÃ„Â±ÃƒÂ§ saati seÃƒÂ§in!", "error");
        return;
    }

    showLoading("Zaman ÃƒÂ§izelgesi oluÃ…Å¸turuluyor...");

    try {
        // Noktalar arasÃ„Â± mesafeleri hesapla
        const segmentDistances = calculateSegmentDistances();

        // Nokta bilgilerini hazÃ„Â±rla
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
            throw new Error(data.error || "Zaman ÃƒÂ§izelgesi oluÃ…Å¸turulamadÃ„Â±");
        }

        displayTimeline(data);
        showToast("Zaman ÃƒÂ§izelgesi oluÃ…Å¸turuldu! \u{2705}", "success");

    } catch (error) {
        console.error("Timeline hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * Segment mesafelerini hesaplar (basitleÃ…Å¸tirilmiÃ…Å¸)
 */
function calculateSegmentDistances() {
    if (!currentRouteData || !currentRouteData.total_distance_km) {
        return [];
    }

    // Basit yaklaÃ…Å¸Ã„Â±m: toplam mesafeyi nokta sayÃ„Â±sÃ„Â±na bÃƒÂ¶l
    const numSegments = selectedPoints.length - 1;
    const avgDistance = currentRouteData.total_distance_km / numSegments;

    return Array(numSegments).fill(avgDistance);
}

/**
 * Zaman ÃƒÂ§izelgesini gÃƒÂ¶rÃƒÂ¼ntÃƒÂ¼ler
 */
function displayTimeline(timeline) {
    elTimelineDisplay.style.display = "block";

    const totalHours = Math.floor(timeline.total_duration_minutes / 60);
    const totalMins = timeline.total_duration_minutes % 60;

    let html = `
        <div class="timeline-summary">
            <div class="timeline-stat">
                <span class="timeline-stat-label">BaÃ…Å¸langÃ„Â±ÃƒÂ§</span>
                <span class="timeline-stat-value">\u{1F553} ${timeline.start_time}</span>
            </div>
            <div class="timeline-stat">
                <span class="timeline-stat-label">BitiÃ…Å¸</span>
                <span class="timeline-stat-value">\u{1F553} ${timeline.end_time}</span>
            </div>
            <div class="timeline-stat">
                <span class="timeline-stat-label">Toplam SÃƒÂ¼re</span>
                <span class="timeline-stat-value">\u{23F1}\u{FE0F} ${totalHours}s ${totalMins}dk</span>
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
                            <span class="timeline-time-label">VarÃ„Â±Ã…Å¸:</span>
                            <span class="timeline-time-value">${item.arrival_time}</span>
                        </span>
                        <span class="timeline-time">
                            <span class="timeline-time-label">AyrÃ„Â±lÃ„Â±Ã…Å¸:</span>
                            <span class="timeline-time-value">${item.departure_time}</span>
                        </span>
                    </div>
                    <div class="timeline-duration">
                        \u{23F1}\u{FE0F} ${item.visit_duration_minutes} dakika kalÃ„Â±Ã…Å¸
                    </div>
                    ${item.weather ? `
                    <div class="timeline-weather">
                        <span class="tl-weather-emoji">${item.weather.weather_emoji || '\u{2601}\u{FE0F}'}</span>
                        <span class="tl-weather-temp">${item.weather.temperature != null ? Math.round(item.weather.temperature) + 'Ã‚Â°C' : ''}</span>
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
                            \u{1F6B6} \u{2192} ${item.next_travel_time_minutes} dakika yÃƒÂ¼rÃƒÂ¼yÃƒÂ¼Ã…Å¸
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

// Ã„Â°kon haritasÃ„Â± Ã¢â‚¬â€ KayÃ„Â±tlÃ„Â± yerler iÃƒÂ§in emoji eÃ…Å¸lemesi
const locationEmojiMap = {
    marker: "\u{1F4CD}",
    home: "\u{1F3E0}",
    work: "\u{1F4BC}",
    school: "\u{1F3EB}",
    gym: "\u{1F3CB}\u{FE0F}",
    market: "\u{1F6D2}",
    star: "\u{2B50}",
    coffee: "\u{2615}",
    restaurant: "\u{1F37D}\u{FE0F}",
    heart: "\u{2764}\u{FE0F}",
    hospital: "\u{1F3E5}",
    park: "\u{1F333}",
    museum: "\u{1F3DB}\u{FE0F}",
    plane: "\u{2708}\u{FE0F}",
    car: "\u{1F697}",
    bike: "\u{1F6B2}",
    beach: "\u{1F3D6}\u{FE0F}",
    mountain: "\u{26F0}\u{FE0F}",
    bank: "\u{1F3E6}",
    gas: "\u{26FD}",
    pharmacy: "\u{1F48A}"
};

/**
 * Konum kaydetme modalÃ„Â±nÃ„Â± aÃƒÂ§ar
 */
window.openSaveLocationModal = function (lat, lon, defaultName = "") {
    elLocationLat.value = lat;
    elLocationLon.value = lon;
    elLocationName.value = defaultName;
    elLocationAddress.value = ""; // Reverse geocoding ile de doldurulabilir (Ã…Å¸imdilik boÃ…Å¸ kalsÃ„Â±n)

    // Default marker'Ã„Â± sÃ„Â±fÃ„Â±rla
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
        showToast("Konum adÃ„Â± gerekli!", "error");
        return;
    }

    if (isNaN(lat) || isNaN(lon)) {
        showToast("GeÃƒÂ§ersiz koordinatlar!", "error");
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
            throw new Error(data.error || "Kaydetme hatasÃ„Â±");
        }

        closeSaveLocationModal();
        loadSavedLocations(); // Listeyi yenile
        showToast(`"${name}" konumu kaydedildi! \u{2705}`, "success");

    } catch (error) {
        console.error("Konum kaydetme hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * Sunucudan kayÃ„Â±tlÃ„Â± konumlarÃ„Â± getir ve ekrana ÃƒÂ§iz
 */
async function loadSavedLocations() {
    try {
        const response = await fetch(`${API_BASE}/locations?limit=20&sort_by=favorite`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Konumlar yÃƒÂ¼klenemedi");
        }

        displaySavedLocationsSidebar(data.locations);

        if (showSavedLocationsOnMap) {
            drawSavedLocationsOnMap(data.locations);
        }

    } catch (error) {
        console.error("Konum yÃƒÂ¼kleme hatasÃ„Â±:", error);
        elSavedLocationsList.innerHTML = `<div class="empty-state"><p>Yer imleri yÃƒÂ¼klenemedi</p></div>`;
    }
}

function displaySavedLocationsSidebar(locations) {
    if (!locations || locations.length === 0) {
        elSavedLocationsList.innerHTML = `<div class="empty-state"><p>HenÃƒÂ¼z kayÃ„Â±tlÃ„Â± yeriniz yok</p></div>`;
        return;
    }

    let html = "";
    locations.forEach(loc => {
        const emoji = locationEmojiMap[loc.icon_type] || "\u{1F4CD}";
        const favoriteIcon = loc.favorite ? "?" : "?";

        html += `
            <div class="saved-location-card"
                 data-zoom-location
                 data-lat="${loc.lat}"
                 data-lon="${loc.lon}"
                 data-name="${encodeURIComponent(loc.name)}">
                <div class="saved-location-icon">${emoji}</div>
                <div class="saved-location-info">
                    <h3 class="saved-location-name">${escapeHtml(loc.name)}</h3>
                    <p class="saved-location-address">KullanÃ„Â±m: ${loc.times_used || 0}</p>
                </div>
                <div class="saved-location-actions" data-stop-propagation>
                    <button class="ic-btn ic-btn-favorite" data-action-toggle-loc-fav data-id="${escapeHtml(loc.id)}" title="Favori">
                        ${favoriteIcon}
                    </button>
                    <button class="ic-btn ic-btn-route" data-action-add-point data-lat="${loc.lat}" data-lon="${loc.lon}" title="Rotaya Ekle">
                        +
                    </button>
                    <button class="ic-btn ic-btn-delete" data-action-delete-loc data-id="${escapeHtml(loc.id)}" title="Sil">
                        ?
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
 * KayÃ„Â±tlÃ„Â± konumun favori durumunu deÃ„Å¸iÃ…Å¸tirir
 */
async function toggleLocationFavorite(locationId) {
    try {
        const response = await fetch(`${API_BASE}/locations/${locationId}/favorite`, {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Favori iÃ…Å¸lemi baÃ…Å¸arÃ„Â±sÃ„Â±z");
        }

        loadSavedLocations();
        showToast(data.is_favorite ? "Favorilere eklendi \u{2B50}" : "Favorilerden ÃƒÂ§Ã„Â±karÃ„Â±ldÃ„Â±", "success");

    } catch (error) {
        console.error("Favori iÃ…Å¸lemi hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    }
}

async function deleteSavedLocation(locationId) {
    if (!confirm("Bu konumu silmek istediÃ„Å¸inizden emin misiniz?")) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/locations/${locationId}`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Silme iÃ…Å¸lemi baÃ…Å¸arÃ„Â±sÃ„Â±z");
        }

        loadSavedLocations(); // Backendi ve haritayÃ„Â± yenile
        showToast("Konum silindi \u{1F5D1}\u{FE0F}", "success");

    } catch (error) {
        console.error("Konum silme hatasÃ„Â±:", error);
        showToast(`Hata: ${error.message}`, "error");
    }
}

/**
 * Haritadaki markerlarÃ„Â± ÃƒÂ§izer
 */
function drawSavedLocationsOnMap(locations) {
    clearSavedLocationMarkers();

    locations.forEach(loc => {
        const emoji = locationEmojiMap[loc.icon_type] || "\u{1F4CD}";

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
        // Ã„Â°konu aktif gÃƒÂ¶z yap
        elIconLocationVisible.innerHTML = `
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
        `;
        elIconLocationVisible.style.stroke = "currentColor";
        loadSavedLocations(); // Yeniden yÃƒÂ¼kleyip ÃƒÂ§izsin
    } else {
        // Ã„Â°konu kapalÃ„Â± gÃƒÂ¶z yap
        elIconLocationVisible.innerHTML = `
            <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
        `;
        elIconLocationVisible.style.stroke = "var(--text-muted)";
        clearSavedLocationMarkers();
    }
}

<<<<<<< Updated upstream
// ========== EVENT DELEGATION - XSS GÃƒÂ¼venlik DÃƒÂ¼zeltmeleri ==========
// TÃƒÂ¼m inline onclick handlers yerine tek bir event listener kullanÃ„Â±lÃ„Â±r
// Bu, XSS saldÃ„Â±rÃ„Â±larÃ„Â±nÃ„Â± ÃƒÂ¶nler ve daha iyi performans saÃ„Å¸lar
=======
        } else if (seg.mode === "bus") {
            const stopCoords = (Array.isArray(seg.stop_coords) && seg.stop_coords.length >= 2)
                ? seg.stop_coords
                : seg.coords;
            const stopLatLngs = stopCoords.map(c => [c[0], c[1]]);

            // ---- OTOBUS SEGMENTI ----
>>>>>>> Stashed changes

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

<<<<<<< Updated upstream
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
=======
            // 3. Ara durak noktalari (kucuk beyaz daireler)
            const stride = stopLatLngs.length > 60 ? 3 : 1;
            stopLatLngs.forEach((coord, i) => {
                const isEndpoint = (i === 0 || i === stopLatLngs.length - 1);
                if (!isEndpoint) {
                    if (stride > 1 && i % stride !== 0) {
                        return;
                    }
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
            const boardCoord = stopLatLngs[0] || latlngs[0];
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
            const alightCoord = stopLatLngs[stopLatLngs.length - 1] || latlngs[latlngs.length - 1];
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
>>>>>>> Stashed changes

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
        document.getElementById("weatherWidgetEmoji").textContent = cur.weather_emoji || "\u{2601}\u{FE0F}";
        document.getElementById("weatherWidgetTemp").textContent = `${Math.round(cur.temperature)}Ã‚Â°C`;
        document.getElementById("weatherWidgetDesc").textContent = cur.weather_tr || cur.weather_description || "Ã¢â‚¬â€";

        // GÃƒÂ¶ster ve 5 sn sonra otomatik kaybet
        el.style.display = "block";
        el.classList.remove("auto-hide");
        if (_weatherHideTimer) clearTimeout(_weatherHideTimer);
        _weatherHideTimer = setTimeout(() => {
            el.classList.add("auto-hide");
        }, 5000);
    } catch (e) {
        // fail silently Ã¢â‚¬â€ widget gÃƒÂ¶sterilmez
    }
}

function initWeatherWidget() {
    // Sayfa aÃƒÂ§Ã„Â±ldÃ„Â±Ã„Å¸Ã„Â±nda harita merkezinden baÃ…Å¸la
    const center = map.getCenter();
    fetchWeatherWidget(center.lat, center.lng);
    // Nokta eklenmediÃ„Å¸i sÃƒÂ¼rece harita hareketiyle gÃƒÂ¼ncelleme yapma
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

// KullanÃ„Â±cÃ„Â± startTime alanÃ„Â±nÃ„Â± bilinÃƒÂ§li deÃ„Å¸iÃ…Å¸tirdiyse forecast modunu aÃƒÂ§
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

        // KullanÃ„Â±cÃ„Â± ÃƒÂ¶zel saat seÃƒÂ§tiyse, route-weather iÃƒÂ§in forecast modunu aÃƒÂ§
        const startTimeInput = document.getElementById("startTime");
        const startTimeValue = (startTimeInput?.value || "").trim();

        let hasTime = _weatherUseCustomStartTime && /^\d{2}:\d{2}$/.test(startTimeValue);

        // GeÃƒÂ§miÃ…Å¸ saat seÃƒÂ§ildiyse (bugÃƒÂ¼n iÃƒÂ§in), anlÃ„Â±k moda dÃƒÂ¼Ã…Å¸
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
        // sessiz hata Ã¢â‚¬â€œ banner olmadan devam
    }
}

function showWeatherBanner(routeWeather, criticalAdvice = null) {
    // TÃƒÂ¼m noktalardan tavsiye topla, tekrar edenleri filtrele
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

    const iconMap = { info: "\u{2139}\u{FE0F}", warning: "\u{26A0}\u{FE0F}", danger: "\u{1F6A8}" };
    const titleMap = { info: "Hava Durumu Bilgisi", warning: "Hava Durumu UyarÃ„Â±sÃ„Â±", danger: "Tehlikeli Hava KoÃ…Å¸ullarÃ„Â±" };

    let html = `
        <div class="weather-banner-header">
            <span class="weather-banner-icon">${iconMap[topLevel]}</span>
            <span class="weather-banner-title">${titleMap[topLevel]}</span>
            <button class="weather-banner-close" onclick="hideWeatherBanner()">\u{2715}</button>
        </div>
    `;

    if (criticalAdvice) {
        html += `
        <div class="weather-banner-critical">
            <span class="wbc-icon">\u{26A0}\u{FE0F}</span>
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


// ========== TÃƒÅ“RKÃ„Â°YE VERÃ„Â°SÃ„Â° YÃƒâ€“NETÃ„Â°MÃ„Â° ==========
let turkiyeData = null;

// TÃƒÂ¼rkiye verisini yÃƒÂ¼kle
async function loadTurkiyeData() {
    try {
        const response = await fetch('data/turkiye-data.json');
        turkiyeData = await response.json();
        initializeRegionDropdown();
    } catch (error) {
        console.error('TÃƒÂ¼rkiye verisi yÃƒÂ¼klenemedi:', error);
        showToast('BÃƒÂ¶lge verileri yÃƒÂ¼klenemedi', 'error');
    }
}

// BÃƒÂ¶lge dropdown'Ã„Â±nÃ„Â± doldur
function initializeRegionDropdown() {
    if (!turkiyeData) return;
    
    elRegionSelect.innerHTML = '<option value="">BÃƒÂ¶lge SeÃƒÂ§in</option>';
    Object.keys(turkiyeData).forEach(region => {
        const option = document.createElement('option');
        option.value = region;
        option.textContent = region;
        elRegionSelect.appendChild(option);
    });
}

// BÃƒÂ¶lge seÃƒÂ§ildiÃ„Å¸inde illeri doldur
elRegionSelect.addEventListener('change', function() {
    const selectedRegion = this.value;
    
    if (!selectedRegion) {
        elProvinceSelect.disabled = true;
        elProvinceSelect.innerHTML = '<option value="">Ãƒâ€“nce BÃƒÂ¶lge SeÃƒÂ§in</option>';
        elDistrictSelect.disabled = true;
        elDistrictSelect.innerHTML = '<option value="">Ãƒâ€“nce Ã„Â°l SeÃƒÂ§in</option>';
        return;
    }
    
    const provinces = turkiyeData[selectedRegion];
    elProvinceSelect.innerHTML = '<option value="">Ã„Â°l SeÃƒÂ§in</option>';
    
    Object.keys(provinces).forEach(province => {
        const option = document.createElement('option');
        option.value = province;
        option.textContent = province;
        elProvinceSelect.appendChild(option);
    });
    
    elProvinceSelect.disabled = false;
    elDistrictSelect.disabled = true;
    elDistrictSelect.innerHTML = '<option value="">Ãƒâ€“nce Ã„Â°l SeÃƒÂ§in</option>';
});

// Ã„Â°l seÃƒÂ§ildiÃ„Å¸inde ilÃƒÂ§eleri doldur
elProvinceSelect.addEventListener('change', function() {
    const selectedRegion = elRegionSelect.value;
    const selectedProvince = this.value;
    
    if (!selectedProvince) {
        elDistrictSelect.disabled = true;
        elDistrictSelect.innerHTML = '<option value="">Ãƒâ€“nce Ã„Â°l SeÃƒÂ§in</option>';
        return;
    }
    
    const districts = turkiyeData[selectedRegion][selectedProvince];
    elDistrictSelect.innerHTML = '<option value="">Ã„Â°lÃƒÂ§e SeÃƒÂ§in (Opsiyonel)</option>';
    
    districts.forEach(district => {
        const option = document.createElement('option');
        option.value = district;
        option.textContent = district;
        elDistrictSelect.appendChild(option);
    });
    
    elDistrictSelect.disabled = false;
});

// Ã„Â°lÃƒÂ§e seÃƒÂ§ildiÃ„Å¸inde haritayÃ„Â± oraya odakla
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
                showToast(`${selectedDistrict}, ${selectedProvince} konumuna odaklandÃ„Â±`, 'success');
            }
        } catch (error) {
            console.error('Konum bulunamadÃ„Â±:', error);
        }
    }
});

// Sayfa yÃƒÂ¼klendiÃ„Å¸inde TÃƒÂ¼rkiye verisini yÃƒÂ¼kle

// ========== TURN-BY-TURN & TTS ==========
const elTurnByTurnPanel = document.getElementById('turnByTurnPanel');
const elTurnByTurnList = document.getElementById('turnByTurnList');
const elBtnStartVoice = document.getElementById('btnStartVoice');
const elBtnStopVoice = document.getElementById('btnStopVoice');

let ttsQueue = [];
let ttsUtterance = null;
let ttsPlaying = false;

async function fetchRouteSteps() {
    if (!selectedPoints || selectedPoints.length < 2) return;
    try {
        const resp = await fetch(`${API_BASE}/get-route-steps`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ points: selectedPoints, optimize: false })
        });
        if (!resp.ok) return;
        const data = await resp.json();
        if (data && data.steps && data.steps.length > 0) {
            displayRouteSteps(data.steps);
        } else {
            if (elTurnByTurnPanel) elTurnByTurnPanel.style.display = 'none';
        }
    } catch (e) {
        // silent
    }
}

function displayRouteSteps(steps) {
    if (!elTurnByTurnPanel || !elTurnByTurnList) return;
    elTurnByTurnPanel.style.display = 'block';
    elTurnByTurnList.innerHTML = steps.map((s,i)=>`<div class="turn-step"><strong>${i+1}.</strong> ${escapeHtml(s.instruction)} <span class="muted">(${s.distance_m} m, ${s.duration_min} dk)</span></div>`).join('');
}

function startVoicePlayback() {
    if (!('speechSynthesis' in window)) { showToast('TarayÃ„Â±cÃ„Â± TTS desteklemiyor','warning'); return; }
    if (!elTurnByTurnList) return;
    const items = Array.from(elTurnByTurnList.querySelectorAll('.turn-step')).map(el=> el.textContent.trim());
    if (!items.length) { showToast('AdÃ„Â±m yok','warning'); return; }
    stopVoicePlayback();
    ttsQueue = items;
    ttsPlaying = true;
    playNextTTS();
}

function playNextTTS() {
    if (!ttsPlaying || ttsQueue.length===0) { ttsPlaying=false; return; }
    const text = ttsQueue.shift();
    ttsUtterance = new SpeechSynthesisUtterance(text);
    ttsUtterance.lang = 'tr-TR';
    ttsUtterance.rate = 1;
    ttsUtterance.onend = ()=> { playNextTTS(); };
    speechSynthesis.speak(ttsUtterance);
}

function stopVoicePlayback() {
    ttsPlaying = false;
    ttsQueue = [];
    if (ttsUtterance) {
        try { speechSynthesis.cancel(); } catch(e){}
        ttsUtterance = null;
    }
}

if (elBtnStartVoice) elBtnStartVoice.addEventListener('click', startVoicePlayback);
if (elBtnStopVoice) elBtnStopVoice.addEventListener('click', stopVoicePlayback);

loadTurkiyeData();
initMainLlmChat();

// ========== UX ENHANCEMENTS (2026-03-18) ==========

const routeDecisionState = {
    routeData: null,
    weatherSummary: null,
    overlapWarning: null,
};

function normalizePoiConfidenceScore(poi) {
    let value = Number(
        poi?.confidence ?? poi?.match_score ?? poi?.similarity ?? poi?.score ?? 0.5
    );
    if (!Number.isFinite(value)) value = 0.5;
    if (value > 1 && value <= 100) value = value / 100;
    return Math.max(0, Math.min(1, value));
}

function ensureRouteDecisionPanel() {
    const routeInfo = document.getElementById("routeInfo");
    if (!routeInfo) return null;
    let panel = document.getElementById("routeDecisionPanel");
    if (!panel) {
        panel = document.createElement("div");
        panel.id = "routeDecisionPanel";
        panel.style.marginTop = "12px";
        panel.style.padding = "10px 12px";
        panel.style.borderRadius = "10px";
        panel.style.border = "1px solid rgba(108, 92, 231, 0.35)";
        panel.style.background = "rgba(108, 92, 231, 0.08)";
        routeInfo.appendChild(panel);
    }
    return panel;
}

function renderRouteDecisionPanel() {
    const panel = ensureRouteDecisionPanel();
    if (!panel) return;

    const route = routeDecisionState.routeData;
    const weather = routeDecisionState.weatherSummary;
    const overlapWarning = routeDecisionState.overlapWarning;

    if (!route) {
        panel.style.display = "none";
        return;
    }

    const routeType = route.route_type || "route_1";
    const routeLabel = routeType.replace("route_", "Rota ");
    const distance = Number(route.total_distance_km || 0).toFixed(1);
    const duration = Math.round(Number(route.estimated_walk_minutes || 0));

    const weatherText = weather
        ? `${weather.levelLabel}: ${weather.message}`
        : "Hava analizi bekleniyor";

    const warningHtml = overlapWarning
        ? `<div style="margin-top:8px;color:#b45309;font-weight:600;">${overlapWarning}</div>`
        : "";

    panel.innerHTML = `
        <div style="font-weight:700; margin-bottom:4px;">Akilli Rota Karari</div>
        <div style="font-size:0.92rem; line-height:1.45;">
            <div><strong>${routeLabel}</strong> secildi Ã¢â‚¬Â¢ ${distance} km Ã¢â‚¬Â¢ ${duration} dk</div>
            <div style="margin-top:4px;">Hava etkisi: ${weatherText}</div>
            ${warningHtml}
        </div>
    `;
    panel.style.display = "block";
}

function summarizeWeatherForDecision(routeWeather, criticalAdvice) {
    if (!Array.isArray(routeWeather) || routeWeather.length === 0) {
        return null;
    }

    const levelOrder = { danger: 3, warning: 2, info: 1 };
    let topLevel = "info";
    let itemCount = 0;

    routeWeather.forEach((rw) => {
        const advice = rw?.advice;
        if (!advice) return;
        itemCount += Array.isArray(advice.items) ? advice.items.length : 0;
        if ((levelOrder[advice.alert_level] || 0) > (levelOrder[topLevel] || 0)) {
            topLevel = advice.alert_level;
        }
    });

    const labelMap = {
        info: "Bilgi",
        warning: "Uyari",
        danger: "Yuksek Risk",
    };

    let message = `${routeWeather.length} nokta analiz edildi`;
    if (criticalAdvice && criticalAdvice.summary) {
        message = criticalAdvice.summary;
    } else if (itemCount > 0) {
        message = `${itemCount} adet hava uyari maddesi var`;
    }

    return {
        level: topLevel,
        levelLabel: labelMap[topLevel] || "Bilgi",
        message,
    };
}

function buildShortDistanceOverlapWarning(alternatives) {
    if (!Array.isArray(alternatives) || alternatives.length < 2) return null;
    const shortest = Number(alternatives[0]?.distance_km || 0);
    if (!Number.isFinite(shortest) || shortest > 1.0) return null;

    const closeAlternatives = alternatives.slice(1).filter((alt) => {
        const km = Number(alt?.distance_km || 0);
        if (!Number.isFinite(km)) return false;
        return Math.abs(km - shortest) <= 0.12;
    });

    if (closeAlternatives.length === 0) return null;
    return "Kisa mesafede alternatifler benzer olabilir (olasi yuksek overlap).";
}

const _origShowRouteInfo = showRouteInfo;
showRouteInfo = function (data) {
    _origShowRouteInfo(data);
    routeDecisionState.routeData = data || null;
    renderRouteDecisionPanel();
};

const _origShowWeatherBanner = showWeatherBanner;
showWeatherBanner = function (routeWeather, criticalAdvice = null) {
    _origShowWeatherBanner(routeWeather, criticalAdvice);
    routeDecisionState.weatherSummary = summarizeWeatherForDecision(routeWeather, criticalAdvice);
    renderRouteDecisionPanel();
};

if (typeof hideWeatherBanner === "function") {
    const _origHideWeatherBanner = hideWeatherBanner;
    hideWeatherBanner = function () {
        _origHideWeatherBanner();
        routeDecisionState.weatherSummary = null;
        renderRouteDecisionPanel();
    };
}

const _origDisplayAlternativeRoutes = displayAlternativeRoutes;
displayAlternativeRoutes = function (alternatives) {
    _origDisplayAlternativeRoutes(alternatives);
    routeDecisionState.overlapWarning = buildShortDistanceOverlapWarning(alternatives);
    renderRouteDecisionPanel();
};

function ensurePoiFilterPanel() {
    let panel = document.getElementById("poiFilterPanel");
    if (panel) return panel;

    const clearButton = document.getElementById("btnClearPois");
    const host = clearButton?.parentElement;
    if (!host) return null;

    panel = document.createElement("div");
    panel.id = "poiFilterPanel";
    panel.style.display = "none";
    panel.style.marginTop = "8px";
    panel.style.padding = "8px";
    panel.style.borderRadius = "8px";
    panel.style.background = "rgba(0, 206, 201, 0.08)";
    panel.style.border = "1px solid rgba(0, 206, 201, 0.30)";
    host.insertBefore(panel, clearButton);

    panel.innerHTML = `
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <label style="font-size:0.82rem;">Kategori:
                <select id="poiCategoryFilter" style="margin-left:4px;"></select>
            </label>
            <label style="font-size:0.82rem;">Min guven:
                <input id="poiMinConfidence" type="range" min="0" max="100" value="0" step="5" style="vertical-align:middle;" />
                <span id="poiMinConfidenceLabel">0%</span>
            </label>
            <span id="poiFilterCount" style="font-size:0.82rem;color:#374151;"></span>
        </div>
    `;

    panel.querySelector("#poiCategoryFilter").addEventListener("change", applyPoiFilters);
    panel.querySelector("#poiMinConfidence").addEventListener("input", applyPoiFilters);
    return panel;
}

function applyPoiFilters() {
    const panel = document.getElementById("poiFilterPanel");
    if (!panel) return;

    const category = panel.querySelector("#poiCategoryFilter").value || "all";
    const minConf = Number(panel.querySelector("#poiMinConfidence").value || 0) / 100;
    panel.querySelector("#poiMinConfidenceLabel").textContent = `${Math.round(minConf * 100)}%`;

    let visibleCount = 0;
    poiMarkers.forEach((marker) => {
        const meta = marker.__poiMeta || { category: "unknown", confidence: 0.5 };
        const categoryOk = category === "all" || meta.category === category;
        const confidenceOk = meta.confidence >= minConf;
        const show = categoryOk && confidenceOk;
        marker.setOpacity(show ? 1 : 0.15);
        if (show) visibleCount += 1;
    });

    const countEl = panel.querySelector("#poiFilterCount");
    if (countEl) {
        countEl.textContent = `${visibleCount}/${poiMarkers.length} mekan gosteriliyor`;
    }
}

const _origDisplayPois = displayPois;
displayPois = function (pois, category, markerEmoji, markerLabel) {
    const startLen = poiMarkers.length;
    _origDisplayPois(pois, category, markerEmoji, markerLabel);

    const panel = ensurePoiFilterPanel();
    if (!panel) return;

    const categories = new Set(["all"]);
    poiMarkers.forEach((marker, idx) => {
        const poi = pois[idx - startLen];
        if (!poi) return;

        const confidence = normalizePoiConfidenceScore(poi);
        marker.__poiMeta = {
            category,
            confidence,
        };
        categories.add(category);

        const popup = marker.getPopup();
        if (popup) {
            const currentContent = popup.getContent() || "";
            marker.setPopupContent(
                `${currentContent}<div style="margin-top:6px;font-size:0.8rem;color:#4b5563;">Guven skoru: %${Math.round(confidence * 100)}</div>`
            );
        }
    });

    const select = panel.querySelector("#poiCategoryFilter");
    select.innerHTML = "";
    Array.from(categories).forEach((cat) => {
        const option = document.createElement("option");
        option.value = cat;
        option.textContent = cat === "all" ? "Tum" : cat;
        select.appendChild(option);
    });

    panel.style.display = "block";
    applyPoiFilters();
};

if (typeof clearPois === "function") {
    const _origClearPois = clearPois;
    clearPois = function () {
        _origClearPois();
        const panel = document.getElementById("poiFilterPanel");
        if (panel) {
            panel.style.display = "none";
        }
    };
}






