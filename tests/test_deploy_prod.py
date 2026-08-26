from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = PROJECT_ROOT / "scripts" / "deploy_prod.sh"


class DeploymentCompileScopeTests(unittest.TestCase):
    def test_compile_checks_only_git_tracked_python_files(self):
        script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("admin_git ls-files -z -- '*.py'", script)
        self.assertIn('"$PROJECT_DIR/venv/bin/python" -m py_compile', script)
        self.assertNotIn('"$PROJECT_DIR/venv/bin/python" -m compileall', script)

    def test_compile_does_not_remove_local_production_files(self):
        script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("git clean", script)
        self.assertNotIn("rm -rf", script)

    def test_api_health_checks_wait_for_service_readiness(self):
        script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("wait_for_http()", script)
        self.assertIn(
            'wait_for_http "http://127.0.0.1:8000/" 30',
            script,
        )
        self.assertIn(
            '"http://127.0.0.1:8000/api/portal/dashboard" 30',
            script,
        )
        self.assertIn("sleep 1", script)


if __name__ == "__main__":
    unittest.main()
