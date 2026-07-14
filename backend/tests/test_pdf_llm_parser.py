import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import date

from backend.app.services.pdf_parser.parser import PdfParserService

class TestPdfLlmParser(unittest.TestCase):
    def setUp(self):
        self.parser = PdfParserService()

    def test_clean_numeric_boundary(self):
        clean = self.parser._clean_numeric_boundary
        self.assertEqual(clean(">40"), 40.0)
        self.assertEqual(clean(">40%"), 40.0)
        self.assertEqual(clean("1.5 Lakh"), 150000.0)
        self.assertEqual(clean("3 LAKHS"), 300000.0)
        self.assertEqual(clean("OPEN"), None)
        self.assertEqual(clean("NA"), None)
        self.assertEqual(clean(None), None)
        self.assertEqual(clean("40+"), 40.0)
        self.assertEqual(clean(">= 50%"), 50.0)
        self.assertEqual(clean("1000 cc"), 1000.0)
        self.assertEqual(clean("1500 kg"), 1500.0)

    def test_llm_row_to_rule_non_motor_is_ignored(self):
        row = {
            "lob": "Health",
            "insurer": "Oriental",
            "commission_type": "NON_SLAB"
        }
        rule = self.parser._llm_row_to_rule(row, "Oriental", "test.pdf", 1, set())
        self.assertIsNone(rule)

    def test_llm_row_to_rule_defaults_and_fields(self):
        row = {
            "lob": "Motor",
            "insurer": "Oriental",
            "product": None, # Should default to ALL
            "sub_product": None, # Should default to NA
            "policy_type": "", # Should default to ALL
            "plan_type": "", # Should default to ALL
            "file_type": None, # Should default to ALL
            "make": "Maruti",
            "model": "Swift",
            "fuel_type": "Petrol",
            "cpa": "YES",
            "ncb": "NO",
            "vehicle_age": "UPTO 5 YEARS",
            "state": "Maharashtra, Gujarat, Delhi",
            "remarks": "Footnote 1",
            "commission_type": "NON_SLAB",
            "payin_od": 15.0,
            "payout_od": None, # Should default to 15 * 0.8 = 12.0
            "payin_tp": 5.0,
            "payout_tp": 4.0, # Explicitly specified
            "explanation": "This is a test rule"
        }
        rule = self.parser._llm_row_to_rule(row, "Oriental", "test.pdf", 1, set())
        self.assertIsNotNone(rule)
        self.assertEqual(rule["lob"], "Motor")
        self.assertEqual(rule["insurance_company"], "Oriental")
        self.assertEqual(rule["product"], "ALL")
        self.assertEqual(rule["sub_product"], "NA")
        self.assertEqual(rule["policy_type"], "ALL")
        self.assertEqual(rule["plan_type"], "ALL")
        self.assertEqual(rule["file_type"], "ALL")
        self.assertEqual(rule["make"], "Maruti")
        self.assertEqual(rule["model"], "Swift")
        self.assertEqual(rule["fuel_type"], "Petrol")
        self.assertEqual(rule["cpa_status"], "YES")
        self.assertEqual(rule["ncb_status"], "NO")
        self.assertEqual(rule["vehicle_age_from"], 0)
        self.assertEqual(rule["vehicle_age_to"], 5)
        self.assertEqual(rule["state"], "MH, GJ, DL")
        self.assertEqual(rule["remarks"], "Footnote 1")
        self.assertEqual(rule["payin_od"], 15.0)
        self.assertEqual(rule["payout_od"], 12.0)
        self.assertEqual(rule["payin_tp"], 5.0)
        self.assertEqual(rule["payout_tp"], 4.0)
        
        # Verify explanation maps to warnings list
        self.assertIn("Source Rule: This is a test rule", rule["warnings"])

    def test_llm_row_to_rule_slabs_parsing(self):
        row = {
            "lob": "Motor",
            "insurer": "Oriental",
            "commission_type": "SLAB",
            "slabs": [
                {
                    "payin_type": "PERCENTAGE",
                    "premium_type": "OD",
                    "slab_from": 0,
                    "slab_to": "30%",
                    "payin_od": 20.0,
                    "payout_od": None, # Default to 16.0
                    "payin_tp": None,
                    "payout_tp": None,
                    "payin_net": None,
                    "payout_net": None,
                    "condition_field": "Discount",
                    "operator": "<=",
                    "value": 30,
                    "original_text": "Discount <= 30%"
                },
                {
                    "payin_type": "PERCENTAGE",
                    "premium_type": "OD",
                    "slab_from": ">30",
                    "slab_to": "OPEN",
                    "payin_od": 15.0,
                    "payout_od": 12.0,
                    "payin_tp": None,
                    "payout_tp": None,
                    "payin_net": None,
                    "payout_net": None,
                    "condition_field": "Discount",
                    "operator": ">",
                    "value": 30,
                    "original_text": "Discount > 30%"
                }
            ]
        }
        rule = self.parser._llm_row_to_rule(row, "Oriental", "test.pdf", 1, set())
        self.assertIsNotNone(rule)
        self.assertEqual(rule["commission_type"], "SLAB")
        self.assertTrue(rule["slab_configuration"])
        self.assertIsNone(rule["payin_od"])
        
        slabs = rule["slabs"]
        self.assertEqual(len(slabs), 2)
        
        self.assertEqual(slabs[0]["slab_from"], 0.0)
        self.assertEqual(slabs[0]["slab_to"], 30.0)
        self.assertEqual(slabs[0]["payin_od"], 20.0)
        self.assertEqual(slabs[0]["payout_od"], 16.0)
        
        self.assertEqual(slabs[1]["slab_from"], 30.0)
        self.assertIsNone(slabs[1]["slab_to"]) # OPEN maps to None
        self.assertEqual(slabs[1]["payin_od"], 15.0)
        self.assertEqual(slabs[1]["payout_od"], 12.0)

    @patch("openai.OpenAI")
    def test_openai_text_extract_page(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '{"rows": [{"lob": "Motor", "insurer": "Oriental", "commission_type": "NON_SLAB", "payin_od": 22.0}]}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        
        mock_raw_response = MagicMock()
        mock_raw_response.headers = {
            "x-ratelimit-remaining-tokens": "5000",
            "x-ratelimit-remaining-requests": "200",
            "x-ratelimit-limit-tokens": "100000",
            "x-ratelimit-limit-requests": "1000"
        }
        mock_raw_response.parse.return_value = mock_response
        mock_client.with_raw_response.chat.completions.create.return_value = mock_raw_response
        
        all_rules = []
        usage = {
            "provider": None,
            "pages_sent": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "errors": 0,
            "remaining_tokens": "N/A",
            "remaining_requests": "N/A",
            "limit_tokens": "N/A",
            "limit_requests": "N/A"
        }
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake_key"}):
            count = self.parser._openai_text_extract_page("some text", 0, "test.pdf", "Oriental", set(), all_rules, usage)
            
        self.assertEqual(count, 1)
        self.assertEqual(len(all_rules), 1)
        self.assertEqual(all_rules[0]["payin_od"], 22.0)
        self.assertEqual(usage["provider"], "openai")
        self.assertEqual(usage["input_tokens"], 100)
        self.assertEqual(usage["output_tokens"], 50)
        self.assertEqual(usage["remaining_tokens"], "5000")

    def test_llm_row_to_rule_advanced_inferences_and_slab_redesign(self):
        # 1. Test Inferences for product, subclass, policy/plan type, NCB, and CPA
        row = {
            "lob": "Motor",
            "insurer": "Oriental",
            "product": "ALL",
            "sub_class": "ALL",
            "policy_type": "ALL",
            "plan_type": "ALL",
            "ncb": "ALL",
            "cpa": "ALL",
            "source": "Private Car Stand Alone Own Damage with NCB cases only with CPA Owner Driver cover",
            "commission_type": "NON_SLAB",
            "payin_od": 10.0
        }
        rule = self.parser._llm_row_to_rule(row, "Oriental", "test.pdf", 1, set())
        self.assertIsNotNone(rule)
        self.assertEqual(rule["product"], "Private Car")
        self.assertEqual(rule["sub_class"], "Private Car")
        self.assertEqual(rule["policy_type"], "Standalone Own Damage")
        self.assertEqual(rule["plan_type"], "Stand Alone Own Damage Policy")
        self.assertEqual(rule["ncb_status"], "NCB cases only")
        self.assertEqual(rule["cpa_status"], "with CPA")

        # 2. Test categorical slabs flattening to NON_SLAB
        row_with_cat_slabs = {
            "lob": "Motor",
            "insurer": "Oriental",
            "commission_type": "SLAB",
            "product": "Two Wheeler",
            "source": "With NCB gets 20% OD, Without NCB gets 15% OD",
            "slabs": [
                {
                    "payin_type": "PERCENTAGE",
                    "premium_type": "OD",
                    "slab_from": "With NCB",
                    "slab_to": "With NCB",
                    "payin_od": 20.0,
                    "condition_field": "NCB Status",
                    "original_text": "With NCB"
                },
                {
                    "payin_type": "PERCENTAGE",
                    "premium_type": "OD",
                    "slab_from": "Without NCB",
                    "slab_to": "Without NCB",
                    "payin_od": 15.0,
                    "condition_field": "NCB Status",
                    "original_text": "Without NCB"
                }
            ]
        }
        rule_cat = self.parser._llm_row_to_rule(row_with_cat_slabs, "Oriental", "test.pdf", 1, set())
        self.assertIsNotNone(rule_cat)
        # Should be flattened/overridden to NON_SLAB
        self.assertEqual(rule_cat["commission_type"], "NON_SLAB")
        self.assertFalse(rule_cat["slab_configuration"])
        self.assertEqual(rule_cat["payin_od"], 20.0) # rate of first slab
        self.assertEqual(rule_cat["ncb_status"], "With NCB") # mapped to ncb_status
        self.assertEqual(len(rule_cat["slabs"]), 0)
        # Warning explanation check
        explanation_warning = [w for w in rule_cat["warnings"] if "Stored as NON_SLAB" in w]
        self.assertTrue(len(explanation_warning) > 0)

    def test_group_and_merge_pdf_rules(self):
        # Create separate rules representing slab tiers split by the LLM
        r1 = {
            "lob": "Motor",
            "insurer": "Oriental",
            "insurance_company": "Oriental",
            "product": "Private Car",
            "policy_type": "Comprehensive",
            "plan_type": "Package Policy",
            "commission_type": "SLAB",
            "slab_configuration": True,
            "source": "Discount up to 30%",
            "warnings": [],
            "slabs": [
                {
                    "payin_type": "PERCENTAGE",
                    "premium_type": "OD",
                    "slab_from": 0.0,
                    "slab_to": 30.0,
                    "payin_od": 20.0,
                    "condition_field": "Discount",
                    "original_text": "Discount up to 30%"
                }
            ]
        }
        r2 = {
            "lob": "Motor",
            "insurer": "Oriental",
            "insurance_company": "Oriental",
            "product": "Private Car",
            "policy_type": "Comprehensive",
            "plan_type": "Package Policy",
            "commission_type": "SLAB",
            "slab_configuration": True,
            "source": "Discount >30% to 60%",
            "warnings": [],
            "slabs": [
                {
                    "payin_type": "PERCENTAGE",
                    "premium_type": "OD",
                    "slab_from": 30.0,
                    "slab_to": 60.0,
                    "payin_od": 15.0,
                    "condition_field": "Discount",
                    "original_text": "Discount >30% to 60%"
                }
            ]
        }
        
        merged = self.parser._group_and_merge_pdf_rules([r1, r2])
        self.assertEqual(len(merged), 1)
        m_rule = merged[0]
        self.assertEqual(m_rule["commission_type"], "SLAB")
        self.assertEqual(len(m_rule["slabs"]), 2)
        self.assertEqual(m_rule["slabs"][0]["slab_to"], 30.0)
        self.assertEqual(m_rule["slabs"][1]["slab_to"], 60.0)
        self.assertIn("Discount up to 30%", m_rule["source"])
        self.assertIn("Discount >30% to 60%", m_rule["source"])

    def test_is_rule_empty_of_rates(self):
        empty_rule = {
            "payin_od": None,
            "payin_tp": None,
            "payin_net": None,
            "slabs": []
        }
        self.assertTrue(self.parser._is_rule_empty_of_rates(empty_rule))
        
        non_empty_rule = {
            "payin_od": 15.0,
            "payin_tp": None,
            "payin_net": None,
            "slabs": []
        }
        self.assertFalse(self.parser._is_rule_empty_of_rates(non_empty_rule))
        
        slab_rule = {
            "payin_od": None,
            "payin_tp": None,
            "payin_net": None,
            "slabs": [
                {
                    "payin_od": 20.0,
                    "payin_tp": None,
                    "payin_net": None
                }
            ]
        }
        self.assertFalse(self.parser._is_rule_empty_of_rates(slab_rule))
