(function () {
    if (typeof map === "undefined" || typeof API_BASE === "undefined") {
        return;
    }

    const elChkShowStops = document.getElementById("chkShowStops");
    const elTransitPanel = document.getElementById("transitPanel");
    const elTransitSearchInput = document.getElementById("transitSearchInput");
    const elBtnSearchTransit = document.getElementById("btnSearchTransit");
    const elTransitSearchResults = document.getElementById("transitSearchResults");
    const elNearbyStopsList = document.getElementById("nearbyStopsList");
    const elBtnCompareRoutes = document.getElementById("btnCompareRoutes");
    const elMultimodalPanel = document.getElementById("multimodalPanel");
    const elMultimodalResults = document.getElementById("multimodalResults");
    const elTransitModeInputs = Array.from(document.querySelectorAll("input[data-transit-mode]"));

    let transitEnabled = false;
    let transitStopMarkers = null;
    let transitRouteLayers = [];
    let transitDebounceTimer = null;
    let multimodalData = null;

    function createStopIcon() {
        return L.divIcon({
            className: "transit-stop-icon",
            html: '<div class="stop-marker">&#x1F68F;</div>',
            iconSize: [24, 24],
            iconAnchor: [12, 12],
            popupAnchor: [0, -12],
        });
    }

    function ensureTransitLayer() {
        if (transitStopMarkers) return;
        if (typeof L.markerClusterGroup === "function") {
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
        } else {
            transitStopMarkers = L.layerGroup();
        }
        map.addLayer(transitStopMarkers);
    }

    function updateNearbyStopsList(stops) {
        if (!elNearbyStopsList) return;
        if (!stops || stops.length === 0) {
            elNearbyStopsList.innerHTML = '<div class="empty-state"><p>No stops found in this area</p></div>';
            return;
        }

        const displayStops = stops.slice(0, 10);
        let html = "";
        displayStops.forEach((stop) => {
            html += `
                <div class="nearby-stop-item" onclick="focusMapInIstanbul(${stop.lat}, ${stop.lon}, 17)">
                    <div class="nearby-stop-info">
                        <span class="nearby-stop-name">${stop.name || "Stop"}</span>
                        <span class="nearby-stop-district">${stop.district || ""}</span>
                    </div>
                    <span class="nearby-stop-distance">${stop.distance_m || 0}m</span>
                </div>
            `;
        });
        if (stops.length > 10) {
            html += `<div class="nearby-stop-more">${stops.length - 10} more...</div>`;
        }
        elNearbyStopsList.innerHTML = html;
    }

    function buildStopPopup(stop) {
        let html = '<div class="stop-popup-card">';
        html += '<div class="stop-popup-header">';
        html += '<span class="stop-popup-emoji">&#x1F68F;</span>';
        html += "<div>";
        html += `<h3 class="stop-popup-name">${stop.name || "Stop"}</h3>`;
        html += `<span class="stop-popup-district">${stop.district || ""}</span>`;
        html += "</div></div>";
        html += '<div class="stop-popup-details">';
        html += `<div class="stop-detail"><span class="stop-detail-label">Code:</span>${stop.code || "-"}</div>`;
        if (stop.distance_m !== undefined) {
            html += `<div class="stop-detail"><span class="stop-detail-label">Distance:</span>${stop.distance_m}m</div>`;
        }
        html += "</div>";
        html += `<button class="stop-popup-btn" onclick="addPoint(${stop.lat}, ${stop.lon})">+ Add to route</button>`;
        html += "</div>";
        return html;
    }

    async function loadNearbyStops() {
        if (!transitEnabled) return;
        ensureTransitLayer();

        const center = map.getCenter();
        const zoom = map.getZoom();
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
                return;
            }

            transitStopMarkers.clearLayers();
            const stops = data.stops || [];
            stops.forEach((stop) => {
                const marker = L.marker([stop.lat, stop.lon], { icon: createStopIcon() });
                marker.bindPopup(buildStopPopup(stop), {
                    maxWidth: 300,
                    minWidth: 210,
                    className: "transit-popup",
                });
                transitStopMarkers.addLayer(marker);
            });

            updateNearbyStopsList(stops);
        } catch (error) {
            console.error("Transit stops error:", error);
        }
    }

    function displayTransitSearchResults(stops) {
        if (!elTransitSearchResults) return;
        elTransitSearchResults.style.display = "block";
        if (!stops || stops.length === 0) {
            elTransitSearchResults.innerHTML = '<div class="empty-state"><p>No result</p></div>';
            return;
        }

        let html = "";
        stops.forEach((stop) => {
            const name = (stop.name || "Stop").replace(/'/g, "\\'");
            html += `
                <div class="transit-result-item" onclick="selectTransitStop(${stop.lat}, ${stop.lon}, '${name}')">
                    <span class="transit-result-icon">&#x1F68F;</span>
                    <div class="transit-result-info">
                        <span class="transit-result-name">${stop.name || "Stop"}</span>
                        <span class="transit-result-district">${stop.district || ""} - ${stop.code || "-"}</span>
                    </div>
                </div>
            `;
        });
        elTransitSearchResults.innerHTML = html;
    }

    window.selectTransitStop = function (lat, lon, name) {
        if (typeof window.focusMapInIstanbul === "function") {
            if (!window.focusMapInIstanbul(lat, lon, 17)) return;
        } else {
            map.setView([lat, lon], 17);
        }
        if (elTransitSearchInput) elTransitSearchInput.value = "";
        if (elTransitSearchResults) elTransitSearchResults.style.display = "none";
        if (typeof showToast === "function") {
            showToast(`${name} selected`, "info");
        }
    };

    async function searchTransitStops() {
        if (!elTransitSearchInput) return;
        const query = elTransitSearchInput.value.trim();
        if (!query || query.length < 2) {
            if (typeof showToast === "function") {
                showToast("Enter at least 2 characters", "error");
            }
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/transit/search?q=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "Search failed");
            }
            displayTransitSearchResults(data.stops || []);
        } catch (error) {
            if (typeof showToast === "function") {
                showToast(error.message, "error");
            }
        }
    }

    function clearTransitRoute() {
        transitRouteLayers.forEach((layer) => {
            try {
                map.removeLayer(layer);
            } catch (e) {
                // ignore
            }
        });
        transitRouteLayers = [];
    }

    function getSelectedTransitModes() {
        if (!Array.isArray(elTransitModeInputs) || elTransitModeInputs.length === 0) {
            return ["bus", "metro", "metrobus", "ferry"];
        }
        const selected = elTransitModeInputs
            .filter((el) => el && el.checked)
            .map((el) => String(el.dataset.transitMode || "").toLowerCase())
            .filter((m) => m);
        return selected;
    }

    function haversineMeters(a, b) {
        const toRad = (deg) => (deg * Math.PI) / 180;
        const lat1 = Number(a[0]);
        const lon1 = Number(a[1]);
        const lat2 = Number(b[0]);
        const lon2 = Number(b[1]);
        if (!Number.isFinite(lat1) || !Number.isFinite(lon1) || !Number.isFinite(lat2) || !Number.isFinite(lon2)) {
            return Number.POSITIVE_INFINITY;
        }
        const R = 6371000;
        const dLat = toRad(lat2 - lat1);
        const dLon = toRad(lon2 - lon1);
        const s1 = Math.sin(dLat / 2);
        const s2 = Math.sin(dLon / 2);
        const aa = s1 * s1 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * s2 * s2;
        const c = 2 * Math.atan2(Math.sqrt(aa), Math.sqrt(1 - aa));
        return R * c;
    }

    function splitSegmentCoords(coords, mode = "") {
        const normalized = (coords || [])
            .filter((c) => Array.isArray(c) && c.length >= 2)
            .map((c) => [Number(c[0]), Number(c[1])])
            .filter((c) => Number.isFinite(c[0]) && Number.isFinite(c[1]));

        if (normalized.length < 2) return [];

        const modeName = String(mode || "").toLowerCase();
        if (normalized.length === 2 && (modeName === "rail" || modeName === "bus" || modeName === "ferry")) {
            return [normalized];
        }

        const maxJumpMeters = modeName === "ferry"
            ? 45000
            : (modeName === "rail"
                ? 6500
                : (modeName === "bus" ? 5500 : (modeName === "walk" ? 2500 : 5000)));

        const chunks = [];
        let current = [normalized[0]];

        for (let i = 1; i < normalized.length; i += 1) {
            const prev = current[current.length - 1];
            const next = normalized[i];
            const jumpMeters = haversineMeters(prev, next);

            if (jumpMeters > maxJumpMeters) {
                if (current.length >= 2) chunks.push(current);
                current = [next];
                continue;
            }
            current.push(next);
        }

        if (current.length >= 2) chunks.push(current);
        return chunks;
    }

    function sanitizeSegmentCoords(coords, mode = "") {
        const chunks = splitSegmentCoords(coords, mode);
        if (!chunks.length) return [];
        let best = chunks[0];
        let bestLen = 0;
        chunks.forEach((chunk) => {
            let len = 0;
            for (let i = 1; i < chunk.length; i += 1) {
                len += haversineMeters(chunk[i - 1], chunk[i]);
            }
            if (len > bestLen) {
                bestLen = len;
                best = chunk;
            }
        });
        return best;
    }

    function isMetrobusSegment(seg) {
        if (!seg || seg.mode !== "bus") return false;
        const code = String(seg.route_code || "").toUpperCase().trim();
        return /^34[A-Z0-9]*$/.test(code);
    }

    function getSegmentCoordsForDrawing(seg, transitOnlyView) {
        const routeCoords = Array.isArray(seg?.coords) ? seg.coords : [];
        const stopCoords = Array.isArray(seg?.stop_coords) ? seg.stop_coords : [];

        // Duz cizgi "teleport" artefaktlarini azaltmak icin
        // transit gorunumunde de once gercek rota geometrisini kullan.
        if (routeCoords.length >= 2) {
            return routeCoords;
        }
        return stopCoords;
    }

    function getCurrentSelectedPoints() {
        if (typeof selectedPoints !== "undefined" && Array.isArray(selectedPoints)) {
            return selectedPoints;
        }
        if (Array.isArray(window.selectedPoints)) {
            return window.selectedPoints;
        }
        return [];
    }

    function segmentLengthMeters(coords, mode = "") {
        const chunks = splitSegmentCoords(coords, mode);
        if (!chunks.length) return 0;
        let total = 0;
        chunks.forEach((chunk) => {
            for (let i = 1; i < chunk.length; i += 1) {
                total += haversineMeters(chunk[i - 1], chunk[i]);
            }
        });
        return total;
    }

    function drawSegmentLine(seg, coords, opts = {}) {
        const transitOnlyView = !!opts.transitOnlyView;
        const chunks = splitSegmentCoords(coords, seg.mode);
        if (!chunks.length) return;
        if (seg.mode === "bus" || seg.mode === "rail" || seg.mode === "ferry") {
            const isRail = seg.mode === "rail";
            const isFerry = seg.mode === "ferry";
            const isMetrobus = isMetrobusSegment(seg);
            const glowColor = isMetrobus
                ? "#fb7185"
                : (isFerry ? "#06b6d4" : (isRail ? "#8b5cf6" : "#3b82f6"));
            const lineColor = isMetrobus
                ? "#e11d48"
                : (isFerry ? "#0891b2" : (isRail ? "#7c3aed" : "#2563eb"));
            chunks.forEach((chunk) => {
                const latlngs = chunk.map((c) => [c[0], c[1]]);
                const glow = L.polyline(latlngs, {
                    color: glowColor,
                    weight: isMetrobus ? 14 : 12,
                    opacity: isMetrobus ? 0.35 : 0.28,
                }).addTo(map);
                const line = L.polyline(latlngs, {
                    color: lineColor,
                    weight: isMetrobus ? 6 : 5,
                    opacity: 0.95,
                    dashArray: isFerry ? "10,8" : null,
                }).addTo(map);
                transitRouteLayers.push(glow, line);
            });
        } else {
            chunks.forEach((chunk) => {
                const latlngs = chunk.map((c) => [c[0], c[1]]);
                const line = L.polyline(latlngs, {
                    color: "#16a34a",
                    weight: 4,
                    opacity: transitOnlyView ? 0.82 : 0.9,
                    dashArray: transitOnlyView ? null : "2,8", // Transit gorunumunde daha net olsun
                }).addTo(map);
                transitRouteLayers.push(line);
            });
        }
    }

    function drawStepMarker(lat, lon, num, className, text) {
        let iconHtml = num;
        if (num === "W") {
            iconHtml = "👟";
        } else if (num === "B") {
            if (className.includes("metrobus")) iconHtml = "🚨";
            else if (className.includes("metro")) iconHtml = "🚇";
            else if (className.includes("tram")) iconHtml = "🚊";
            else if (className.includes("ferry")) iconHtml = "🚢";
            else iconHtml = "🚌";
        } else if (num === "I") {
            iconHtml = "🛑";
        } else if (num === "T") {
            iconHtml = "🔄";
        }

        const marker = L.marker([lat, lon], {
            icon: L.divIcon({
                className: "transit-step-icon",
                html: `<div class="step-circle ${className}" style="display:flex;align-items:center;justify-content:center;font-size:1.1rem;background:rgba(15,15,20,0.85);backdrop-filter:blur(4px);border:2px solid currentColor;border-radius:50%;box-shadow:0 4px 10px rgba(0,0,0,0.3);width:100%;height:100%;color:#fff;">${iconHtml}</div>`,
                iconSize: [32, 32],
                iconAnchor: [16, 16],
            }),
        }).addTo(map);
        marker.bindTooltip(text || "", {
            permanent: false,
            direction: "top",
            className: "transit-route-tooltip",
        });
        transitRouteLayers.push(marker);
    }

    window.showTransitRoute = function (optionIndex) {
        if (!multimodalData || !multimodalData.options) return;
        const option = multimodalData.options[optionIndex];
        if (!option || !Array.isArray(option.segments)) return;
        const transitOnlyView = option.type === "transit";

        clearTransitRoute();
        const allBounds = [];
        const shownRouteLabels = new Set();
        const drawableSegments = option.segments.map((seg, idx) => {
            const displayCoords = getSegmentCoordsForDrawing(seg, transitOnlyView);
            const isEndpointWalk = idx === 0 || idx === (option.segments.length - 1);
            return { seg, idx, displayCoords, isEndpointWalk };
        }).filter(({ seg, displayCoords }) => {
            if (!Array.isArray(displayCoords) || displayCoords.length < 2) return false;
            if (transitOnlyView && seg.mode === "walk") {
                // Cizimde sureklilik icin ara aktarma yuruyuslerini de goster.
                return true;
            }
            return true;
        });

        let firstDrawnPoint = null;
        let lastDrawnPoint = null;
        drawableSegments.forEach(({ seg, displayCoords }) => {
            drawSegmentLine(seg, displayCoords, { transitOnlyView });
            const chunks = splitSegmentCoords(displayCoords, seg.mode);
            chunks.forEach((chunk) => {
                chunk.forEach((c) => allBounds.push([c[0], c[1]]));
            });
            if (chunks.length) {
                const firstChunk = chunks[0];
                const lastChunk = chunks[chunks.length - 1];
                if (firstChunk.length && !firstDrawnPoint) firstDrawnPoint = firstChunk[0];
                if (lastChunk.length) lastDrawnPoint = lastChunk[lastChunk.length - 1];
            }

            // Transit modunda Google Maps benzeri sade gorunum:
            // sadece gidilecek segmentleri ciz, gereksiz adim marker'larini cizme.
            if (transitOnlyView) {
                if (!seg.route_code) return;
                const routeCode = String(seg.route_code);
                const labelKey = `${seg.mode}:${routeCode}`;
                if (shownRouteLabels.has(labelKey)) return;
                if (segmentLengthMeters(displayCoords, seg.mode) < 120) return;
                shownRouteLabels.add(labelKey);

                const clean = sanitizeSegmentCoords(displayCoords, seg.mode);
                if (clean.length < 2) return;
                const mid = clean[Math.floor(clean.length / 2)];
                const metrobusClass = isMetrobusSegment(seg) ? " route-label-metrobus" : "";
                const labelText = isMetrobusSegment(seg) ? `${routeCode} MB` : routeCode;
                const label = L.marker([mid[0], mid[1]], {
                    icon: L.divIcon({
                        className: "transit-route-label",
                        html: `<div class="route-label-tag${metrobusClass}">${labelText}</div>`,
                        iconSize: [88, 24],
                        iconAnchor: [44, 12],
                    }),
                }).addTo(map);
                transitRouteLayers.push(label);
                return;
            }

            const clean = sanitizeSegmentCoords(displayCoords, seg.mode);
            if (clean.length < 2) return;
            const start = clean[0];
            const end = clean[clean.length - 1];
            if (seg.mode === "walk") {
                drawStepMarker(start[0], start[1], "W", "step-walk", seg.description || "Yürü");
            } else if (seg.mode === "bus" || seg.mode === "rail" || seg.mode === "ferry") {
                const isMetrobus = isMetrobusSegment(seg);
                const isMetro = seg.mode === "rail" && String(seg.route_code || "").startsWith("M");
                const isTram = seg.mode === "rail" && String(seg.route_code || "").startsWith("T");
                
                let boardClass = "step-board";
                if (isMetrobus) boardClass += " metrobus";
                else if (isMetro) boardClass += " metro";
                else if (isTram) boardClass += " tram";
                else if (seg.mode === "ferry") boardClass += " ferry";
                else boardClass += " bus";

                const boardText = isMetrobus ? "Metrobüse bin" : (isMetro ? "Metroya bin" : (isTram ? "Tramvaya bin" : (seg.mode === "ferry" ? "Vapura bin" : "Otobüse bin")));
                drawStepMarker(start[0], start[1], "B", boardClass, boardText);
                drawStepMarker(end[0], end[1], "I", "step-alight", "İniş: " + (seg.to_stop || "İstasyon"));
            }
        });

        // Cizim noktalari markerlara degmiyorsa ince baglanti cizgisi ekle.
        const routePoints = getCurrentSelectedPoints();
        if (routePoints.length >= 2) {
            const originPoint = routePoints[0];
            const destPoint = routePoints[routePoints.length - 1];
            const connectorStyle = {
                color: "#22c55e",
                weight: 3,
                opacity: 0.75,
                dashArray: "4,7",
            };
            if (firstDrawnPoint && Array.isArray(originPoint) && originPoint.length >= 2) {
                const d0 = haversineMeters(
                    [Number(originPoint[0]), Number(originPoint[1])],
                    [Number(firstDrawnPoint[0]), Number(firstDrawnPoint[1])],
                );
                if (Number.isFinite(d0) && d0 > 60) {
                    const c0 = L.polyline([
                        [Number(originPoint[0]), Number(originPoint[1])],
                        [Number(firstDrawnPoint[0]), Number(firstDrawnPoint[1])],
                    ], connectorStyle).addTo(map);
                    transitRouteLayers.push(c0);
                    allBounds.push([Number(originPoint[0]), Number(originPoint[1])]);
                }
            }
            if (lastDrawnPoint && Array.isArray(destPoint) && destPoint.length >= 2) {
                const d1 = haversineMeters(
                    [Number(lastDrawnPoint[0]), Number(lastDrawnPoint[1])],
                    [Number(destPoint[0]), Number(destPoint[1])],
                );
                if (Number.isFinite(d1) && d1 > 60) {
                    const c1 = L.polyline([
                        [Number(lastDrawnPoint[0]), Number(lastDrawnPoint[1])],
                        [Number(destPoint[0]), Number(destPoint[1])],
                    ], connectorStyle).addTo(map);
                    transitRouteLayers.push(c1);
                    allBounds.push([Number(destPoint[0]), Number(destPoint[1])]);
                }
            }
        }

        if (allBounds.length >= 2) {
            map.fitBounds(allBounds, { padding: [40, 40], maxZoom: 16 });
        }

        document.querySelectorAll(".multimodal-option").forEach((el, i) => {
            el.classList.toggle("active-route", i === optionIndex);
        });
    };

    function displayMultimodalResults(data) {
        if (!elMultimodalPanel || !elMultimodalResults) return;
        multimodalData = data;
        elMultimodalPanel.style.display = "block";

        const options = data.options || [];
        let html = "";

        if (options.length === 0) {
            html = '<div class="empty-state"><p>No option found</p></div>';
        } else {
            const recommended = data.recommended || "walking";
            const recClass = recommended === "transit" ? "rec-transit" : "rec-walking";
            if (data.recommendation_reason) {
                html += `<div class="multimodal-rec ${recClass}">${data.recommendation_reason}</div>`;
            }

            options.forEach((opt, index) => {
                const isRec = opt.type === recommended;
                const isMetro = opt.transit_mode === "metro";
                const isMixed = opt.transit_mode === "mixed";
                const isFerryMode = opt.transit_mode === "ferry";
                const hasMetrobus = Array.isArray(opt.segments) && opt.segments.some((s) => isMetrobusSegment(s));
                const iconHtml = opt.type === "transit"
                    ? (hasMetrobus ? "&#x1F68E;" : (isMetro ? "&#x1F687;" : (isMixed ? "&#x1F69D;" : (isFerryMode ? "&#x26F4;" : "&#x1F68C;"))))
                    : "&#x1F6B6;";
                const modeBadge = opt.type === "transit"
                    ? (hasMetrobus ? "Metrobus" : (isMetro ? "Metro" : (isMixed ? "Otobus + Metro" : (isFerryMode ? "Vapur" : "Otobus"))))
                    : "Yuruyus";
                const reasonLabels = {
                    fastest: "En hizli",
                    least_transfer: "Az aktarma",
                    metro_preferred: "Metro odakli",
                    metrobus_preferred: "Metrobus odakli",
                    low_walk: "Az yurume",
                    multimodal_mix: "Karma rota",
                    ferry_direct: "Direkt vapur",
                    alternative: "Alternatif",
                };
                const reasonBadge = (opt.selection_reason && reasonLabels[opt.selection_reason])
                    ? `<span class="route-label-tag" style="margin-left:8px;">${reasonLabels[opt.selection_reason]}</span>`
                    : "";
                html += `
                    <div class="multimodal-option ${isRec ? "recommended" : ""}" onclick="showTransitRoute(${index})" style="cursor:pointer;">
                        <div class="multimodal-option-header">
                            <span class="multimodal-icon">${iconHtml}</span>
                            <div class="multimodal-option-info">
                                <h3 class="multimodal-option-name">${opt.name || opt.type || "Option"} ${reasonBadge}</h3>
                                <p class="multimodal-option-desc"><strong>${modeBadge}</strong>${opt.description ? ` · ${opt.description}` : ""}</p>
                            </div>
                            <div class="multimodal-option-time">
                                <span class="multimodal-time-value">${opt.total_time_min || "-"}</span>
                                <span class="multimodal-time-unit">dk</span>
                            </div>
                        </div>
                        <div class="multimodal-segments">
                `;

                (opt.segments || []).forEach((seg) => {
                    if (opt.type === "transit" && seg.mode === "walk") {
                        return;
                    }
                    const isRail = seg.mode === "rail";
                    const isFerry = seg.mode === "ferry";
                    const isMetrobus = isMetrobusSegment(seg);
                    const segIcon = isMetrobus ? "&#x1F68E;" : (seg.mode === "bus" ? "&#x1F68C;" : (isRail ? "&#x1F687;" : (isFerry ? "&#x26F4;" : "&#x1F6B6;")));
                    const segClass = isMetrobus ? "seg-metrobus" : ((seg.mode === "bus" || isRail) ? "seg-bus" : "seg-walk");
                    const segDesc = isMetrobus
                        ? `${seg.route_code || "34"} metrobus`
                        : (seg.description || seg.mode || "");
                    html += `
                        <div class="multimodal-segment ${segClass}">
                            <span class="seg-icon">${segIcon}</span>
                            <span class="seg-desc">${segDesc}</span>
                            <span class="seg-time">${seg.duration_min || 0} dk</span>
                        </div>
                    `;

                    if ((seg.mode === "bus" || seg.mode === "rail" || seg.mode === "ferry") && seg.wait_min) {
                        html += `
                            <div class="multimodal-segment seg-wait">
                                <span class="seg-icon">&#x23F3;</span>
                                <span class="seg-desc">Wait</span>
                                <span class="seg-time">~${seg.wait_min} dk</span>
                            </div>
                        `;
                    }
                });

                html += `
                        </div>
                        <div class="multimodal-show-map">&#x1F5FA; Show on map</div>
                    </div>
                `;
            });
        }

        elMultimodalResults.innerHTML = html;

        const recIndex = options.findIndex((o) => o.type === data.recommended);
        if (recIndex >= 0) {
            window.showTransitRoute(recIndex);
        } else if (options.length > 0) {
            window.showTransitRoute(0);
        }

        elMultimodalPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    async function compareMultimodalRoutes() {
        if (typeof selectedPoints === "undefined" || selectedPoints.length < 2) {
            if (typeof showToast === "function") {
                showToast("Select at least 2 points", "error");
            }
            return;
        }

        const allowedModes = getSelectedTransitModes();
        if (!allowedModes.length) {
            if (typeof showToast === "function") {
                showToast("En az bir ulasim modu sec", "error");
            }
            return;
        }

        const origin = selectedPoints[0];
        const destination = selectedPoints[selectedPoints.length - 1];

        try {
            if (typeof showLoading === "function") {
                showLoading("Transit options are being calculated...");
            }
            const response = await fetch(`${API_BASE}/multimodal/compare`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ origin, destination, allowed_modes: allowedModes }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "Failed to compare routes");
            }
            displayMultimodalResults(data);
            if (typeof showToast === "function") {
                showToast("Route options calculated", "success");
            }
            // Hava durumu uyarısı popup'ını tetikle
            if (typeof checkRouteWeatherAndShowBanner === "function") {
                checkRouteWeatherAndShowBanner(selectedPoints);
            }
        } catch (error) {
            if (typeof showToast === "function") {
                showToast(error.message, "error");
            }
        } finally {
            if (typeof hideLoading === "function") {
                hideLoading();
            }
        }
    }

    if (elChkShowStops) {
        elChkShowStops.addEventListener("change", function () {
            transitEnabled = this.checked;
            if (elTransitPanel) {
                elTransitPanel.style.display = transitEnabled ? "block" : "none";
            }
            if (transitEnabled) {
                loadNearbyStops();
            } else if (transitStopMarkers) {
                transitStopMarkers.clearLayers();
                if (elNearbyStopsList) {
                    elNearbyStopsList.innerHTML = '<div class="empty-state"><p>Transit closed</p></div>';
                }
            }
        });
    }

    map.on("moveend", function () {
        if (!transitEnabled) return;
        clearTimeout(transitDebounceTimer);
        transitDebounceTimer = setTimeout(loadNearbyStops, 300);
    });

    if (elBtnSearchTransit) {
        elBtnSearchTransit.addEventListener("click", searchTransitStops);
    }
    if (elTransitSearchInput) {
        elTransitSearchInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") searchTransitStops();
        });
    }
    if (elBtnCompareRoutes) {
        elBtnCompareRoutes.addEventListener("click", compareMultimodalRoutes);
    }

    window.clearTransitRoute = clearTransitRoute;
})();
