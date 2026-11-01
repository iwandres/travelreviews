import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json
import urllib.parse
from io import BytesIO

# Set up python paths so database modules and their local imports are found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock pymongo client at module level
mock_pymongo = MagicMock()
sys.modules['pymongo'] = mock_pymongo

# Now import the server and databases
import database as db_boxoffice
import travelreviews_database as db_travelreviews
from backend.unified_server import UnifiedRequestHandler

class TestServerHandler(unittest.TestCase):

    def setUp(self):
        # Patch database function calls to verify handler routing
        self.patcher_bo_get = patch('database.get_telemetry_stats')
        self.patcher_tr_get = patch('travelreviews_database.get_telemetry_stats')
        self.patcher_bo_record = patch('database.record_telemetry_event')
        self.patcher_tr_record = patch('travelreviews_database.record_telemetry_event')
        
        self.mock_bo_get = self.patcher_bo_get.start()
        self.mock_tr_get = self.patcher_tr_get.start()
        self.mock_bo_record = self.patcher_bo_record.start()
        self.mock_tr_record = self.patcher_tr_record.start()
        
        # Configure default dictionary return values to prevent JSON serialization crashes on file sync fallbacks
        self.mock_bo_get.return_value = {}
        self.mock_tr_get.return_value = {}

    def tearDown(self):
        self.patcher_bo_get.stop()
        self.patcher_tr_get.stop()
        self.patcher_bo_record.stop()
        self.patcher_tr_record.stop()

    def make_handler(self, method, path, headers=None, body=None):
        # Helper to construct a mock request handler
        request = MagicMock()
        client_address = ('127.0.0.1', 12345)
        server = MagicMock()
        
        # Mock class instantiation
        handler = UnifiedRequestHandler.__new__(UnifiedRequestHandler)
        handler.request = request
        handler.client_address = client_address
        handler.server = server
        handler.headers = headers or {}
        
        # Populate content length for post data
        if body:
            handler.headers['Content-Length'] = str(len(body))
            
        handler.path = path
        handler.directory = os.getcwd()
        
        # Mock IO streams
        handler.rfile = BytesIO(body or b"")
        handler.wfile = BytesIO()
        
        # Mock connection and response tracking methods
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.send_error = MagicMock()
        
        return handler

    def test_get_puzzles_boxoffice(self):
        handler = self.make_handler('GET', '/api/puzzles')
        handler.do_GET()
        
        # Verify it responds 200 OK
        handler.send_response.assert_called_with(200)
        
        # Verify JSON is written
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertIsInstance(response_data, list)

    def test_get_records_referrer_travelreviews(self):
        # Setting referer to travelreviews should trigger travelreviews_database
        headers = {'Referer': 'https://punfiction.io/travelreviews/'}
        handler = self.make_handler('GET', '/api/records', headers=headers)
        
        # Mock DB response
        self.mock_tr_get.return_value = {"015": {"start": 5}}
        
        handler.do_GET()
        
        handler.send_response.assert_called_with(200)
        self.mock_tr_get.assert_called_once()
        self.mock_bo_get.assert_not_called()
        
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertEqual(response_data, {"015": {"start": 5}})

    def test_get_records_prefix_travelreviews(self):
        # URL path prefix /api/travelreviews/records should trigger travelreviews_database
        handler = self.make_handler('GET', '/api/travelreviews/records')
        
        self.mock_tr_get.return_value = {"015": {"start": 12}}
        handler.do_GET()
        
        handler.send_response.assert_called_with(200)
        self.mock_tr_get.assert_called_once()
        
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertEqual(response_data, {"015": {"start": 12}})

    def test_post_telemetry_boxoffice(self):
        payload = json.dumps({
            'event': 'start',
            'puzzle_number': '001'
        }).encode('utf-8')
        
        handler = self.make_handler('POST', '/api/records', body=payload)
        handler.do_POST()
        
        handler.send_response.assert_called_with(200)
        self.mock_bo_record.assert_called_once_with('001', 'start', 0, 1)

    def test_post_telemetry_travelreviews(self):
        payload = json.dumps({
            'event': 'solve',
            'puzzle_number': '015',
            'hints_used': 2,
            'attempts': 3
        }).encode('utf-8')
        
        handler = self.make_handler('POST', '/api/travelreviews/records', body=payload)
        handler.do_POST()
        
        handler.send_response.assert_called_with(200)
        self.mock_tr_record.assert_called_once_with('015', 'solve', 2, 3)

    def test_invalid_path_returns_404(self):
        handler = self.make_handler('GET', '/api/invalid_path_abc')
        handler.do_GET()
        
        self.assertTrue(handler.send_error.called)
        self.assertEqual(handler.send_error.call_args[0][0], 404)

    def test_get_agent_guardrails(self):
        handler = self.make_handler('GET', '/api/travelreviews/agent/guardrails')
        handler.do_GET()

        handler.send_response.assert_called_with(200)
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertIn('guardrails', response_data)
        self.assertIn('pun_positive_rules', response_data['guardrails'])
        self.assertIn('pun_negative_examples', response_data['guardrails'])
        self.assertIn('stats', response_data)

    @patch('backend.unified_server.gemini_available', True)
    @patch('backend.unified_server.get_curation_agent')
    def test_post_agent_run(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.run_pipeline.return_value = {
            "discovered_landmarks_count": 1,
            "discovered_landmarks": [{"id": "lm_1", "name": "Hagia Sophia", "location": "Istanbul, Turkey"}],
            "generated_puzzles_count": 1,
            "generated_puzzles": [{"pun": {"pun_name": "Hog-ia Sofa"}, "landmark": {"name": "Hagia Sophia"}}],
            "errors": []
        }
        mock_get_agent.return_value = mock_agent

        payload = json.dumps({"count": 1, "discover_new_landmarks": True, "art_style": "cartoon"}).encode('utf-8')
        handler = self.make_handler('POST', '/api/travelreviews/agent/run', body=payload)
        handler.do_POST()

        handler.send_response.assert_called_with(200)
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['generated_puzzles_count'], 1)
        mock_agent.run_pipeline.assert_called_once_with(
            count=1, discover_new_landmarks=True, art_style="cartoon", landmark_id=None
        )

    @patch('backend.unified_server.gemini_available', True)
    @patch('backend.unified_server.get_curation_agent')
    def test_post_agent_redo_pun(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.redo_puzzle_piece.return_value = {
            "redo_type": "pun",
            "old_pun_name": "Lover Museum",
            "new_pun_name": "Loofah Museum",
            "clue": {"id": "clue_123", "pun_name": "Loofah Museum"},
            "postcard": {"id": "pc_123", "pun_name": "Loofah Museum"}
        }
        mock_get_agent.return_value = mock_agent

        payload = json.dumps({
            "clue_id": "clue_123",
            "redo_type": "pun",
            "human_feedback": "Make it a household object"
        }).encode('utf-8')
        handler = self.make_handler('POST', '/api/travelreviews/agent/redo', body=payload)
        handler.do_POST()

        handler.send_response.assert_called_with(200)
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['new_pun_name'], 'Loofah Museum')
        mock_agent.redo_puzzle_piece.assert_called_once_with(
            clue_id="clue_123",
            redo_type="pun",
            custom_pun=None,
            human_feedback="Make it a household object",
            art_style="random",
            custom_prompt=None
        )

    @patch('backend.unified_server.get_curation_agent')
    def test_get_agent_analytics(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.get_quality_analytics.return_value = {
            "health_score": 94.5,
            "health_status": "EXCELLENT",
            "signals_summary": {
                "positive_approvals_total": 123,
                "total_redos": 1,
                "negative_declines_total": 0
            },
            "rates": {
                "puzzle_approval_rate_pct": 100.0,
                "first_pass_clean_rate_pct": 95.0
            }
        }
        mock_get_agent.return_value = mock_agent

        handler = self.make_handler('GET', '/api/travelreviews/agent/analytics')
        handler.do_GET()

        handler.send_response.assert_called_with(200)
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['health_status'], 'EXCELLENT')
        self.assertEqual(response_data['signals_summary']['positive_approvals_total'], 123)

    @patch('backend.unified_server.get_curation_agent')
    def test_post_agent_signal(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.record_signal.return_value = {
            "id": "sig_123",
            "signal_type": "approve",
            "signal_weight": 1.0,
            "first_pass_approval": True
        }
        mock_agent.get_quality_analytics.return_value = {
            "health_score": 96.0,
            "health_status": "EXCELLENT"
        }
        mock_get_agent.return_value = mock_agent

        payload = json.dumps({
            "signal_type": "approve",
            "clue_id": "clue_123",
            "postcard_id": "pc_123",
            "landmark_name": "Dubrovnik Old Town",
            "pun_name": "Dubrovnik Mold Town",
            "redo_count_at_event": 0
        }).encode('utf-8')
        handler = self.make_handler('POST', '/api/travelreviews/agent/signal', body=payload)
        handler.do_POST()

        handler.send_response.assert_called_with(200)
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['event']['signal_type'], 'approve')
        self.assertEqual(response_data['analytics']['health_score'], 96.0)

    @patch('backend.unified_server.get_curation_agent')
    def test_get_runway_alert(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.get_runway_status.return_value = {
            "enabled": True,
            "recipient_email": "iwandres@gmail.com",
            "threshold": 10,
            "staged_count": 8,
            "is_low_runway": True
        }
        mock_agent.check_and_send_runway_alert.return_value = {
            "triggered": True,
            "sent": True,
            "runway": {
                "enabled": True,
                "recipient_email": "iwandres@gmail.com",
                "threshold": 10,
                "staged_count": 8,
                "is_low_runway": True
            }
        }
        mock_get_agent.return_value = mock_agent

        handler = self.make_handler('GET', '/api/travelreviews/agent/runway_alert')
        handler.do_GET()

        handler.send_response.assert_called_with(200)
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['runway']['recipient_email'], 'iwandres@gmail.com')
        self.assertEqual(response_data['runway']['staged_count'], 8)
        mock_agent.check_and_send_runway_alert.assert_called_once_with(force=False)

    @patch('backend.unified_server.get_curation_agent')
    def test_post_runway_alert(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.update_alert_config.return_value = {
            "enabled": True,
            "recipient_email": "iwandres@gmail.com",
            "threshold": 10,
            "staged_count": 22,
            "is_low_runway": False
        }
        mock_agent.check_and_send_runway_alert.return_value = {
            "triggered": True,
            "sent": True,
            "delivery_method": "smtp (smtp.gmail.com)",
            "message": "Email sent to iwandres@gmail.com via smtp.gmail.com.",
            "runway": {
                "enabled": True,
                "recipient_email": "iwandres@gmail.com",
                "threshold": 10,
                "staged_count": 22,
                "is_low_runway": False
            }
        }
        mock_get_agent.return_value = mock_agent

        payload = json.dumps({
            "action": "test",
            "recipient_email": "iwandres@gmail.com",
            "threshold": 10
        }).encode('utf-8')
        handler = self.make_handler('POST', '/api/travelreviews/agent/runway_alert', body=payload)
        handler.do_POST()

        handler.send_response.assert_called_with(200)
        response_data = json.loads(handler.wfile.getvalue().decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertTrue(response_data['alert_result']['sent'])
        mock_agent.check_and_send_runway_alert.assert_called_once_with(force=True)

    def test_sanitize_travelreviews_puzzles_enriches_coordinates(self):
        from backend.unified_server import sanitize_travelreviews_puzzles
        sample = [
            {
                "puzzle_number": "001",
                "boss_original_title": "Eiffel Tower",
                "boss_pun_title": "Waffle Tower"
            }
        ]
        result = sanitize_travelreviews_puzzles(sample)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["lat"], 48.8584, places=2)
        self.assertAlmostEqual(result[0]["lng"], 2.2945, places=2)
        self.assertTrue(bool(result[0].get("location")))

    def test_all_daily_games_and_landmarks_have_valid_coordinates(self):
        from backend.unified_server import DAILY_GAMES_FILE, LANDMARKS_FILE, load_json
        daily_games = load_json(DAILY_GAMES_FILE, [])
        landmarks = load_json(LANDMARKS_FILE, [])
        self.assertGreater(len(daily_games), 100)
        self.assertGreater(len(landmarks), 400)
        for p in daily_games:
            self.assertIsInstance(p.get("lat"), (int, float), f"Missing lat on puzzle {p.get('puzzle_number')}")
            self.assertIsInstance(p.get("lng"), (int, float), f"Missing lng on puzzle {p.get('puzzle_number')}")
            self.assertTrue(-90 <= p["lat"] <= 90)
            self.assertTrue(-180 <= p["lng"] <= 180)
        for lm in landmarks:
            self.assertIsInstance(lm.get("lat"), (int, float), f"Missing lat on landmark {lm.get('name')}")
            self.assertIsInstance(lm.get("lng"), (int, float), f"Missing lng on landmark {lm.get('name')}")
            self.assertTrue(-90 <= lm["lat"] <= 90)
            self.assertTrue(-180 <= lm["lng"] <= 180)

if __name__ == '__main__':
    unittest.main()
