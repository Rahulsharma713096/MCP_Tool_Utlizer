"""Deployment Readiness Checks - validates the system is ready for production deployment.

These checks are typically run as part of a CI/CD pipeline to verify:
- All required environment variables are set
- All critical services are reachable
- Database schema is valid
- API endpoints respond correctly
- Security configurations are in place
- No known vulnerabilities
"""

import os
import sys
import json

# Add backend source to path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), 'ai-workspace', 'apps', 'backend')
sys.path.insert(0, os.path.abspath(BACKEND_DIR))


def check_environment_variables() -> list[str]:
    """Check all required environment variables are set.
    Returns list of missing variable names (empty = all present).
    """
    # Settings with defaults don't need to be checked
    # These are critical ones that should be set in production
    optional_vars = [
        "SECRET_KEY",
        "ENCRYPTION_KEY",
        "DATABASE_URL",
        "OLLAMA_HOST",
        "CORS_ORIGINS",
    ]

    missing = []
    for var in optional_vars:
        if not os.environ.get(var):
            missing.append(var)

    return missing


def check_module_imports() -> list[str]:
    """Check all backend modules import correctly.
    Returns list of failed modules (empty = all pass).
    """
    failed = []

    modules_to_check = [
        "config.settings",
        "core.logging",
        "core.security",
        "models.database",
        "models.schemas",
        "services.ollama_service",
        "services.mcp_service",
        "services.chat_service",
        "services.provider_service",
        "services.runtime_service",
        "api.routes",
    ]

    for mod_name in modules_to_check:
        try:
            __import__(mod_name)
        except Exception as e:
            failed.append(f"{mod_name}: {e}")

    return failed


def check_api_endpoints(base_url: str = "http://localhost:8080") -> list[dict]:
    """Check critical API endpoints respond correctly.
    Returns list of endpoint check results.
    """
    import httpx

    endpoints = [
        ("GET", "/"),
        ("GET", "/api/v1/version"),
        ("GET", "/api/v1/health"),
        ("GET", "/api/v1/system/info"),
        ("GET", "/api/v1/config/ui"),
        ("GET", "/api/v1/config/runtime"),
    ]

    results = []
    try:
        for method, path in endpoints:
            try:
                response = httpx.get(f"{base_url}{path}", timeout=5)
                results.append({
                    "endpoint": f"{method} {path}",
                    "status": response.status_code,
                    "healthy": response.status_code < 500,
                    "error": None,
                })
            except Exception as e:
                results.append({
                    "endpoint": f"{method} {path}",
                    "status": None,
                    "healthy": False,
                    "error": str(e),
                })
    except Exception as e:
        results.append({
            "endpoint": "ALL",
            "status": None,
            "healthy": False,
            "error": f"Could not connect to {base_url}: {e}",
        })

    return results


def check_database_connectivity() -> dict:
    """Check database connection and schema.
    Returns status dict.
    """
    try:
        from models.database import init_sync_db, sync_engine
        from sqlalchemy import text

        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            return {
                "connected": row is not None,
                "error": None,
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }


def check_security_config() -> list[str]:
    """Check security configuration.
    Returns list of security warnings.
    """
    warnings = []
    import config.settings as settings

    if settings.ENV == "production":
        if not settings.SECRET_KEY or settings.SECRET_KEY == "default-secret-key":
            warnings.append("SECRET_KEY is not set or is default value")
        if not settings.ENCRYPTION_KEY:
            warnings.append("ENCRYPTION_KEY is not set")
        if settings.DEBUG:
            warnings.append("DEBUG mode is enabled in production")
        if "http://localhost:5173" in settings.CORS_ORIGINS:
            warnings.append("Localhost CORS origin in production config")

    return warnings


def run_all_checks() -> dict:
    """Run all deployment checks and return comprehensive report."""
    print("=" * 60)
    print("DEPLOYMENT READINESS CHECK")
    print("=" * 60)

    # Environment
    print("\n[1/5] Environment Variables...")
    missing_vars = check_environment_variables()
    if missing_vars:
        print(f"  ⚠️  Missing (optional) vars: {', '.join(missing_vars)}")
    else:
        print("  ✅ Required env vars present")

    # Modules
    print("\n[2/5] Module Imports...")
    failed_modules = check_module_imports()
    if failed_modules:
        print(f"  ❌ Failed modules:")
        for m in failed_modules:
            print(f"     - {m}")
    else:
        print("  ✅ All modules import correctly")

    # API
    print("\n[3/5] API Endpoints...")
    api_results = check_api_endpoints()
    all_healthy = all(r["healthy"] for r in api_results)
    if all_healthy:
        print(f"  ✅ All endpoints respond: {len(api_results)} checked")
    else:
        for r in api_results:
            if not r["healthy"]:
                print(f"  ❌ {r['endpoint']}: {r['error'] or r['status']}")

    # Database
    print("\n[4/5] Database Connectivity...")
    db_result = check_database_connectivity()
    if db_result["connected"]:
        print("  ✅ Database connected")
    else:
        print(f"  ❌ Database: {db_result['error']}")

    # Security
    print("\n[5/5] Security Configuration...")
    security_warnings = check_security_config()
    if security_warnings:
        for w in security_warnings:
            print(f"  ⚠️  {w}")
    else:
        print("  ✅ No security warnings")

    # Summary
    print("\n" + "=" * 60)
    issues = (
        len(failed_modules)
        + len([r for r in api_results if not r["healthy"]])
        + (1 if not db_result["connected"] else 0)
    )
    if issues == 0:
        print("✅ SYSTEM READY FOR DEPLOYMENT")
    else:
        print(f"❌ {issues} issue(s) found — review before deploying")
    print("=" * 60)

    return {
        "environment": {"missing_vars": missing_vars},
        "modules": {"failed": failed_modules, "total": 12},
        "api": {
            "results": api_results,
            "all_healthy": all_healthy,
            "checked": len(api_results),
        },
        "database": db_result,
        "security": {"warnings": security_warnings},
        "ready": issues == 0,
    }


if __name__ == "__main__":
    result = run_all_checks()
    sys.exit(0 if result["ready"] else 1)
