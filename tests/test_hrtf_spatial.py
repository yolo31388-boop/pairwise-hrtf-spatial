import pytest
from audio import hrtf_spatial as mod

CASES = [
    ("azimuth", 'm.azimuth_bin(90, 8) == 2'),
    ("coord", 'm.coord_convert((1, 2, 3)) == (2, 1, 3)'),
    ("headtrack", 'm.headtrack_comp(10, 9, 2) == -1'),
    ("near", 'm.near_field(1, 2) is True'),
    ("occlusion", 'm.occlusion_rays(2, 4) == approx(0.5)'),
    ("low", 'm.low_freq_keep(100, 200) == 200'),
    ("block", 'm.block_size(48000, 10) == 480'),
    ("channel", 'm.channel_map(0, "LR") == "L"'),
    ("lerp", 'm.dataset_lerp(0, 10, 0.5) == approx(5.0)'),
    ("reverb", 'm.reverb_order(1, 2) is True'),
    ("cache", 'm.cache_key("d", "s") == "d:s"'),
    ("tear", 'm.thread_tear(1, 2) is True'),
    ("compression", 'm.compression_order(1, 2) is True'),
    ("itd", 'm.itd_delay(90, 1) == approx(0.5)'),
    ("ild", 'm.ild_gain(90, 1) == approx(0.5)')
]

@pytest.mark.parametrize("name,expr", CASES, ids=[c[0] for c in CASES])
def test_contract(name, expr):
    assert eval(expr, {"m": mod, "approx": pytest.approx})
