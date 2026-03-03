@echo off
echo ================================================
echo OSMnx Hata Duzeltme Script'i
echo ================================================
echo.

echo [1/3] OSMnx guncelleniyor...
pip install --upgrade osmnx

echo.
echo [2/3] NetworkX guncelleniyor...
pip install --upgrade networkx

echo.
echo [3/3] Diger bagimliliklari kontrol ediliyor...
pip install --upgrade geopandas shapely

echo.
echo ================================================
echo Tamamlandi!
echo ================================================
echo.
echo Simdi backend'i baslatin:
echo   cd backend
echo   python app.py
echo.
pause
