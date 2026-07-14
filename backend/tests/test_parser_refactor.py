from backend.app.services.excel_parser.parser import split_product_range, is_slab_rule

def test_split_product_range():
    # Test cases from user prompt
    assert split_product_range("GCV >3.5<=7.5") == ("GCV", ">3.5<=7.5")
    assert split_product_range("LCV Upto 2.5T") == ("LCV", "Upto 2.5T")
    assert split_product_range("PRIVATE CAR >1500CC") == ("PRIVATE CAR", ">1500CC")
    
    # Other common range formats
    assert split_product_range("GCV 3.5-7.5 T") == ("GCV", "3.5-7.5 T")
    assert split_product_range("PCV 1500 CC") == ("PCV", "1500 CC")
    
    # Non-range cases
    assert split_product_range("TWO WHEELER") == ("TWO WHEELER", None)
    assert split_product_range("PRIVATE CAR") == ("PRIVATE CAR", None)
    assert split_product_range("") == ("", None)
    assert split_product_range(None) == ("", None)

def test_is_slab_rule():
    # Check sheet name
    assert is_slab_rule("Slab Grid", [], {}, {}) is True
    
    # Check headers
    assert is_slab_rule("Grid", ["Premium Slab", "Insurer"], {}, {}) is True
    assert is_slab_rule("Grid", ["Range", "LOB"], {}, {}) is False
    assert is_slab_rule("Grid", ["Vehicle Age", "LOB"], {}, {}) is False
    
    # Check values of slab_from/slab_to
    assert is_slab_rule("Grid", [], {}, {"slab_from": 100}) is True
    assert is_slab_rule("Grid", [], {}, {"slab_to": 200}) is True
    
    # Check ranges in product, subclass or remarks (should be False now as they are business filters)
    assert is_slab_rule("Grid", [], {"product": "GCP >3.5<=7.5"}, {}) is False
    assert is_slab_rule("Grid", [], {"sub_class": "Upto 2.5T"}, {}) is False
    assert is_slab_rule("Grid", [], {"remarks": "SI > 50000"}, {}) is False
    assert is_slab_rule("Grid", [], {"product": "GCV"}, {}) is False
