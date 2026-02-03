import unittest
from unittest.mock import MagicMock, patch
import json
from freshdesk_client import FreshdeskClient
from report_generator import generate_report
import os
import pandas as pd

class TestFreshdeskScraper(unittest.TestCase):
    def setUp(self):
        self.client = FreshdeskClient("fake.freshdesk.com", "fake_key")

    @patch('requests.Session.get')
    def test_search_pagination(self, mock_get):
        # Mock response for Page 1 (30 results)
        page1_data = {
            "results": [{"id": i, "subject": f"Ticket {i}"} for i in range(1, 31)]
        }
        # Mock response for Page 2 (5 results)
        page2_data = {
            "results": [{"id": i, "subject": f"Ticket {i}"} for i in range(31, 36)]
        }
        
        # Configure side effect for successive calls
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: page1_data), # Page 1
            MagicMock(status_code=200, json=lambda: page2_data)  # Page 2
        ]

        tickets = self.client.search_tickets("test")
        
        self.assertEqual(len(tickets), 35)
        self.assertEqual(tickets[0]['id'], 1)
        self.assertEqual(tickets[-1]['id'], 35)
        print("\nTest Search Pagination: SUCCESS (Found 35 tickets across 2 pages)")

    @patch('requests.Session.get')
    def test_get_ticket_details(self, mock_get):
        mock_ticket = {
            "id": 101,
            "subject": "Help me",
            "description_text": "I need help",
            "conversations": [
                {"body_text": "Sure", "user_id": 999, "created_at": "2023-01-01T10:00:00Z"},
                {"body_text": "Thanks", "user_id": 101, "created_at": "2023-01-01T11:00:00Z"}
            ]
        }
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_ticket)
        
        details = self.client.get_ticket_details(101)
        self.assertEqual(details['id'], 101)
        self.assertEqual(len(details['conversations']), 2)
        print("Test Get Details: SUCCESS")

    def test_report_generation(self):
        # Create dummy data
        tickets = [
            {
                "id": 1,
                "subject": "Test Ticket",
                "status": 2,
                "priority": 1,
                "responder_id": 55,
                "created_at": "2023-01-01",
                "description_text": "Initial Problem",
                "conversations": [
                    {"body_text": "Reply 1", "user_id": 2, "created_at": "2023-01-02", "private": False}
                ]
            }
        ]
        
        filename = "test_report.xlsx"
        generate_report(tickets, filename)
        
        # Verify file exists and has content
        df = pd.read_excel(filename)
        self.assertEqual(len(df), 1)
        self.assertTrue("Initial Problem" in df.iloc[0]['Full Conversation'])
        self.assertTrue("Reply 1" in df.iloc[0]['Full Conversation'])
        
        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)
            
        print("Test Report Generation: SUCCESS")

if __name__ == '__main__':
    unittest.main()
