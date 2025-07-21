#!/usr/bin/env python3
"""
Load Test Runner for Nova-Torch
Author: Torch
Department: QA/DevOps
Project: Nova-Torch  
Date: 2025-01-21

Automated load test execution and reporting
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from load_test_config import LoadTestProfiles, LoadTestEnvironment, create_test_command


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoadTestRunner:
    """Manages load test execution and reporting"""
    
    def __init__(self, output_dir: str = "load_test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: Dict[str, Any] = {}
    
    def run_test(
        self, 
        profile_name: str, 
        environment: str = "local",
        distributed: bool = False,
        workers: int = 1
    ) -> Dict[str, Any]:
        """Run a load test with the specified profile"""
        
        logger.info(f"Starting load test: {profile_name} on {environment}")
        
        profile = LoadTestProfiles.get_profile(profile_name)
        if not profile:
            raise ValueError(f"Unknown profile: {profile_name}")
        
        # Create test command
        cmd, env_vars = create_test_command(profile_name, environment)
        
        # Setup output files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_id = f"{profile_name}_{environment}_{timestamp}"
        
        html_report = self.output_dir / f"{test_id}_report.html"
        csv_prefix = self.output_dir / f"{test_id}_results"
        log_file = self.output_dir / f"{test_id}.log"
        
        # Update command with output files
        cmd.extend([
            "--html", str(html_report),
            "--csv", str(csv_prefix),
            "--logfile", str(log_file)
        ])
        
        # Add distributed testing if requested
        if distributed and workers > 1:
            cmd.extend([
                "--master",
                "--expect-workers", str(workers)
            ])
        
        # Prepare environment
        test_env = os.environ.copy()
        test_env.update(env_vars)
        
        # Log test configuration
        logger.info(f"Test ID: {test_id}")
        logger.info(f"Profile: {profile.description}")
        logger.info(f"Users: {profile.users}, Spawn Rate: {profile.spawn_rate}")
        logger.info(f"Duration: {profile.run_time}")
        logger.info(f"Target: {profile.host}")
        
        # Execute test
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                env=test_env,
                capture_output=True,
                text=True,
                timeout=self._parse_duration_to_seconds(profile.run_time) + 300  # 5min buffer
            )
            
            execution_time = time.time() - start_time
            
            # Parse results
            test_results = self._parse_test_results(
                test_id, profile, result, execution_time, html_report, csv_prefix
            )
            
            # Validate against thresholds
            validation_results = self._validate_results(profile_name, test_results)
            test_results["validation"] = validation_results
            
            self.results[test_id] = test_results
            
            # Save results
            results_file = self.output_dir / f"{test_id}_summary.json"
            with open(results_file, 'w') as f:
                json.dump(test_results, f, indent=2, default=str)
            
            logger.info(f"Test completed: {test_id}")
            logger.info(f"Results saved to: {results_file}")
            
            return test_results
            
        except subprocess.TimeoutExpired:
            logger.error(f"Load test timed out: {test_id}")
            raise
        except Exception as e:
            logger.error(f"Load test failed: {e}")
            raise
    
    def run_test_suite(
        self, 
        profiles: List[str], 
        environment: str = "local",
        parallel: bool = False
    ) -> Dict[str, Any]:
        """Run multiple load tests"""
        
        logger.info(f"Starting load test suite: {profiles}")
        
        suite_results = {}
        
        if parallel:
            # TODO: Implement parallel execution
            logger.warning("Parallel execution not yet implemented, running sequentially")
        
        for profile_name in profiles:
            try:
                result = self.run_test(profile_name, environment)
                suite_results[profile_name] = result
                
                # Brief pause between tests
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Test {profile_name} failed: {e}")
                suite_results[profile_name] = {"error": str(e)}
        
        # Generate suite summary
        suite_summary = self._generate_suite_summary(suite_results)
        
        # Save suite results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suite_file = self.output_dir / f"test_suite_{timestamp}.json"
        
        with open(suite_file, 'w') as f:
            json.dump(suite_summary, f, indent=2, default=str)
        
        logger.info(f"Test suite completed. Results: {suite_file}")
        
        return suite_summary
    
    def _parse_test_results(
        self, 
        test_id: str, 
        profile, 
        result: subprocess.CompletedProcess,
        execution_time: float,
        html_report: Path,
        csv_prefix: Path
    ) -> Dict[str, Any]:
        """Parse load test results from output files"""
        
        test_results = {
            "test_id": test_id,
            "profile": profile.name,
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            "exit_code": result.returncode,
            "success": result.returncode == 0
        }
        
        # Parse CSV results if available
        stats_file = Path(f"{csv_prefix}_stats.csv")
        if stats_file.exists():
            test_results["stats"] = self._parse_csv_stats(stats_file)
        
        # Parse failures if available
        failures_file = Path(f"{csv_prefix}_failures.csv")
        if failures_file.exists():
            test_results["failures"] = self._parse_csv_failures(failures_file)
        
        # Parse stdout/stderr
        test_results["stdout"] = result.stdout
        test_results["stderr"] = result.stderr
        
        return test_results
    
    def _parse_csv_stats(self, stats_file: Path) -> Dict[str, Any]:
        """Parse Locust stats CSV file"""
        import csv
        
        stats = []
        with open(stats_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats.append(row)
        
        # Extract key metrics
        if stats:
            aggregated = stats[-1]  # Last row is typically aggregated
            return {
                "total_requests": int(aggregated.get("Request Count", 0)),
                "failure_count": int(aggregated.get("Failure Count", 0)),
                "failure_rate": float(aggregated.get("Failure Rate", 0)),
                "avg_response_time": float(aggregated.get("Average Response Time", 0)),
                "min_response_time": float(aggregated.get("Min Response Time", 0)),
                "max_response_time": float(aggregated.get("Max Response Time", 0)),
                "rps": float(aggregated.get("Requests/s", 0)),
                "raw_stats": stats
            }
        
        return {}
    
    def _parse_csv_failures(self, failures_file: Path) -> List[Dict[str, Any]]:
        """Parse Locust failures CSV file"""
        import csv
        
        failures = []
        with open(failures_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                failures.append(row)
        
        return failures
    
    def _validate_results(self, profile_name: str, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate test results against performance thresholds"""
        from load_test_config import LoadTestMetrics
        
        validation = {
            "passed": True,
            "failed_checks": [],
            "warnings": []
        }
        
        if profile_name not in LoadTestMetrics.PERFORMANCE_THRESHOLDS:
            validation["warnings"].append(f"No thresholds defined for profile: {profile_name}")
            return validation
        
        thresholds = LoadTestMetrics.PERFORMANCE_THRESHOLDS[profile_name]
        stats = test_results.get("stats", {})
        
        # Check response time
        avg_response_time = stats.get("avg_response_time", 0)
        if avg_response_time > thresholds["avg_response_time"]:
            validation["passed"] = False
            validation["failed_checks"].append(
                f"Average response time {avg_response_time}ms > {thresholds['avg_response_time']}ms"
            )
        
        # Check error rate
        failure_rate = stats.get("failure_rate", 0) / 100  # Convert percentage
        if failure_rate > thresholds["error_rate"]:
            validation["passed"] = False
            validation["failed_checks"].append(
                f"Error rate {failure_rate:.3f} > {thresholds['error_rate']:.3f}"
            )
        
        # Check throughput
        rps = stats.get("rps", 0)
        if rps < thresholds["throughput_rps"]:
            validation["warnings"].append(
                f"Throughput {rps:.1f} RPS < expected {thresholds['throughput_rps']} RPS"
            )
        
        return validation
    
    def _generate_suite_summary(self, suite_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary for test suite"""
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(suite_results),
            "passed_tests": 0,
            "failed_tests": 0,
            "test_results": suite_results,
            "overall_success": True
        }
        
        for test_name, result in suite_results.items():
            if isinstance(result, dict) and result.get("success"):
                validation = result.get("validation", {})
                if validation.get("passed", False):
                    summary["passed_tests"] += 1
                else:
                    summary["failed_tests"] += 1
                    summary["overall_success"] = False
            else:
                summary["failed_tests"] += 1
                summary["overall_success"] = False
        
        return summary
    
    def _parse_duration_to_seconds(self, duration: str) -> int:
        """Parse duration string to seconds"""
        if duration.endswith('s'):
            return int(duration[:-1])
        elif duration.endswith('m'):
            return int(duration[:-1]) * 60
        elif duration.endswith('h'):
            return int(duration[:-1]) * 3600
        else:
            return int(duration)


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Nova-Torch Load Test Runner")
    
    parser.add_argument(
        "profile", 
        nargs="?",
        help="Load test profile to run",
        choices=LoadTestProfiles.list_profiles() + ["all", "suite"]
    )
    
    parser.add_argument(
        "--environment", "-e",
        default="local",
        choices=list(LoadTestEnvironment.ENVIRONMENTS.keys()),
        help="Target environment"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default="load_test_results",
        help="Output directory for results"
    )
    
    parser.add_argument(
        "--distributed", "-d",
        action="store_true",
        help="Run distributed load test"
    )
    
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=1,
        help="Number of worker processes for distributed testing"
    )
    
    parser.add_argument(
        "--list-profiles", "-l",
        action="store_true",
        help="List available test profiles"
    )
    
    parser.add_argument(
        "--validate-only", "-v",
        action="store_true",
        help="Only validate configuration, don't run tests"
    )
    
    args = parser.parse_args()
    
    if args.list_profiles:
        print("Available Load Test Profiles:")
        for profile_name in LoadTestProfiles.list_profiles():
            profile = LoadTestProfiles.get_profile(profile_name)
            print(f"  {profile.name:12} - {profile.description}")
            print(f"               Users: {profile.users}, Duration: {profile.run_time}")
        return
    
    if not args.profile:
        parser.print_help()
        return
    
    runner = LoadTestRunner(args.output_dir)
    
    try:
        if args.profile in ["all", "suite"]:
            # Run full test suite
            profiles = ["smoke", "development", "staging"] if args.profile == "suite" else LoadTestProfiles.list_profiles()
            results = runner.run_test_suite(profiles, args.environment)
            
            print("\n" + "="*50)
            print("LOAD TEST SUITE SUMMARY")
            print("="*50)
            print(f"Total Tests: {results['total_tests']}")
            print(f"Passed: {results['passed_tests']}")
            print(f"Failed: {results['failed_tests']}")
            print(f"Overall Success: {results['overall_success']}")
            
        else:
            # Run single test
            if args.validate_only:
                profile = LoadTestProfiles.get_profile(args.profile)
                env_config = LoadTestEnvironment.get_environment(args.environment)
                print(f"✓ Profile '{args.profile}' is valid")
                print(f"✓ Environment '{args.environment}' is configured")
                print(f"✓ Target: {env_config['host']}")
                return
            
            result = runner.run_test(
                args.profile, 
                args.environment,
                args.distributed,
                args.workers
            )
            
            print("\n" + "="*50)
            print("LOAD TEST SUMMARY")
            print("="*50)
            print(f"Test ID: {result['test_id']}")
            print(f"Profile: {result['profile']}")
            print(f"Success: {result['success']}")
            print(f"Duration: {result['execution_time']:.1f}s")
            
            if "stats" in result:
                stats = result["stats"]
                print(f"Total Requests: {stats.get('total_requests', 0)}")
                print(f"Failure Rate: {stats.get('failure_rate', 0):.2f}%")
                print(f"Avg Response Time: {stats.get('avg_response_time', 0):.1f}ms")
                print(f"Throughput: {stats.get('rps', 0):.1f} RPS")
            
            validation = result.get("validation", {})
            if validation:
                print(f"Validation: {'✓ PASSED' if validation.get('passed') else '✗ FAILED'}")
                for check in validation.get("failed_checks", []):
                    print(f"  - {check}")
    
    except KeyboardInterrupt:
        logger.info("Load test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Load test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()