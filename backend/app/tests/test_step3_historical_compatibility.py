"""
Test Step 3 Historical Data Service Compatibility
Verifies that CLI and API produce identical results for historical data parsing
"""
import pytest
import json
import os
import shutil
import subprocess
import httpx
from pathlib import Path


class TestStep3HistoricalCompatibility:
    """Test CLI vs API compatibility for historical data processing"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup test environment and cleanup after tests"""
        # Save current universe.json if it exists
        self.universe_path = Path("data/universe.json")
        self.backup_path = Path("data/universe_test_backup.json")

        if self.universe_path.exists():
            shutil.copy(self.universe_path, self.backup_path)

        yield

        # Restore original universe.json
        if self.backup_path.exists():
            shutil.copy(self.backup_path, self.universe_path)
            self.backup_path.unlink()

    def test_cli_step3_execution(self):
        """Test that CLI step 3 executes successfully"""
        # Ensure we have a universe.json to work with
        if not self.universe_path.exists():
            pytest.skip("No universe.json file found - run step 2 first")

        # Execute CLI step 3
        result = subprocess.run(
            ["python", "main.py", "3"],
            capture_output=True,
            text=True,
            cwd="."
        )

        assert result.returncode == 0, f"CLI step 3 failed: {result.stderr}"
        assert "Step 3 complete" in result.stdout
        assert "updated with historical performance data" in result.stdout

    def test_api_endpoints_functionality(self):
        """Test that all API endpoints work correctly"""
        base_url = "http://localhost:8000/api/v1/historical"

        with httpx.Client() as client:
            # Test get all backtest data
            response = client.get(f"{base_url}/screeners/backtest")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert len(data["data"]) > 0  # Should have screener data

            # Test get specific screener data
            screener_keys = list(data["data"].keys())
            if screener_keys:
                first_screener = screener_keys[0]
                response = client.get(f"{base_url}/screeners/backtest/{first_screener}")
                assert response.status_code == 200
                screener_data = response.json()
                assert screener_data["success"] is True
                assert screener_data["screener_id"] == first_screener

            # Test performance summary
            response = client.get(f"{base_url}/performance/summary")
            assert response.status_code == 200
            summary = response.json()
            assert summary["success"] is True
            assert "summary" in summary
            assert "screeners" in summary["summary"]

    def test_cli_vs_api_universe_update_compatibility(self):
        """Test that CLI and API produce identical universe.json updates"""
        if not self.universe_path.exists():
            pytest.skip("No universe.json file found - run step 2 first")

        # Create two copies of universe.json for testing
        universe_cli_path = Path("data/universe_cli_test.json")
        universe_api_path = Path("data/universe_api_test.json")

        try:
            # Copy original universe for both tests
            shutil.copy(self.universe_path, universe_cli_path)
            shutil.copy(self.universe_path, universe_api_path)

            # Test CLI update
            shutil.copy(universe_cli_path, self.universe_path)
            result = subprocess.run(
                ["python", "main.py", "3"],
                capture_output=True,
                text=True,
                cwd="."
            )
            assert result.returncode == 0, f"CLI step 3 failed: {result.stderr}"

            # Save CLI result
            shutil.copy(self.universe_path, universe_cli_path)

            # Test API update
            shutil.copy(universe_api_path, self.universe_path)
            with httpx.Client() as client:
                response = client.post("http://localhost:8000/api/v1/historical/universe/update")
                assert response.status_code == 200
                api_result = response.json()
                assert api_result["success"] is True

            # Save API result
            shutil.copy(self.universe_path, universe_api_path)

            # Compare the results
            with open(universe_cli_path, 'r', encoding='utf-8') as f:
                cli_data = json.load(f)

            with open(universe_api_path, 'r', encoding='utf-8') as f:
                api_data = json.load(f)

            # Verify both have historical_performance section
            assert "metadata" in cli_data
            assert "metadata" in api_data
            assert "historical_performance" in cli_data["metadata"]
            assert "historical_performance" in api_data["metadata"]

            # Verify same screeners processed
            cli_screeners = set(cli_data["metadata"]["historical_performance"].keys())
            api_screeners = set(api_data["metadata"]["historical_performance"].keys())
            assert cli_screeners == api_screeners

            # Verify quarterly data matches for each screener
            for screener_id in cli_screeners:
                cli_screener = cli_data["metadata"]["historical_performance"][screener_id]
                api_screener = api_data["metadata"]["historical_performance"][screener_id]

                # Check that both have same structure
                assert "quarterly_data" in cli_screener
                assert "quarterly_data" in api_screener
                assert "quarterly_summary" in cli_screener
                assert "quarterly_summary" in api_screener

                # Check quarterly data count matches
                cli_quarters = len(cli_screener["quarterly_data"])
                api_quarters = len(api_screener["quarterly_data"])
                assert cli_quarters == api_quarters, f"Quarter count mismatch for {screener_id}: CLI={cli_quarters}, API={api_quarters}"

                # Check quarterly summary statistics match
                cli_summary = cli_screener["quarterly_summary"]
                api_summary = api_screener["quarterly_summary"]
                assert cli_summary["total_quarters"] == api_summary["total_quarters"]

                # Check if avg returns are calculated and match
                if "avg_quarterly_return" in cli_summary and "avg_quarterly_return" in api_summary:
                    assert cli_summary["avg_quarterly_return"] == api_summary["avg_quarterly_return"]

        finally:
            # Cleanup test files
            for test_file in [universe_cli_path, universe_api_path]:
                if test_file.exists():
                    test_file.unlink()

    def test_quarterly_data_parsing_accuracy(self):
        """Test that quarterly data parsing produces expected structure and calculations"""
        base_url = "http://localhost:8000/api/v1/historical"

        with httpx.Client() as client:
            response = client.get(f"{base_url}/screeners/backtest")
            assert response.status_code == 200
            data = response.json()

            for screener_id, screener_data in data["data"].items():
                if "error" not in screener_data:
                    # Verify required sections exist
                    assert "metadata" in screener_data
                    assert "quarterly_performance" in screener_data
                    assert "statistics" in screener_data

                    # Verify quarterly performance structure
                    quarterly_data = screener_data["quarterly_performance"]
                    assert len(quarterly_data) > 0, f"No quarterly data for {screener_id}"

                    # Check each quarter has required fields
                    for quarter in quarterly_data:
                        assert "quarter" in quarter
                        assert "return" in quarter
                        assert "period_sd" in quarter
                        assert "beta" in quarter
                        # benchmark_return is optional

                        # Verify quarter format (should be like "2023 Q1")
                        quarter_str = quarter["quarter"]
                        assert " Q" in quarter_str, f"Invalid quarter format: {quarter_str}"

                        # Verify return format (should be percentage like "5.23%")
                        return_str = quarter["return"]
                        assert "%" in return_str, f"Invalid return format: {return_str}"

    def test_performance_summary_calculations(self):
        """Test that performance summary calculations are accurate"""
        base_url = "http://localhost:8000/api/v1/historical"

        with httpx.Client() as client:
            # Get raw backtest data
            backtest_response = client.get(f"{base_url}/screeners/backtest")
            assert backtest_response.status_code == 200
            backtest_data = backtest_response.json()["data"]

            # Get performance summary
            summary_response = client.get(f"{base_url}/performance/summary")
            assert summary_response.status_code == 200
            summary_data = summary_response.json()["summary"]

            # Verify summary matches raw data
            for screener_id, raw_data in backtest_data.items():
                if "error" not in raw_data:
                    assert screener_id in summary_data["screeners"]
                    summary_screener = summary_data["screeners"][screener_id]

                    # Verify status is success
                    assert summary_screener["status"] == "success"

                    # Verify quarterly count matches
                    raw_quarters = len(raw_data["quarterly_performance"])
                    summary_quarters = summary_screener["quarterly_summary"]["total_quarters"]
                    assert raw_quarters == summary_quarters

                    # Verify avg quarterly return calculation (if present)
                    if "avg_quarterly_return" in summary_screener["quarterly_summary"]:
                        # Calculate expected average
                        returns = []
                        for quarter in raw_data["quarterly_performance"]:
                            try:
                                ret = quarter.get("return", "").replace("%", "")
                                if ret:
                                    returns.append(float(ret))
                            except (ValueError, AttributeError):
                                pass

                        if returns:
                            expected_avg = sum(returns) / len(returns)
                            expected_str = f"{expected_avg:.2f}%"
                            actual_str = summary_screener["quarterly_summary"]["avg_quarterly_return"]
                            assert actual_str == expected_str, f"Average calculation mismatch for {screener_id}: expected {expected_str}, got {actual_str}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])