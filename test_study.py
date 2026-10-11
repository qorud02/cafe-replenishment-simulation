"""Targeted scientific checks for event timing, conservation and demand law."""
import unittest
import numpy as np
from study import consume, forecast_expiry, simulate, make_demand, forecasts, P


class SimulatorTests(unittest.TestCase):
    def test_fifo(self):
        stock = np.array([[[3., 5., 8.]]])
        served = consume(stock, np.array([[6.]]))
        np.testing.assert_array_equal(served, [[6.]])
        np.testing.assert_array_equal(stock, [[[0., 2., 8.]]])

    def test_projected_expiry_not_all_older_inventory(self):
        stock = np.array([[[10., 7., 20.]]])
        np.testing.assert_allclose(forecast_expiry(stock, np.array([6., 5.])), [[6.]])
        np.testing.assert_array_equal(stock, [[[10., 7., 20.]]])

    def test_lead_time_and_shortage(self):
        # Day zero has no available inventory, even after placing an order.
        result = simulate(np.array([[5]]), pack=20, life=2, cv=0,
                          penalty_ratio=3, z_values=[0], burn_in=0)
        self.assertEqual(result['served_per_day'][0,0], 0)
        self.assertEqual(result['unmet_per_day'][0,0], 5)
        self.assertEqual(result['purchased_per_day'][0,0] % 20, 0)

    def test_expiry_and_boundary_conservation(self):
        # No demand: stock arriving on day one expires at the end of day two.
        result = simulate(np.zeros((1,3), dtype=int), pack=20, life=2, cv=0,
                          penalty_ratio=3, z_values=[0], burn_in=0)
        purchased = result['purchased_per_day'][0,0] * 3
        expired = result['expired_per_day'][0,0] * 3
        self.assertGreater(expired, 0)
        self.assertEqual(purchased, expired + result['final_inventory'][0,0] + result['final_pipeline'][0,0])

    def test_zero_demand_waste_not_double_charged(self):
        result = simulate(np.zeros((1,3), dtype=int), pack=20, life=2, cv=0,
                          penalty_ratio=3, z_values=[0], burn_in=0)
        expected = result['purchased_per_day']*P['purchase_cost_krw_per_unit'] + result['inventory_per_day']*P['holding_cost_krw_per_unit_day']
        np.testing.assert_allclose(result['cost_per_day'], expected)

    def test_reproducible_disjoint_streams(self):
        a = make_demand(8,20,.35,1)
        np.testing.assert_array_equal(a, make_demand(8,20,.35,1))
        self.assertFalse(np.array_equal(a, make_demand(8,20,.35,2)))

    def test_demand_moments(self):
        # A large independent sample checks the implemented compound law.
        for cv in [0., .7]:
            sample = make_demand(200000,1,cv,456)[:,0]
            mean, variance = forecasts(1,cv)
            self.assertLess(abs(sample.mean()-mean[0]), 5*np.sqrt(variance[0]/len(sample)))
            self.assertLess(abs(sample.var()/variance[0]-1), .025)

    def test_paired_z_vectorization(self):
        demand = make_demand(4,20,.7,44)
        params = dict(pack=60,life=3,cv=.7,penalty_ratio=10,burn_in=3,expiry_adjusted=True)
        batch = simulate(demand,z_values=[0,1],**params)
        for j,z in enumerate([0,1]):
            scalar = simulate(demand,z_values=[z],**params)
            for key in batch:
                np.testing.assert_allclose(batch[key][:,j],scalar[key][:,0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
