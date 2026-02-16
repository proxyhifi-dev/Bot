import json
import os
import tempfile

import requests
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from execution.fyers_adapter import FyersAdapter
from engine.mode import ModeManager, TradingMode
from engine.portfolio import Portfolio
from engine.risk import RiskManager


class TestRiskManager(unittest.TestCase):
    def test_position_size(self):
        risk = RiskManager(100000)
        qty = risk.calculate_position_size(22000, 21950)
        self.assertTrue(qty > 0)

    def test_trade_limits(self):
        risk = RiskManager(100000, max_trades_per_day=1)
        snap = risk.can_open_new_trade(__import__('datetime').datetime.now())
        self.assertFalse(snap.blocked)
        risk.register_trade(-100)
        snap_after = risk.can_open_new_trade(__import__('datetime').datetime.now())
        self.assertTrue(snap_after.blocked)


class TestPortfolio(unittest.TestCase):
    def test_add_and_close_position(self):
        pf = Portfolio()
        pf.open_trade('NIFTY', 'BUY', 10, 22000, 21950, 22100, 'PAPER')
        pnl = pf.close_trade(22100, 'Target hit')
        self.assertEqual(pnl, 1000)


class TestModeManager(unittest.TestCase):
    def test_live_requires_confirmation(self):
        mm = ModeManager(TradingMode.PAPER)
        with self.assertRaises(ValueError):
            mm.switch_mode(TradingMode.LIVE, has_open_position=False, confirm_live=False, auth_validator=lambda: True)


class TestFyersAdapter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.token_file = Path(self.temp_dir.name) / "token.json"
        self.env = {
            "FYERS_CLIENT_ID": "TESTCLIENT-100",
            "FYERS_SECRET_KEY": "SECRET",
            "FYERS_REDIRECT_URI": "https://example.com/callback",
            "FYERS_BASE_URL": "https://fyers.example.test",
            "FYERS_TOKEN_FILE": str(self.token_file),
            "FYERS_APP_TYPE": "test",
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("execution.fyers_adapter.load_dotenv", return_value=False)
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_fails_fast(self, _):
        with self.assertRaises(RuntimeError):
            FyersAdapter()

    def test_login_url_uses_base_url(self):
        with patch.dict(os.environ, self.env, clear=True):
            adapter = FyersAdapter()
            url = adapter.get_login_url(state="x")
            self.assertTrue(url.startswith("https://fyers.example.test/api/v3/generate-authcode"))
            self.assertIn("state=x", url)

    def test_token_file_corruption_recovery(self):
        self.token_file.write_text("{broken", encoding="utf-8")
        with patch.dict(os.environ, self.env, clear=True):
            adapter = FyersAdapter()
            self.assertEqual(adapter.access_token, "")
            backups = list(Path(self.temp_dir.name).glob("token.json.corrupt"))
            self.assertEqual(len(backups), 1)

    def test_retry_only_on_429_and_503(self):
        with patch.dict(os.environ, self.env, clear=True):
            adapter = FyersAdapter()
            response_429 = MagicMock(status_code=429)
            response_429.raise_for_status.side_effect = requests.HTTPError(response=MagicMock(status_code=429))
            response_200 = MagicMock(status_code=200)
            response_200.raise_for_status.return_value = None
            with patch.object(adapter.session, "request", side_effect=[response_429, response_200]) as req:
                adapter._request_with_backoff("GET", "/api/v3/profile")
                self.assertEqual(req.call_count, 2)

            response_401 = MagicMock(status_code=401)
            response_401.raise_for_status.side_effect = requests.HTTPError(response=MagicMock(status_code=401))
            with patch.object(adapter.session, "request", return_value=response_401) as req:
                with self.assertRaises(requests.HTTPError):
                    adapter._request_with_backoff("GET", "/api/v3/profile")
                self.assertEqual(req.call_count, 1)

    def test_exchange_token_uses_base_url_and_persists_token(self):
        with patch.dict(os.environ, self.env, clear=True):
            adapter = FyersAdapter()
            response = MagicMock(status_code=200)
            response.raise_for_status.return_value = None
            response.json.return_value = {"access_token": "abc-token"}
            with patch.object(adapter.session, "request", return_value=response) as req:
                adapter.exchange_auth_code("AUTH")
                called_url = req.call_args.kwargs["url"]
                self.assertEqual(called_url, "https://fyers.example.test/api/v3/token")
            saved = json.loads(self.token_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["access_token"], "abc-token")


if __name__ == '__main__':
    unittest.main()
