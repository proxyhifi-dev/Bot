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


if __name__ == '__main__':
    unittest.main()
