import hashlib
import os
import tempfile
import unittest

from engine.mode import ModeManager, TradingMode
from engine.portfolio import Portfolio
from engine.risk import RiskManager
from execution.fyers_adapter import FyersAdapter


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
    def test_app_id_hash(self):
        os.environ['FYERS_CLIENT_ID'] = 'ABCD-100'
        os.environ['FYERS_SECRET_KEY'] = 'SECRET'
        os.environ['FYERS_REDIRECT_URI'] = 'http://127.0.0.1:8000/auth/callback'
        fa = FyersAdapter()
        expected = hashlib.sha256(b'ABCD-100:SECRET').hexdigest()
        self.assertEqual(fa._app_id_hash(), expected)

    def test_persist_access_token(self):
        fa = FyersAdapter()
        fa.access_token = 'token_123'
        with tempfile.TemporaryDirectory() as td:
            env_file = os.path.join(td, '.env')
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write('X=1\nFYERS_ACCESS_TOKEN=old\n')
            ok = fa.persist_access_token(env_file)
            self.assertTrue(ok)
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn('FYERS_ACCESS_TOKEN=token_123', content)


if __name__ == '__main__':
    unittest.main()
