#!/usr/bin/env python3
# autoblogger/scripts/ci/check_profile_ready.py

import sys
from pathlib import Path
from autoblogger.core.profile import check_selenium_profile_ready
from autoblogger.core.logging import get_logger

logger = get_logger(__name__)


def main():
    """Check if the automation profile is ready for CI/CD."""
    # Get profile path
    profile_path = str(
        Path.home()
        / "AppData"
        / "Local"
        / "Google"
        / "Chrome"
        / "User Data"
        / "SeleniumProfile"
    )

    # Check profile readiness
    if not check_selenium_profile_ready(profile_path):
        logger.error("❌ Profile not ready for automation")
        logger.error(
            "Please run: python -m autoblogger.scripts.setup_automation_profile"
        )
        sys.exit(1)

    logger.info("✅ Profile ready for automation")
    sys.exit(0)


if __name__ == "__main__":
    main()
