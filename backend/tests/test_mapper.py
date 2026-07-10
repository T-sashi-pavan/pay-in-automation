from backend.app.services.mapping_engine.mapper import ColumnMapper

def test_column_mapper():
    mapper = ColumnMapper()
    
    headers = ["Line of Business", "Insurer", "Product Name", "Policy Type", "Age of Vehicle", "States"]
    resolved = mapper.resolve_headers(headers)
    
    assert resolved.get("lob") == "Line of Business"
    assert resolved.get("insurance_company") == "Insurer"
    assert resolved.get("product") == "Product Name"
    assert resolved.get("policy_type") == "Policy Type"
    assert resolved.get("vehicle_age") == "Age of Vehicle"
    assert resolved.get("state") == "States"
