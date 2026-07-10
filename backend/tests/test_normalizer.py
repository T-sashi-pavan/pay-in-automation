from backend.app.services.normalizer.normalizer import ValueNormalizer

def test_normalize_vehicle_age():
    # Ranges
    assert ValueNormalizer.normalize_vehicle_age("5-10 YEARS") == (5, 10)
    assert ValueNormalizer.normalize_vehicle_age("3 TO 5") == (3, 5)
    # Upto scenarios
    assert ValueNormalizer.normalize_vehicle_age("UPTO 5 YEARS") == (0, 5)
    assert ValueNormalizer.normalize_vehicle_age("<= 3") == (0, 3)
    # Above scenarios
    assert ValueNormalizer.normalize_vehicle_age("5+") == (5, 99)
    assert ValueNormalizer.normalize_vehicle_age("> 3 YEARS") == (3, 99)
    # Single values
    assert ValueNormalizer.normalize_vehicle_age(5) == (5, 5)

def test_normalize_states():
    assert ValueNormalizer.normalize_states("AP,TS,TN") == "AP, TS, TN"
    assert ValueNormalizer.normalize_states("AP / TS / TN") == "AP, TS, TN"
    assert ValueNormalizer.normalize_states("AP;TS;TN") == "AP, TS, TN"
    # New coverage
    assert ValueNormalizer.normalize_states("ANDHRA PRADESH") == "AP"
    assert ValueNormalizer.normalize_states("HARYANA ( HR RTO ONLY)") == "HR"
    assert ValueNormalizer.normalize_states("ALL EXCEPT (DL, MP, CG)") == "ALL EXCEPT (DL, MP, CG)"


def test_normalize_percentage():
    assert ValueNormalizer.normalize_percentage("15%") == 15.0
    assert ValueNormalizer.normalize_percentage("15.5 %") == 15.5
    assert ValueNormalizer.normalize_percentage(12.5) == 12.5
