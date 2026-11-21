import time
import unittest

from centerion.compute_engine import ComputeEngine


class ComputeEngineTests(unittest.TestCase):
    def test_registered_handler_runs(self):
        engine = ComputeEngine(max_workers=1, max_pending=2)
        engine.register("sum", lambda payload: payload["a"] + payload["b"])
        task = engine.submit("sum", {"a": 2, "b": 3})
        for _ in range(100):
            result = engine.get_task(task["task_id"])
            if result["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.01)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["result"], 5)
        engine.close()

    def test_unregistered_handler_is_rejected(self):
        engine = ComputeEngine()
        with self.assertRaises(ValueError):
            engine.submit("arbitrary-code", {})
        engine.close()

    def test_handler_failure_is_recorded(self):
        engine = ComputeEngine()
        def fail(_payload):
            raise RuntimeError("expected test failure")
        engine.register("failure", fail)
        task = engine.submit("failure", {})
        for _ in range(100):
            result = engine.get_task(task["task_id"])
            if result["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.01)
        self.assertEqual(result["status"], "failed")
        self.assertIn("expected test failure", result["error"])
        engine.close()


if __name__ == "__main__":
    unittest.main()
