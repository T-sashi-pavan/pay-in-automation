import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from backend.app.api.uploads import upload_excel, process_upload_in_background
from backend.app.models.upload_history import UploadHistory
from backend.app.models.commission_rule import CommissionRule
from backend.app.models.slab_detail import SlabDetail

class TestUploadsApi(unittest.TestCase):
    
    @patch("backend.app.api.uploads.BackgroundTasks")
    @patch("backend.app.api.uploads.shutil")
    @patch("backend.app.api.uploads.open")
    def test_upload_excel_route_returns_processing_immediately(self, mock_open, mock_shutil, mock_bg_tasks_class):
        mock_bg_tasks = MagicMock()
        mock_db = MagicMock(spec=Session)
        
        # Mock file object
        mock_file = MagicMock()
        mock_file.filename = "test_digit_rules.xlsx"
        
        # Invoke endpoint
        with patch("backend.app.api.uploads.UploadHistory") as mock_history_class:
            mock_history_instance = MagicMock()
            mock_history_instance.id = 123
            mock_history_instance.filename = "test_digit_rules.xlsx"
            mock_history_class.return_value = mock_history_instance
            
            response = mock_db.add
            
            import asyncio
            result = asyncio.run(upload_excel(mock_bg_tasks, mock_file, mock_db))
            
        # Assertions
        self.assertEqual(result["upload_id"], 123)
        self.assertEqual(result["status"], "PROCESSING")
        self.assertEqual(result["total_records"], 0)
        
        # Verify background task is enqueued
        mock_bg_tasks.add_task.assert_called_once()
        args = mock_bg_tasks.add_task.call_args[0]
        self.assertEqual(args[0], process_upload_in_background)
        self.assertEqual(args[1], 123)
        self.assertEqual(args[3], "test_digit_rules.xlsx")

    @patch("backend.app.api.uploads.SessionLocal")
    @patch("backend.app.api.uploads.excel_parser_service")
    @patch("backend.app.api.uploads.open")
    @patch("backend.app.api.uploads.os.path.exists")
    @patch("backend.app.api.uploads.os.remove")
    def test_process_upload_in_background_workflow(self, mock_remove, mock_exists, mock_open, mock_parser, mock_session_local):
        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db
        
        # Mock UploadHistory query
        mock_history = MagicMock()
        mock_db.query().filter().first.return_value = mock_history
        
        # Mock db.execute to return inserted IDs
        mock_result = MagicMock()
        mock_result.all.return_value = [(1001,)]
        mock_db.execute.return_value = mock_result
        
        # Mock parsing result
        mock_parser.parse_workbook.return_value = [
            {
                "insurance_company": "Digit",
                "commission_type": "NON_SLAB",
                "payin_od": 15.0,
                "payout_od": 12.0,
                "slabs": []
            }
        ]
        
        mock_exists.return_value = True
        
        # Execute background task logic
        process_upload_in_background(123, "dummy_temp_path", "test_digit_rules.xlsx")
        
        # Check updates to upload history
        self.assertEqual(mock_history.company, "Digit")
        self.assertEqual(mock_history.status, "COMPLETED")
        self.assertEqual(mock_history.total_records, 1)
        mock_db.commit.assert_called()
        mock_db.close.assert_called_once()
        
        # Check file cleanup
        mock_remove.assert_called_once_with("dummy_temp_path")
