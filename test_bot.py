import hashlib
import os
import tempfile
import unittest

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




class TestFyersAdapterAuthRouting(unittest.TestCase):
    def setUp(self):
        self.prev_env = dict(os.environ)
        os.environ["FYERS_CLIENT_ID"] = "ABCD1234-100"
        os.environ["FYERS_SECRET_KEY"] = "secret"
        os.environ["FYERS_REDIRECT_URI"] = "http://127.0.0.1"
        os.environ["FYERS_BASE_URL"] = "https://api-t1.fyers.in"
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            self.token_path = tmp.name
        os.environ["FYERS_TOKEN_FILE"] = self.token_path

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.prev_env)
        try:
            os.remove(self.token_path)
        except OSError:
            pass

    def test_auto_auth_path(self):
        from execution.fyers_adapter import FyersAdapter

        os.environ["FYERS_AUTO_AUTH"] = "true"
        adapter = FyersAdapter()
        called = {"auto": False}

        adapter.validate_token = lambda force=False: False

        def _auto():
            called["auto"] = True
            return True

        adapter.authenticate_auto = _auto

        self.assertTrue(adapter.ensure_authenticated(interactive=False))
        self.assertTrue(called["auto"])

    def test_interactive_auth_path(self):
        from execution.fyers_adapter import FyersAdapter

        os.environ["FYERS_AUTO_AUTH"] = "false"
        adapter = FyersAdapter()
        called = {"interactive": False}

        adapter.validate_token = lambda force=False: False

        def _interactive():
            called["interactive"] = True
            return True

        adapter.authenticate_interactive = _interactive

        self.assertTrue(adapter.ensure_authenticated(interactive=True))
        self.assertTrue(called["interactive"])

if __name__ == '__main__':
    unittest.main()
