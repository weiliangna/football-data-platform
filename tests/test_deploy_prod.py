from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = PROJECT_ROOT / "scripts" / "deploy_prod.sh"


class DeploymentCompileScopeTests(unittest.TestCase):
    def setUp(self):
        self.script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    def test_compile_checks_only_git_tracked_python_files(self):
        self.assertIn("admin_git ls-files -z -- '*.py'", self.script)
        self.assertIn(
            '"$PROJECT_DIR/venv/bin/python" -m py_compile',
            self.script,
        )
        self.assertNotIn(
            '"$PROJECT_DIR/venv/bin/python" -m compileall',
            self.script,
        )

    def test_compile_does_not_remove_local_production_files(self):
        self.assertNotIn("git clean", self.script)
        self.assertNotIn("rm -rf", self.script)
        self.assertNotIn("git reset --hard", self.script)

    def test_api_health_checks_are_visible_and_bounded(self):
        self.assertIn("wait_for_http()", self.script)
        self.assertIn("Health check $attempt/$attempts", self.script)
        self.assertIn("--connect-timeout 3 --max-time 20", self.script)
        self.assertIn(
            'wait_for_http "http://127.0.0.1:8000/" 3',
            self.script,
        )
        self.assertIn(
            '"http://127.0.0.1:8000/api/portal/dashboard" 3',
            self.script,
        )
        self.assertIn("sleep 2", self.script)

    def test_interrupted_frontend_build_is_repaired(self):
        self.assertIn("FRONTEND_BUILD_MARKER=", self.script)
        self.assertIn("frontend_build_is_current", self.script)
        self.assertIn("mark_frontend_build", self.script)
        self.assertIn("rebuild scheduled", self.script)
        self.assertIn('"${1:-}" == "--repair"', self.script)

    def test_frontend_build_uses_locked_dependencies(self):
        self.assertIn("npm ci --no-audit --no-fund", self.script)
        self.assertIn("npm run build", self.script)


if __name__ == "__main__":
    unittest.main()
