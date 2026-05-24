#!/usr/bin/env python3
"""
Deployment Verification Checks - Based on c.txt Production Architecture.
Validates environment, configuration, security, and runtime readiness.
"""

import sys
import os
import json
import socket
from pathlib import Path


class DeploymentChecker:
    """Performs comprehensive deployment verification."""

    def __init__(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        self.errors = []
        self.warnings = []
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warned = 0

    def check(self, name: str, condition: bool, fatal: bool = True):
        """Run a single check."""
        if condition:
            print(f"  [OK] {name}")
            self.checks_passed += 1
        elif fatal:
            print(f"  [FAIL] {name}")
            self.errors.append(name)
            self.checks_failed += 1
        else:
            print(f"  [WARN] {name}")
            self.warnings.append(name)
            self.checks_warned += 1

    def run_all(self):
        """Run all deployment checks."""
        print()
        print("=" * 60)
        print("  AI Workspace - Deployment Verification")
        print("=" * 60)
        print()

        # Environment Validation
        self._check_environment()

        # Project Structure
        self._check_project_structure()

        # Configuration Validation
        self._check_configurations()

        # Security Validation
        self._check_security()

        # Port Availability
        self._check_ports()

        # Dependency Checks
        self._check_dependencies()

        # Runtime Readiness
        self._check_runtime()

        # Summary
        self._print_summary()
        return len(self.errors) == 0

    def _check_environment(self):
        """Check 1-3 from c.txt: Environment validation."""
        print("[1/7] Environment Validation")

        self.check("Python version >= 3.11",
                    sys.version_info >= (3, 11))

        self.check("Platform detected",
                    sys.platform in ("win32", "linux", "darwin"))

        # Check Python packages
        required_packages = ["fastapi", "uvicorn", "sqlalchemy", "pydantic",
                            "jose", "httpx", "psutil", "cryptography"]
        for pkg in required_packages:
            try:
                __import__(pkg.replace("-", "_"))
                self.check(f"Package '{pkg}' installed", True)
            except ImportError:
                self.check(f"Package '{pkg}' installed", False, fatal=False)
        print()

    def _check_project_structure(self):
        """Check project folder structure."""
        print("[2/7] Project Structure")

        required_dirs = [
            "apps/backend", "apps/frontend",
            "configs", "scripts", "tests",
            "logs", "runtime", "mcps",
        ]
        for dir_name in required_dirs:
            path = self.root_dir / dir_name
            self.check(f"Directory '{dir_name}' exists",
                       path.exists() and path.is_dir())

        required_files = [
            "apps/backend/main.py",
            "apps/frontend/package.json",
            "run.bat", "run.sh",
            "scripts/check_env.bat", "scripts/check_env.sh",
        ]
        for file_name in required_files:
            path = self.root_dir / file_name
            exists = path.exists()
            self.check(f"File '{file_name}' exists", exists, fatal=False)
        print()

    def _check_configurations(self):
        """Check 3 from c.txt: Config validation."""
        print("[3/7] Configuration Validation")

        config_files = ["providers.json", "runtime.json", "ui.json", "mcp_registry.json"]
        for cfg in config_files:
            path = self.root_dir / "configs" / cfg
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    self.check(f"Config '{cfg}' is valid JSON", True)
                except json.JSONDecodeError:
                    self.check(f"Config '{cfg}' is valid JSON", False)
            else:
                self.check(f"Config '{cfg}' exists", False, fatal=False)
        print()

    def _check_security(self):
        """Check 6 from c.txt: Security implementation."""
        print("[4/7] Security Validation")

        # Check for .env file or environment variables
        env_file = self.root_dir / ".env"
        has_secret = bool(os.environ.get("SECRET_KEY"))
        self.check("Secret key configured (env or .env)",
                   has_secret or env_file.exists(), fatal=False)

        # Check security module imports
        sys.path.insert(0, str(self.root_dir / "apps" / "backend"))
        try:
            from core.security import (create_access_token, encrypt_api_key,
                                        sanitize_command)
            self.check("Security module loads correctly", True)
        except ImportError:
            self.check("Security module loads correctly", False)
        print()

    def _check_ports(self):
        """Check from c.txt: Port availability."""
        print("[5/7] Port Availability")

        for port, name in [(8000, "Backend API"), (5173, "Frontend Dev")]:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result != 0:
                self.check(f"Port {port} ({name}) available", True)
            else:
                self.check(f"Port {port} ({name}) available", False, fatal=False)
        print()

    def _check_dependencies(self):
        """Check from c.txt: Dependency validation."""
        print("[6/7] Dependency Checks")

        # Check npm/node availability
        self.check("Node.js is available",
                   self._command_exists("node"), fatal=False)
        self.check("npm is available",
                   self._command_exists("npm"), fatal=False)

        # Check Python package manager
        self.check("pip is available",
                   self._command_exists("pip") or self._command_exists("pip3"), fatal=False)

        # Check Ollama
        self.check("Ollama is available",
                   self._command_exists("ollama"), fatal=False)
        print()

    def _check_runtime(self):
        """Check 5 from c.txt: Runtime readiness."""
        print("[7/7] Runtime Readiness")

        # Check backend modules
        sys.path.insert(0, str(self.root_dir / "apps" / "backend"))
        try:
            from services.ollama_service import OllamaService
            from services.mcp_service import MCPService
            from services.provider_service import ProviderService
            from services.chat_service import ChatService
            from services.runtime_service import RuntimeService
            self.check("All backend services importable", True)
        except ImportError as e:
            self.check(f"All backend services importable: {e}", False)

        # Check frontend dependencies
        package_json = self.root_dir / "apps" / "frontend" / "package.json"
        if package_json.exists():
            with open(package_json) as f:
                data = json.load(f)
            has_deps = len(data.get("dependencies", {})) > 0
            self.check("Frontend dependencies defined", has_deps)
        print()

    def _command_exists(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        import shutil
        return shutil.which(cmd) is not None

    def _print_summary(self):
        """Print deployment check summary."""
        print()
        print("=" * 60)
        print("  Deployment Check Summary")
        print("=" * 60)
        print()
        print(f"  Passed:   {self.checks_passed}")
        print(f"  Failed:   {self.checks_failed}")
        print(f"  Warnings: {self.checks_warned}")

        if self.errors:
            print()
            print("  Failed Checks:")
            for err in self.errors:
                print(f"    - {err}")

        if self.warnings:
            print()
            print("  Warnings:")
            for warn in self.warnings:
                print(f"    - {warn}")

        print()
        if self.errors:
            print("  => Result: DEPLOYMENT FAILED - Fix errors above")
        else:
            print("  => Result: DEPLOYMENT READY")
        print()


if __name__ == "__main__":
    checker = DeploymentChecker()
    success = checker.run_all()
    sys.exit(0 if success else 1)
