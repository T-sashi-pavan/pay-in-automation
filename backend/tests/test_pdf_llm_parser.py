import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import date

from backend.app.services.pdf_parser.parser import PdfParserService

class TestPdfLlmParser(unittest.TestCase):
    def setUp(self):
        self.parser = PdfParserService()

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
        
        self.assertEqual(slabs[1]["slab_from"], ">30")
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
        mock_client.chat.completions.create.return_value = mock_response
        
        all_rules = []
        usage = {"provider": None, "pages_sent": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "errors": 0}
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake_key"}):
            count = self.parser._openai_text_extract_page("some text", 0, "test.pdf", "Oriental", set(), all_rules, usage)
            
        self.assertEqual(count, 1)
        self.assertEqual(len(all_rules), 1)
        self.assertEqual(all_rules[0]["payin_od"], 22.0)
        self.assertEqual(usage["provider"], "openai")
        self.assertEqual(usage["input_tokens"], 100)
        self.assertEqual(usage["output_tokens"], 50)
