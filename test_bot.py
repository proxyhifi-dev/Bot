import unittest
from engine.risk import RiskManager
from engine.portfolio import Portfolio
from engine.execution import ExecutionEngine

class TestRiskManager(unittest.TestCase):
    def test_position_size(self):
        risk = RiskManager(100000, risk_per_trade=0.01, max_daily_loss=0.03)
        qty = risk.calculate_position_size(22000, 21950)
        self.assertTrue(qty > 0)

    def test_can_trade(self):
        risk = RiskManager(100000, risk_per_trade=0.01, max_daily_loss=0.03)
        self.assertTrue(risk.can_trade())
        risk.update_loss(4000)
        self.assertFalse(risk.can_trade())

class TestPortfolio(unittest.TestCase):
    def test_add_and_close_position(self):
        pf = Portfolio()
        pf.add_position('NIFTY', 10, 22000)
        pnl = pf.close_position('NIFTY', 22100)
        self.assertEqual(pnl, 1000)

class TestExecutionEngine(unittest.TestCase):
    def test_execute_and_close_trade(self):
        risk = RiskManager(100000, risk_per_trade=0.01, max_daily_loss=0.03)
        pf = Portfolio()
        exec_engine = ExecutionEngine(risk, pf)
        exec_engine.execute_trade('NIFTY', 'BUY', 22000, 21950)
        exec_engine.close_trade('NIFTY', 22100)

if __name__ == '__main__':
    unittest.main()
