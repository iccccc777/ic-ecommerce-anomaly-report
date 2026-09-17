import importlib.util
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ANOMALY_MODULE = ROOT / "python" / "anomaly_utils.py"


def load_anomaly_module():
    spec = importlib.util.spec_from_file_location("anomaly_utils", ANOMALY_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AnomalyBaselineTest(unittest.TestCase):
    def test_ma3_uses_only_previous_three_days(self):
        module = load_anomaly_module()
        daily = pd.DataFrame(
            {
                "day": pd.date_range("2017-01-01", periods=5, freq="D"),
                "dau": [10, 20, 30, 40, 100],
                "pv": [100, 200, 300, 400, 1000],
                "buy": [1, 2, 3, 4, 10],
            }
        )

        result = module.build_anomaly_table(daily)

        self.assertTrue(pd.isna(result.loc[0, "dau_ma3"]))
        self.assertEqual(result.loc[1, "dau_ma3"], 10)
        self.assertEqual(result.loc[2, "dau_ma3"], 15)
        self.assertEqual(result.loc[3, "dau_ma3"], 20)
        self.assertEqual(result.loc[4, "dau_ma3"], 30)
        self.assertAlmostEqual(
            result.loc[4, "dau_pct_to_ma"],
            (100 - 30) / 30 * 100,
        )

    def test_current_day_value_does_not_change_its_own_baseline(self):
        module = load_anomaly_module()
        base = pd.DataFrame(
            {
                "day": pd.date_range("2017-01-01", periods=5, freq="D"),
                "dau": [10, 20, 30, 40, 100],
                "pv": [100, 200, 300, 400, 1000],
                "buy": [1, 2, 3, 4, 10],
            }
        )
        changed = base.copy()
        changed.loc[4, ["dau", "pv", "buy"]] = [1000, 10000, 100]

        base_result = module.build_anomaly_table(base)
        changed_result = module.build_anomaly_table(changed)

        for metric in ("dau", "pv", "buy"):
            self.assertEqual(
                base_result.loc[4, f"{metric}_ma3"],
                changed_result.loc[4, f"{metric}_ma3"],
            )


if __name__ == "__main__":
    unittest.main()
