#Requires -Version 5.1
<#
.SYNOPSIS
    OpenRoutePlanner Route API Smoke Test Script

.DESCRIPTION
    Route API endpoint'lerinin temel fonksiyonalitesini test eder.
    HTTP status code, response structure ve error handling kontrol edilir.

.PARAMETER BaseUrl
    API base URL. Varsayilan: http://localhost:5000

.PARAMETER OutputFormat
    Ciktí format: Text, Json, Csv. Varsayilan: Text

.EXAMPLE
    .\qa_route_contract.ps1
    .\qa_route_contract.ps1 -BaseUrl http://localhost:5000 -OutputFormat Json
#>

param(
    [string]$BaseUrl = "http://localhost:5000",
    [ValidateSet("Text", "Json", "Csv")]
    [string]$OutputFormat = "Text",
    [switch]$Verbose
)

# =============================================================================
# CONFIGURATION
# =============================================================================

$Script:TestResults = @()
$Script:TotalTests = 0
$Script:PassedTests = 0
$Script:FailedTests = 0

# Istanbul bounding box for valid coordinates
$IstanbulBBox = @{
    MinLat = 40.78
    MaxLat = 41.40
    MinLon = 28.30
    MaxLon = 29.70
}

# Valid test points (Istanbul icinde)
$ValidPoints = @(
    @(40.9900, 29.0290)  # Kadikoy
    @(41.0082, 28.9784) # Sultanahmet
    @(41.0422, 29.0067)  # Besiktas
)

# Invalid test point (Istanbul disi)
$InvalidOutsidePoint = @(39.9208, 32.8541)  # Ankara

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

function Write-TestOutput {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $color = switch ($Level) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "White" }
    }
    
    if ($OutputFormat -eq "Text") {
        Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
    }
}

function Test-ApiEndpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [string]$Description,
        [string]$Body = $null,
        [hashtable]$Headers = @{},
        [string]$ExpectedStatus = "200",
        [scriptblock]$ValidateResponse = $null,
        [scriptblock]$ValidateError = $null
    )
    
    $Script:TotalTests++
    
    $url = "$BaseUrl$Endpoint"
    $result = @{
        Name = $Name
        Method = $Method
        Endpoint = $Endpoint
        Description = $Description
        Status = "PASS"
        StatusCode = 0
        ResponseTime = 0
        Error = $null
        Details = @{}
    }
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    try {
        $params = @{
            Uri = $url
            Method = $Method
            ContentType = "application/json"
            Headers = $Headers
        }
        
        if ($Body) {
            $params.Body = $Body
        }
        
        $response = Invoke-WebRequest @params -TimeoutSec 30 -ErrorAction Stop
        $stopwatch.Stop()
        
        $result.StatusCode = [int]$response.StatusCode
        $result.ResponseTime = $stopwatch.ElapsedMilliseconds
        
        # Parse JSON response
        $responseBody = $null
        try {
            $responseBody = $response.Content | ConvertFrom-Json -ErrorAction Stop
            $result.Details = $responseBody
        }
        catch {
            $result.Details = @{ raw = $response.Content }
        }
        
        # Check status code
        if ([string]$result.StatusCode -ne $ExpectedStatus) {
            $result.Status = "FAIL"
            $result.Error = "Unexpected status code: $($result.StatusCode), expected: $ExpectedStatus"
            Write-TestOutput "$Name - $($result.Error)" "FAIL"
        }
        # Validate response structure if provided
        elseif ($ValidateResponse -and $responseBody) {
            $validationError = & $ValidateResponse $responseBody
            if ($validationError) {
                $result.Status = "FAIL"
                $result.Error = $validationError
                Write-TestOutput "$Name - $($result.Error)" "FAIL"
            }
            else {
                Write-TestOutput "$Name - OK ($($result.ResponseTime)ms)" "PASS"
            }
        }
        else {
            Write-TestOutput "$Name - OK ($($result.ResponseTime)ms)" "PASS"
        }
    }
    catch {
        $stopwatch.Stop()
        $result.Status = "FAIL"
        $result.ResponseTime = $stopwatch.ElapsedMilliseconds
        
        if ($_.Exception.Response) {
            $result.StatusCode = [int]$_.Exception.Response.StatusCode
            $result.Error = "HTTP $($result.StatusCode): $($_.Exception.Message)"
        }
        else {
            $result.Error = $_.Exception.Message
        }
        
        Write-TestOutput "$Name - $($result.Error)" "FAIL"
    }
    
    $Script:TestResults += $result
    
    if ($result.Status -eq "PASS") {
        $Script:PassedTests++
    }
    else {
        $Script:FailedTests++
    }
    
    return $result
}

function Assert-JsonField {
    param(
        [object]$Json,
        [string]$Field,
        [string]$ExpectedType = $null,
        [object]$ExpectedValue = $null
    )
    
    if ($null -eq $Json) {
        return "Response is not valid JSON"
    }
    
    $parts = $Field.Split(".")
    $current = $Json
    
    foreach ($part in $parts) {
        if ($part -match "^\[(\d+)\]$") {
            $index = [int]$matches[1]
            if ($current -is [System.Collections.IList] -and $index -lt $current.Count) {
                $current = $current[$index]
            }
            else {
                return "Field '$Field': index $index out of bounds"
            }
        }
        elseif ($null -ne $current -and $current.PSObject.Properties.Name -contains $part) {
            $current = $current.$part
        }
        else {
            return "Field '$Field' not found in response"
        }
    }
    
    if ($ExpectedType) {
        $actualType = $current.GetType().Name
        $expectedDotNetType = switch ($ExpectedType) {
            "string" { "String" }
            "number" { "Double", "Int32", "Int64" }
            "boolean" { "Boolean" }
            "array" { "Object[]" }
            "object" { "PSCustomObject" }
            default { $ExpectedType }
        }
        
        if ($actualType -notin $expectedDotNetType) {
            return "Field '$Field': expected type '$ExpectedType', got '$actualType' (value: $current)"
        }
    }
    
    if ($null -ne $ExpectedValue -and $current -ne $ExpectedValue) {
        return "Field '$Field': expected value '$ExpectedValue', got '$current'"
    }
    
    return $null
}

# =============================================================================
# TEST SUITE: Health & Status
# =============================================================================

function Test-Suite-Health {
    Write-Host "`n=== HEALTH & STATUS TESTS ===" -ForegroundColor Cyan
    
    Test-ApiEndpoint `
        -Name "GET /api/health" `
        -Method "GET" `
        -Endpoint "/api/health" `
        -Description "Health check endpoint" `
        -ExpectedStatus "200" `
        -ValidateResponse {
            param($json)
            Assert-JsonField $json "status" "string"
        }
}

# =============================================================================
# TEST SUITE: Route Endpoints
# =============================================================================

function Test-Suite-Route {
    Write-Host "`n=== ROUTE API TESTS ===" -ForegroundColor Cyan
    
    # Test 1: Basic successful route request
    $body = @{
        points = $ValidPoints
        optimize = $false
        route_type = "route_1"
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "POST /api/get-route - Basic Success" `
        -Method "POST" `
        -Endpoint "/api/get-route" `
        -Description "Basic route request with valid Istanbul points" `
        -Body $body `
        -ExpectedStatus "200" `
        -ValidateResponse {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "optimized_order" "array"
            $errors += Assert-JsonField $json "route_coords" "array"
            $errors += Assert-JsonField $json "total_distance_km" "number"
            $errors += Assert-JsonField $json "estimated_walk_minutes" "number"
            $errors += Assert-JsonField $json "google_maps_link" "string"
            $errors += Assert-JsonField $json "route_type" "string"
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
    
    # Test 2: Route with optimization
    $body = @{
        points = $ValidPoints
        optimize = $true
        route_type = "route_2"
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "POST /api/get-route - With Optimization" `
        -Method "POST" `
        -Endpoint "/api/get-route" `
        -Description "Route with TSP optimization enabled" `
        -Body $body `
        -ExpectedStatus "200" `
        -ValidateResponse {
            param($json)
            Assert-JsonField $json "total_distance_km" "number"
        }
    
    # Test 3: Missing points field
    $body = @{ optimize = $false } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "POST /api/get-route - Missing Points" `
        -Method "POST" `
        -Endpoint "/api/get-route" `
        -Description "Request without points field" `
        -Body $body `
        -ExpectedStatus "400" `
        -ValidateError {
            param($json)
            Assert-JsonField $json "error" "string"
        }
    
    # Test 4: Less than 2 points
    $body = @{
        points = @($ValidPoints[0])
        optimize = $false
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "POST /api/get-route - Insufficient Points" `
        -Method "POST" `
        -Endpoint "/api/get-route" `
        -Description "Request with only 1 point" `
        -Body $body `
        -ExpectedStatus "400"
    
    # Test 5: Invalid point format
    $body = @{
        points = @("invalid", $ValidPoints[0])
        optimize = $false
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "POST /api/get-route - Invalid Point Format" `
        -Method "POST" `
        -Endpoint "/api/get-route" `
        -Description "Point not in [lat, lon] format" `
        -Body $body `
        -ExpectedStatus "400"
    
    # Test 6: Outside Istanbul boundary
    $body = @{
        points = @($ValidPoints[0], $InvalidOutsidePoint)
        optimize = $false
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "POST /api/get-route - Outside Istanbul" `
        -Method "POST" `
        -Endpoint "/api/get-route" `
        -Description "Point coordinates outside Istanbul boundaries" `
        -ExpectedStatus "400" `
        -ValidateError {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "code" "string" "outside_istanbul"
            $errors += Assert-JsonField $json "geofence" "object"
            $errors += Assert-JsonField $json "field" "string" "points"
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
}

# =============================================================================
# TEST SUITE: Route Steps
# =============================================================================

function Test-Suite-RouteSteps {
    Write-Host "`n=== ROUTE STEPS API TESTS ===" -ForegroundColor Cyan
    
    $body = @{
        points = $ValidPoints
        optimize = $false
        route_type = "route_1"
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "POST /api/get-route-steps - Basic Success" `
        -Method "POST" `
        -Endpoint "/api/get-route-steps" `
        -Description "Turn-by-turn route steps request" `
        -Body $body `
        -ExpectedStatus "200" `
        -ValidateResponse {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "steps" "array"
            $errors += Assert-JsonField $json "route_coords" "array"
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
}

# =============================================================================
# TEST SUITE: Alternative Routes
# =============================================================================

function Test-Suite-AlternativeRoutes {
    Write-Host "`n=== ALTERNATIVE ROUTES API TESTS ===" -ForegroundColor Cyan
    
    $body = @{
        points = $ValidPoints
        optimize = $false
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "POST /api/get-alternative-routes - Basic Success" `
        -Method "POST" `
        -Endpoint "/api/get-alternative-routes" `
        -Description "Request 3 alternative routes" `
        -Body $body `
        -ExpectedStatus "200" `
        -ValidateResponse {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "alternatives" "array"
            
            # Verify each alternative has required fields
            if ($json.alternatives -and $json.alternatives.Count -gt 0) {
                $alt = $json.alternatives[0]
                $errors += Assert-JsonField $alt "type" "string"
                $errors += Assert-JsonField $alt "name" "string"
                $errors += Assert-JsonField $alt "route_coords" "array"
                $errors += Assert-JsonField $alt "distance_km" "number"
                $errors += Assert-JsonField $alt "duration_minutes" "number"
            }
            
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
}

# =============================================================================
# PAYLOAD SUMMARY REPORTER
# =============================================================================

function Write-PayloadSummary {
    param([array]$TestResults)
    
    Write-Host "`n=== PAYLOAD SUMMARY ===" -ForegroundColor Cyan
    
    $grouped = $TestResults | Group-Object -Property Name | ForEach-Object {
        $first = $_.Group[0]
        [PSCustomObject]@{
            Name = $first.Name
            Endpoint = $first.Endpoint
            Method = $first.Method
            Count = $_.Count
            Passed = ($_.Group | Where-Object { $_.Status -eq "PASS" }).Count
            Failed = ($_.Group | Where-Object { $_.Status -eq "FAIL" }).Count
        }
    }
    
    $grouped | Format-Table -AutoSize Name, Method, Endpoint, Passed, Failed
}

# =============================================================================
# TEST SUITE: Error Responses
# =============================================================================

function Test-Suite-ErrorResponses {
    Write-Host "`n=== ERROR RESPONSE TESTS ===" -ForegroundColor Cyan
    
    # Test 1: no_pedestrian_path - requires graph edge case
    # Using an edge case point pair that may not connect in OSM graph
    $bodyNoPed = @{
        points = @(
            @(40.9911, 29.0289),  # Near Kadikoy ferry
            @(40.9928, 29.0060)   # Near Ayrilik Cesmesi - may have graph gaps
        )
        optimize = $false
        route_type = "route_1"
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "Error Response - no_pedestrian_path" `
        -Method "POST" `
        -Endpoint "/api/get-route" `
        -Description "Verify no_pedestrian_path error code handling" `
        -Body $bodyNoPed `
        -ExpectedStatus "400" `
        -ValidateError {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "error" "string"
            $errors += Assert-JsonField $json "code" "string"
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
    
    # Test 2: no_route_geometry - similar edge case
    Test-ApiEndpoint `
        -Name "Error Response - no_route_geometry" `
        -Method "POST" `
        -Endpoint "/api/get-route" `
        -Description "Verify no_route_geometry error code handling" `
        -Body $bodyNoPed `
        -ExpectedStatus "400" `
        -ValidateError {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "error" "string"
            $errors += Assert-JsonField $json "code" "string"
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
    
    # Test 3: outside_istanbul error - verify structure
    $body = @{
        points = @($ValidPoints[0], $InvalidOutsidePoint)
        optimize = $false
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "Error Response - outside_istanbul structure" `
        -Method "POST" `
        -Endpoint "/api/get-route" `
        -Description "Verify outside_istanbul error structure" `
        -Body $body `
        -ExpectedStatus "400" `
        -ValidateError {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "error" "string"
            $errors += Assert-JsonField $json "code" "string" "outside_istanbul"
            $errors += Assert-JsonField $json "geofence" "object"
            $errors += Assert-JsonField $json "suggestion" "object"
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
}

# =============================================================================
# TEST SUITE: Route Storage
# =============================================================================

function Test-Suite-RouteStorage {
    Write-Host "`n=== ROUTE STORAGE API TESTS ===" -ForegroundColor Cyan
    
    # First get a route to save
    $routeBody = @{
        points = $ValidPoints
        optimize = $false
        route_type = "route_1"
    } | ConvertTo-Json -Compress
    
    $routeResponse = Invoke-WebRequest -Uri "$BaseUrl/api/get-route" -Method POST -ContentType "application/json" -Body $routeBody -TimeoutSec 30 -ErrorAction Stop
    $routeData = $routeResponse.Content | ConvertFrom-Json
    
    # Test list routes
    Test-ApiEndpoint `
        -Name "GET /api/routes - List Routes" `
        -Method "GET" `
        -Endpoint "/api/routes" `
        -Description "List saved routes" `
        -ExpectedStatus "200" `
        -ValidateResponse {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "routes" "array"
            $errors += Assert-JsonField $json "count" "number"
            $errors += Assert-JsonField $json "total" "number"
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
    
    # Test save route
    $saveBody = @{
        name = "QA Test Route $(Get-Date -Format 'yyyyMMddHHmmss')"
        points = $ValidPoints
        route_coords = $routeData.route_coords
        distance_km = $routeData.total_distance_km
        duration_minutes = $routeData.estimated_walk_minutes
        route_type = "route_1"
        description = "Smoke test ile olusturuldu"
        tags = @("qa", "smoke-test")
    } | ConvertTo-Json -Compress
    
    Test-ApiEndpoint `
        -Name "POST /api/routes/save - Save Route" `
        -Method "POST" `
        -Endpoint "/api/routes/save" `
        -Description "Save a new route" `
        -Body $saveBody `
        -ExpectedStatus "200" `
        -ValidateResponse {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "status" "string" "success"
            $errors += Assert-JsonField $json "route" "object"
            $errors += Assert-JsonField $json "message" "string"
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
    
    # Test route statistics
    Test-ApiEndpoint `
        -Name "GET /api/routes/statistics - Route Stats" `
        -Method "GET" `
        -Endpoint "/api/routes/statistics" `
        -Description "Get route statistics" `
        -ExpectedStatus "200" `
        -ValidateResponse {
            param($json)
            $errors = @()
            $errors += Assert-JsonField $json "total_routes" "number"
            $errors += Assert-JsonField $json "total_distance_km" "number"
            $errors += Assert-JsonField $json "total_duration_minutes" "number"
            return ($errors | Where-Object { $_ -ne $null }) -join "; "
        }
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

function Main {
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host "  OpenRoutePlanner - Route API Smoke Test Suite" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host "Base URL: $BaseUrl" -ForegroundColor White
    Write-Host "Start Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
    Write-Host ""
    
    # Check server connectivity
    try {
        Write-TestOutput "Checking server connectivity..." "INFO"
        $healthCheck = Invoke-WebRequest -Uri "$BaseUrl/api/health" -Method GET -TimeoutSec 10 -ErrorAction Stop
        if ($healthCheck.StatusCode -eq 200) {
            Write-TestOutput "Server is reachable" "PASS"
        }
    }
    catch {
        Write-TestOutput "ERROR: Cannot connect to server at $BaseUrl" "FAIL"
        Write-TestOutput "Ensure the Flask server is running: python -m flask run" "WARN"
        return
    }
    
    # Run test suites
    Test-Suite-Health
    Test-Suite-Route
    Test-Suite-RouteSteps
    Test-Suite-AlternativeRoutes
    Test-Suite-ErrorResponses
    Test-Suite-RouteStorage
    
    # Print payload summary
    Write-PayloadSummary -TestResults $Script:TestResults
    
    # Print summary
    Write-Host "`n==================================================" -ForegroundColor Cyan
    Write-Host "  TEST SUMMARY" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
    
    $passRate = if ($Script:TotalTests -gt 0) { [math]::Round(($Script:PassedTests / $Script:TotalTests) * 100, 1) } else { 0 }
    
    Write-Host "Total Tests : $($Script:TotalTests)" -ForegroundColor White
    Write-Host "Passed     : $($Script:PassedTests)" -ForegroundColor Green
    Write-Host "Failed     : $($Script:FailedTests)" -ForegroundColor Red
    Write-Host "Pass Rate  : ${passRate}%" -ForegroundColor $(if ($passRate -ge 80) { "Green" } elseif ($passRate -ge 50) { "Yellow" } else { "Red" })
    
    if ($Script:FailedTests -gt 0) {
        Write-Host "`nFailed Tests:" -ForegroundColor Red
        foreach ($test in $Script:TestResults | Where-Object { $_.Status -eq "FAIL" }) {
            Write-Host "  - $($test.Name): $($test.Error)" -ForegroundColor Red
        }
    }
    
    # Export results
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $reportPath = "scripts/qa_route_contract_${timestamp}.json"
    
    if ($OutputFormat -eq "Json") {
        $Script:TestResults | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportPath -Encoding UTF8
        Write-Host "`nJSON report saved: $reportPath" -ForegroundColor White
    }
    
    Write-Host "`nEnd Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
    
    # Exit with appropriate code
    if ($Script:FailedTests -gt 0) {
        exit 1
    }
    else {
        exit 0
    }
}

# Run
Main