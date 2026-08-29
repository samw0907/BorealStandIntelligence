# boreal-stand-intelligence/tests/test_luke_msnfi.py
"""fetch_msnfi URL construction and msnfi_stand_medians nodata handling (A5c)."""

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from fi_forest_data.luke import _theme_url, fetch_dtw
from src.a_stand_estimation import msnfi_stand_medians


def test_theme_url_known_theme_and_year():
    url = _theme_url("volume", 2023)
    assert url.endswith("/vmi/2023/tilavuus_vmi1x_1923.tif")


def test_theme_url_rejects_unknown_theme_and_year():
    with pytest.raises(KeyError):
        _theme_url("carbon", 2023)
    with pytest.raises(KeyError):
        _theme_url("volume", 2099)


def test_fetch_dtw_not_implemented():
    with pytest.raises(NotImplementedError):
        fetch_dtw(1.0, None)


def test_msnfi_stand_medians_masks_nodata_and_scales(tmp_path):
    x0, y0 = 600000, 6806000
    arr = np.full((20, 20), 150, dtype="uint16")
    arr[:, 10:] = 32767            # half the raster is "not forestry land"
    tif = tmp_path / "msnfi.tif"
    with rasterio.open(tif, "w", driver="GTiff", crs="EPSG:3067",
                       transform=from_origin(x0, y0 + 20 * 16, 16, 16),
                       width=20, height=20, count=1, dtype="uint16",
                       nodata=32767) as dst:
        dst.write(arr, 1)

    stands = gpd.GeoDataFrame(
        {"standid": [1, 2]},
        geometry=[box(x0 + 16, y0 + 16, x0 + 128, y0 + 128),        # in the valid half
                  box(x0 + 176, y0 + 16, x0 + 300, y0 + 128)],       # in the nodata half
        crs="EPSG:3067",
    ).set_index("standid")

    med = msnfi_stand_medians(stands, tif, scale=0.1)
    assert np.isclose(med.loc[1], 15.0)      # 150 dm * 0.1 = 15 m
    assert np.isnan(med.loc[2])              # only nodata under this stand
