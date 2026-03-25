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
                <div class="nearby-stop-item" onclick="map.setView([${stop.lat}, ${stop.lon}], 17)">
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
        map.setView([lat, lon], 17);
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

    function drawSegmentLine(seg, coords) {
        const latlngs = coords.map((c) => [c[0], c[1]]);
        if (seg.mode === "bus") {
            const glow = L.polyline(latlngs, {
                color: "#3b82f6",
                weight: 10,
                opacity: 0.18,
            }).addTo(map);
            const line = L.polyline(latlngs, {
                color: "#2563eb",
                weight: 5,
                opacity: 0.95,
            }).addTo(map);
            transitRouteLayers.push(glow, line);
        } else {
            const line = L.polyline(latlngs, {
                color: "#16a34a",
                weight: 4,
                opacity: 0.9,
                dashArray: "8,6",
            }).addTo(map);
            transitRouteLayers.push(line);
        }
    }

    function drawStepMarker(lat, lon, num, className, text) {
        const marker = L.marker([lat, lon], {
            icon: L.divIcon({
                className: "transit-step-icon",
                html: `<div class="step-circle ${className}">${num}</div>`,
                iconSize: [28, 28],
                iconAnchor: [14, 14],
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

        clearTransitRoute();
        let step = 1;
        const allBounds = [];

        option.segments.forEach((seg) => {
            if (!Array.isArray(seg.coords) || seg.coords.length < 2) return;
            drawSegmentLine(seg, seg.coords);
            seg.coords.forEach((c) => allBounds.push([c[0], c[1]]));

            const start = seg.coords[0];
            const end = seg.coords[seg.coords.length - 1];
            if (seg.mode === "walk") {
                drawStepMarker(start[0], start[1], step++, "step-walk", seg.description || "Walk");
            } else if (seg.mode === "bus") {
                drawStepMarker(start[0], start[1], step++, "step-board", "Board bus");
                drawStepMarker(end[0], end[1], step++, "step-alight", "Get off");
                if (seg.route_code) {
                    const mid = seg.coords[Math.floor(seg.coords.length / 2)];
                    const label = L.marker([mid[0], mid[1]], {
                        icon: L.divIcon({
                            className: "transit-route-label",
                            html: `<div class="route-label-tag">${seg.route_code}</div>`,
                            iconSize: [70, 24],
                            iconAnchor: [35, 12],
                        }),
                    }).addTo(map);
                    transitRouteLayers.push(label);
                }
            }
            drawStepMarker(end[0], end[1], step++, "step-end", "Destination");
        });

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
                const iconHtml = opt.type === "transit" ? "&#x1F68C;" : "&#x1F6B6;";
                html += `
                    <div class="multimodal-option ${isRec ? "recommended" : ""}" onclick="showTransitRoute(${index})" style="cursor:pointer;">
                        <div class="multimodal-option-header">
                            <span class="multimodal-icon">${iconHtml}</span>
                            <div class="multimodal-option-info">
                                <h3 class="multimodal-option-name">${opt.name || opt.type || "Option"}</h3>
                                <p class="multimodal-option-desc">${opt.description || ""}</p>
                            </div>
                            <div class="multimodal-option-time">
                                <span class="multimodal-time-value">${opt.total_time_min || "-"}</span>
                                <span class="multimodal-time-unit">dk</span>
                            </div>
                        </div>
                        <div class="multimodal-segments">
                `;

                (opt.segments || []).forEach((seg) => {
                    const segIcon = seg.mode === "bus" ? "&#x1F68C;" : "&#x1F6B6;";
                    const segClass = seg.mode === "bus" ? "seg-bus" : "seg-walk";
                    html += `
                        <div class="multimodal-segment ${segClass}">
                            <span class="seg-icon">${segIcon}</span>
                            <span class="seg-desc">${seg.description || seg.mode || ""}</span>
                            <span class="seg-time">${seg.duration_min || 0} dk</span>
                        </div>
                    `;
                });

                if (opt.wait_time_min) {
                    html += `
                        <div class="multimodal-segment seg-wait">
                            <span class="seg-icon">&#x23F3;</span>
                            <span class="seg-desc">Wait</span>
                            <span class="seg-time">${opt.wait_time_min} dk</span>
                        </div>
                    `;
                }

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

        const origin = selectedPoints[0];
        const destination = selectedPoints[selectedPoints.length - 1];

        try {
            if (typeof showLoading === "function") {
                showLoading("Transit options are being calculated...");
            }
            const response = await fetch(`${API_BASE}/multimodal/compare`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ origin, destination }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "Failed to compare routes");
            }
            displayMultimodalResults(data);
            if (typeof showToast === "function") {
                showToast("Route options calculated", "success");
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
