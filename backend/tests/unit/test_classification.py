"""
Test klasifikasi ADI/CV² → kuadran Syntetos-Boylan (docs/ARCHITECTURE.md §6.2).
"""
from app.services.forecasting.legacy.classification import classify


def test_smooth_pattern_classified_correctly(smooth_df):
    profile = classify(smooth_df)
    assert profile.demand_class == "smooth"
    assert profile.adi < 1.32
    assert profile.cv2 < 0.49


def test_erratic_pattern_classified_correctly(erratic_df):
    profile = classify(erratic_df)
    assert profile.demand_class == "erratic"
    assert profile.adi < 1.32
    assert profile.cv2 >= 0.49


def test_intermittent_pattern_classified_correctly(intermittent_df):
    profile = classify(intermittent_df)
    assert profile.demand_class == "intermittent"
    assert profile.adi >= 1.32
    assert profile.cv2 < 0.49


def test_lumpy_pattern_classified_correctly(lumpy_df):
    profile = classify(lumpy_df)
    assert profile.demand_class == "lumpy"
    assert profile.adi >= 1.32
    assert profile.cv2 >= 0.49
