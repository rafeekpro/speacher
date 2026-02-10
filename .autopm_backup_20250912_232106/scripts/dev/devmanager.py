#!/usr/bin/env python3
"""
Speecher DevManager - Complete development environment management tool
"""

import os
import sys
import subprocess
import time
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import signal
import requests

class Colors:
    """Terminal colors for better UI"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class DevManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.docker_compose_file = self.project_root / "docker-compose.yml"
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:8501"
        self.mongodb_uri = "mongodb://localhost:27017"
        self.docker_compose_cmd = None  # Will be set after checking
        
        # Container names - can be overridden via environment or docker-compose.yml
        self.mongodb_container = os.getenv("MONGODB_CONTAINER_NAME", "mongodb")
        self.backend_container = os.getenv("BACKEND_CONTAINER_NAME", "backend")
        self.frontend_container = os.getenv("FRONTEND_CONTAINER_NAME", "frontend")
        
    def get_docker_compose_cmd(self) -> List[str]:
        """Get the docker compose command to use"""
        if self.docker_compose_cmd is None:
            # Check and set the command if not already done
            if not self.check_docker_compose():
                raise RuntimeError("Docker Compose is not available")
        return self.docker_compose_cmd
    
    def get_container_name(self, service: str) -> str:
        """Get the actual container name for a service from docker-compose"""
        # Try to get container name from docker compose ps
        result = subprocess.run(
            [*self.get_docker_compose_cmd(), "ps", "-q", service],
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Get container ID and then its name
            container_id = result.stdout.strip()
            name_result = subprocess.run(
                ["docker", "inspect", "-f", "{{.Name}}", container_id],
                capture_output=True,
                text=True
            )
            if name_result.returncode == 0:
                # Remove leading slash from container name
                return name_result.stdout.strip().lstrip('/')
        
        # Fallback to default project-service naming convention
        project_name = self.get_project_name()
        return f"{project_name}-{service}-1"
    
    def get_project_name(self) -> str:
        """Get the docker compose project name"""
        # Try to get from COMPOSE_PROJECT_NAME env var
        project_name = os.getenv("COMPOSE_PROJECT_NAME")
        if project_name:
            return project_name
        
        # Default to directory name
        return self.project_root.name.lower()
    
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")
    
    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
    
    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")
    
    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")
    
    def run_command(self, command: List[str], capture_output: bool = False, 
                   check: bool = True) -> Optional[subprocess.CompletedProcess]:
        """Run shell command"""
        try:
            result = subprocess.run(
                command, 
                capture_output=capture_output, 
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            if check:
                self.print_error(f"Command failed: {' '.join(command)}")
                if e.output:
                    print(e.output)
            return None
        except FileNotFoundError:
            self.print_error(f"Command not found: {command[0]}")
            return None
    
    def check_docker(self) -> bool:
        """Check if Docker is installed and running"""
        # Check if docker is installed
        result = self.run_command(["docker", "--version"], capture_output=True, check=False)
        if not result or result.returncode != 0:
            self.print_error("Docker is not installed")
            return False
        
        # Check if docker daemon is running - try multiple methods
        # Method 1: docker info
        result = self.run_command(["docker", "info"], capture_output=True, check=False)
        if result and result.returncode == 0:
            return True
            
        # Method 2: docker ps (sometimes works when info doesn't)
        result = self.run_command(["docker", "ps"], capture_output=True, check=False)
        if result and result.returncode == 0:
            return True
            
        # Method 3: Check Docker Desktop specific (macOS)
        if sys.platform == "darwin":
            # Check various Docker socket locations on macOS
            socket_paths = [
                "/var/run/docker.sock",
                os.path.expanduser("~/.docker/run/docker.sock"),
                "/usr/local/var/run/docker.sock"
            ]
            
            for socket_path in socket_paths:
                if os.path.exists(socket_path):
                    self.print_info(f"Found Docker socket at {socket_path}")
                    # Try with explicit socket
                    result = self.run_command(
                        ["docker", "-H", f"unix://{socket_path}", "ps"], 
                        capture_output=True, 
                        check=False
                    )
                    if result and result.returncode == 0:
                        return True
            
            # Check if Docker Desktop app is running
            result = self.run_command(
                ["pgrep", "-f", "Docker Desktop"], 
                capture_output=True, 
                check=False
            )
            if result and result.stdout.strip():
                self.print_warning("Docker Desktop process found but daemon not responding")
                self.print_info("Try: 1) Quit Docker Desktop, 2) Start it again, 3) Wait 30 seconds")
                return False
        
        self.print_error("Docker daemon is not running or not accessible")
        self.print_info("Please start Docker Desktop and wait for it to fully initialize")
        self.print_info("On macOS: Open Docker Desktop from Applications")
        return False
    
    def check_docker_compose(self) -> bool:
        """Check if docker compose is installed"""
        # Try new docker compose command first
        result = self.run_command(["docker", "compose", "--version"], capture_output=True, check=False)
        if result and result.returncode == 0:
            self.docker_compose_cmd = ["docker", "compose"]
            return True
        
        # Try old docker compose command
        result = self.run_command(["docker-compose", "--version"], capture_output=True, check=False)
        if result and result.returncode == 0:
            self.docker_compose_cmd = ["docker-compose"]
            self.print_info("Using docker compose (legacy)")
            return True
        
        self.print_error("Neither 'docker compose' nor 'docker-compose' is installed")
        return False
    
    def setup_environment(self):
        """Setup environment configuration"""
        self.print_header("Environment Setup")
        
        if not self.env_file.exists():
            if self.env_example.exists():
                self.print_info("Creating .env file from .env.example")
                shutil.copy(self.env_example, self.env_file)
                self.print_success(".env file created")
                self.print_warning("Please update .env with your API keys if needed")
            else:
                self.print_warning("No .env file found, using default configuration")
        else:
            self.print_success(".env file already exists")
    
    def start_services(self, services: Optional[List[str]] = None):
        """Start Docker services"""
        self.print_header("Starting Services")
        
        if not self.check_docker():
            return False
        
        cmd = self.get_docker_compose_cmd() + ["up", "-d"]
        if services:
            cmd.extend(services)
        
        self.print_info("Starting Docker containers...")
        result = self.run_command(cmd)
        
        if result:
            self.print_success("Services started")
            self.wait_for_health()
            self.show_service_status()
            return True
        return False
    
    def stop_services(self, remove_volumes: bool = False):
        """Stop Docker services"""
        self.print_header("Stopping Services")
        
        cmd = self.get_docker_compose_cmd() + ["down"]
        if remove_volumes:
            cmd.append("-v")
            self.print_warning("Removing volumes (all data will be deleted)")
        
        result = self.run_command(cmd)
        if result:
            self.print_success("Services stopped")
            return True
        return False
    
    def restart_service(self, service: str):
        """Restart specific service"""
        self.print_info(f"Restarting {service}...")
        result = self.run_command(self.get_docker_compose_cmd() + ["restart", service])
        if result:
            self.print_success(f"{service} restarted")
            return True
        return False
    
    def show_service_status(self):
        """Show status of all services"""
        self.print_header("Service Status")
        
        result = self.run_command(self.get_docker_compose_cmd() + ["ps"], capture_output=True)
        if result:
            print(result.stdout)
            
            # Check individual service health
            services = self.get_service_health()
            print(f"\n{Colors.BOLD}Service Health:{Colors.ENDC}")
            for service, health in services.items():
                if health['healthy']:
                    self.print_success(f"{service}: {health['status']}")
                else:
                    self.print_error(f"{service}: {health['status']}")
    
    def get_service_health(self) -> Dict[str, Dict]:
        """Get health status of services"""
        services = {}
        
        # Check MongoDB
        result = self.run_command(
            self.get_docker_compose_cmd() + ["exec", "-T", "mongodb", "mongosh", 
             "--quiet", "--eval", "db.runCommand({ping: 1})"],
            capture_output=True, check=False
        )
        services['mongodb'] = {
            'healthy': result and result.returncode == 0,
            'status': 'healthy' if result and result.returncode == 0 else 'unhealthy'
        }
        
        # Check Backend
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=2)
            services['backend'] = {
                'healthy': response.status_code == 200,
                'status': 'healthy' if response.status_code == 200 else 'unhealthy'
            }
        except:
            services['backend'] = {'healthy': False, 'status': 'not responding'}
        
        # Check Frontend
        try:
            response = requests.get(f"{self.frontend_url}/_stcore/health", timeout=2)
            services['frontend'] = {
                'healthy': response.status_code == 200,
                'status': 'healthy' if response.status_code == 200 else 'unhealthy'
            }
        except:
            services['frontend'] = {'healthy': False, 'status': 'not responding'}
        
        return services
    
    def wait_for_health(self, timeout: int = 60):
        """Wait for services to become healthy"""
        self.print_info("Waiting for services to become healthy...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            services = self.get_service_health()
            all_healthy = all(s['healthy'] for s in services.values())
            
            if all_healthy:
                self.print_success("All services are healthy!")
                return True
            
            print(".", end="", flush=True)
            time.sleep(2)
        
        print()
        self.print_warning("Some services did not become healthy in time")
        return False
    
    def view_logs(self, service: Optional[str] = None, follow: bool = False):
        """View service logs"""
        self.print_header("Service Logs")
        
        cmd = self.get_docker_compose_cmd() + ["logs"]
        if follow:
            cmd.append("-f")
        else:
            cmd.extend(["--tail", "100"])
        
        if service:
            cmd.append(service)
            self.print_info(f"Showing logs for {service}")
        else:
            self.print_info("Showing logs for all services")
        
        self.run_command(cmd, check=False)
    
    def run_tests(self, verbose: bool = True):
        """Run integration tests"""
        self.print_header("Running Tests")
        
        # Ensure services are running
        services = self.get_service_health()
        if not all(s['healthy'] for s in services.values()):
            self.print_warning("Some services are not healthy. Starting services...")
            self.start_services()
        
        self.print_info("Running integration tests...")
        cmd = self.get_docker_compose_cmd() + ["--profile", "test", "up", "--abort-on-container-exit", "test-runner"]
        
        result = self.run_command(cmd)
        
        # Check test results
        results_file = self.project_root / "test_results" / "results.xml"
        if results_file.exists():
            self.print_success(f"Test results saved to {results_file}")
            # Parse and display summary
            self.show_test_summary(results_file)
        
        return result is not None
    
    def show_test_summary(self, results_file: Path):
        """Parse and show test results summary"""
        try:
            with open(results_file, 'r') as f:
                content = f.read()
                if 'errors="0" failures="0"' in content:
                    self.print_success("All tests passed!")
                else:
                    self.print_warning("Some tests failed. Check results.xml for details")
        except Exception as e:
            self.print_error(f"Could not parse test results: {e}")
    
    def exec_shell(self, service: str):
        """Execute shell in service container"""
        self.print_info(f"Opening shell in {service} container...")
        
        shells = {
            'backend': '/bin/bash',
            'frontend': '/bin/bash',
            'mongodb': 'mongosh -u speecher_user -p speecher_pass speecher'
        }
        
        shell = shells.get(service, '/bin/bash')
        cmd = self.get_docker_compose_cmd() + ["exec", service, shell]
        
        os.system(' '.join(cmd))
    
    def backup_database(self):
        """Backup MongoDB database"""
        self.print_header("Database Backup")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / "backups" / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.print_info(f"Creating backup in {backup_dir}")
        
        # Create backup in container
        result = self.run_command([
            *self.get_docker_compose_cmd(), "exec", "-T", "mongodb",
            "mongodump", "-u", "admin", "-p", "speecher_admin_pass",
            "--out", f"/tmp/backup_{timestamp}"
        ])
        
        if not result:
            return False
        
        # Copy backup to host
        mongodb_container = self.get_container_name(self.mongodb_container)
        result = self.run_command([
            "docker", "cp",
            f"{mongodb_container}:/tmp/backup_{timestamp}",
            str(backup_dir)
        ])
        
        if result:
            self.print_success(f"Backup created successfully at {backup_dir}")
            
            # Cleanup temp backup in container
            self.run_command([
                *self.get_docker_compose_cmd(), "exec", "-T", "mongodb",
                "rm", "-rf", f"/tmp/backup_{timestamp}"
            ], check=False)
            
            return True
        return False
    
    def restore_database(self, backup_path: Optional[str] = None):
        """Restore MongoDB database from backup"""
        self.print_header("Database Restore")
        
        if not backup_path:
            # List available backups
            backups_dir = self.project_root / "backups"
            if not backups_dir.exists():
                self.print_error("No backups found")
                return False
            
            backups = sorted(backups_dir.glob("*"))
            if not backups:
                self.print_error("No backups found")
                return False
            
            print("Available backups:")
            for i, backup in enumerate(backups, 1):
                print(f"  {i}. {backup.name}")
            
            try:
                choice = int(input("\nSelect backup to restore (number): "))
                backup_path = backups[choice - 1]
            except (ValueError, IndexError):
                self.print_error("Invalid selection")
                return False
        else:
            backup_path = Path(backup_path)
        
        if not backup_path.exists():
            self.print_error(f"Backup not found: {backup_path}")
            return False
        
        self.print_warning("This will overwrite the current database!")
        confirm = input("Continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Restore cancelled")
            return False
        
        # Copy backup to container
        temp_path = f"/tmp/restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        mongodb_container = self.get_container_name(self.mongodb_container)
        result = self.run_command([
            "docker", "cp",
            str(backup_path),
            f"{mongodb_container}:{temp_path}"
        ])
        
        if not result:
            return False
        
        # Restore database
        result = self.run_command([
            *self.get_docker_compose_cmd(), "exec", "-T", "mongodb",
            "mongorestore", "-u", "admin", "-p", "speecher_admin_pass",
            "--drop", temp_path
        ])
        
        if result:
            self.print_success("Database restored successfully")
            
            # Cleanup
            self.run_command([
                *self.get_docker_compose_cmd(), "exec", "-T", "mongodb",
                "rm", "-rf", temp_path
            ], check=False)
            
            return True
        return False
    
    def configure_api_keys(self):
        """Configure API keys through CLI"""
        self.print_header("API Key Configuration")
        
        providers = ['aws', 'azure', 'gcp']
        
        print("Select provider to configure:")
        for i, provider in enumerate(providers, 1):
            print(f"  {i}. {provider.upper()}")
        
        try:
            choice = int(input("\nSelect provider (number): "))
            provider = providers[choice - 1]
        except (ValueError, IndexError):
            self.print_error("Invalid selection")
            return False
        
        self.print_info(f"Configuring {provider.upper()} API keys")
        
        keys = {}
        if provider == 'aws':
            keys['access_key_id'] = input("AWS Access Key ID: ")
            keys['secret_access_key'] = input("AWS Secret Access Key: ")
            keys['region'] = input("AWS Region (default: us-east-1): ") or "us-east-1"
            keys['s3_bucket_name'] = input("S3 Bucket Name: ")
        elif provider == 'azure':
            keys['subscription_key'] = input("Azure Subscription Key: ")
            keys['region'] = input("Azure Region (default: eastus): ") or "eastus"
            keys['storage_account'] = input("Storage Account Name: ")
            keys['storage_key'] = input("Storage Account Key: ")
        elif provider == 'gcp':
            keys['credentials_json'] = input("GCP Service Account JSON (paste entire JSON): ")
            keys['gcs_bucket_name'] = input("GCS Bucket Name: ")
        
        # Save via API
        try:
            response = requests.post(
                f"{self.backend_url}/api/keys/{provider}",
                json={"provider": provider, "keys": keys}
            )
            if response.status_code == 200:
                self.print_success(f"{provider.upper()} API keys configured successfully")
                return True
            else:
                self.print_error(f"Failed to configure API keys: {response.text}")
        except Exception as e:
            self.print_error(f"Failed to connect to backend: {e}")
        
        return False
    
    def rebuild_services(self, no_cache: bool = False):
        """Rebuild Docker images"""
        self.print_header("Rebuilding Services")
        
        cmd = self.get_docker_compose_cmd() + ["build"]
        if no_cache:
            cmd.append("--no-cache")
            self.print_info("Building without cache (this may take longer)")
        
        result = self.run_command(cmd)
        if result:
            self.print_success("Services rebuilt successfully")
            return True
        return False
    
    def clean_system(self):
        """Clean Docker system"""
        self.print_header("System Cleanup")
        
        print("This will remove:")
        print("  - Stopped containers")
        print("  - Unused networks")
        print("  - Dangling images")
        print("  - Build cache")
        
        confirm = input("\nContinue? (y/N): ")
        if confirm.lower() != 'y':
            print("Cleanup cancelled")
            return False
        
        self.print_info("Cleaning Docker system...")
        result = self.run_command(["docker", "system", "prune", "-f"])
        
        if result:
            self.print_success("System cleaned")
            return True
        return False
    
    def show_resource_usage(self):
        """Show Docker resource usage"""
        self.print_header("Resource Usage")
        
        # Docker stats
        self.print_info("Container resource usage:")
        result = self.run_command(
            ["docker", "stats", "--no-stream", "--format", 
             "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"],
            capture_output=True
        )
        if result:
            print(result.stdout)
        
        # Disk usage
        self.print_info("\nDisk usage:")
        result = self.run_command(["docker", "system", "df"], capture_output=True)
        if result:
            print(result.stdout)
    
    def interactive_menu(self):
        """Show interactive menu"""
        while True:
            self.print_header("Speecher DevManager")
            
            print(f"{Colors.BOLD}Docker Management:{Colors.ENDC}")
            print("  1. Start all services")
            print("  2. Stop all services")
            print("  3. Restart a service")
            print("  4. Show service status")
            print("  5. View logs")
            print("  6. Rebuild services")
            
            print(f"\n{Colors.BOLD}Database:{Colors.ENDC}")
            print("  7. Backup database")
            print("  8. Restore database")
            print("  9. Open MongoDB shell")
            
            print(f"\n{Colors.BOLD}Development:{Colors.ENDC}")
            print("  10. Run tests")
            print("  11. Open backend shell")
            print("  12. Open frontend shell")
            print("  13. Configure API keys")
            
            print(f"\n{Colors.BOLD}System:{Colors.ENDC}")
            print("  14. Show resource usage")
            print("  15. Clean Docker system")
            print("  16. Setup environment (.env)")
            
            print(f"\n{Colors.BOLD}Quick Actions:{Colors.ENDC}")
            print("  20. Full restart (stop + start)")
            print("  21. View backend logs (follow)")
            print("  22. Quick health check")
            
            print(f"\n  0. Exit")
            
            try:
                choice = input(f"\n{Colors.CYAN}Select option: {Colors.ENDC}")
                
                if choice == '0':
                    print("Goodbye!")
                    break
                elif choice == '1':
                    self.start_services()
                elif choice == '2':
                    self.stop_services()
                elif choice == '3':
                    service = input("Service name (mongodb/backend/frontend): ")
                    self.restart_service(service)
                elif choice == '4':
                    self.show_service_status()
                elif choice == '5':
                    service = input("Service name (or Enter for all): ").strip() or None
                    follow = input("Follow logs? (y/N): ").lower() == 'y'
                    self.view_logs(service, follow)
                elif choice == '6':
                    no_cache = input("Build without cache? (y/N): ").lower() == 'y'
                    self.rebuild_services(no_cache)
                elif choice == '7':
                    self.backup_database()
                elif choice == '8':
                    self.restore_database()
                elif choice == '9':
                    self.exec_shell('mongodb')
                elif choice == '10':
                    self.run_tests()
                elif choice == '11':
                    self.exec_shell('backend')
                elif choice == '12':
                    self.exec_shell('frontend')
                elif choice == '13':
                    self.configure_api_keys()
                elif choice == '14':
                    self.show_resource_usage()
                elif choice == '15':
                    self.clean_system()
                elif choice == '16':
                    self.setup_environment()
                elif choice == '20':
                    self.stop_services()
                    time.sleep(2)
                    self.start_services()
                elif choice == '21':
                    self.view_logs('backend', follow=True)
                elif choice == '22':
                    services = self.get_service_health()
                    for service, health in services.items():
                        if health['healthy']:
                            self.print_success(f"{service}: {health['status']}")
                        else:
                            self.print_error(f"{service}: {health['status']}")
                else:
                    self.print_warning("Invalid option")
                
                if choice != '0':
                    input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")
                    
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                self.print_error(f"An error occurred: {e}")
                input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.ENDC}")

def main():
    """Main entry point"""
    manager = DevManager()
    
    # Allow skipping Docker check with --skip-check flag
    skip_check = "--skip-check" in sys.argv
    if skip_check:
        sys.argv.remove("--skip-check")
        manager.print_warning("Skipping Docker checks (--skip-check flag used)")
        # Set default docker compose command
        manager.docker_compose_cmd = ["docker", "compose"]
    else:
        # Check prerequisites
        if not manager.check_docker():
            print("\nIf Docker is running but not detected, use: ./dm --skip-check [command]")
            sys.exit(1)
        
        if not manager.check_docker_compose():
            print("Please install docker compose first")
            sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'start':
            manager.start_services()
        elif command == 'stop':
            manager.stop_services()
        elif command == 'restart':
            if len(sys.argv) > 2:
                manager.restart_service(sys.argv[2])
            else:
                manager.stop_services()
                manager.start_services()
        elif command == 'status':
            manager.show_service_status()
        elif command == 'logs':
            service = sys.argv[2] if len(sys.argv) > 2 else None
            follow = '--follow' in sys.argv or '-f' in sys.argv
            manager.view_logs(service, follow)
        elif command == 'test':
            manager.run_tests()
        elif command == 'backup':
            manager.backup_database()
        elif command == 'restore':
            backup_path = sys.argv[2] if len(sys.argv) > 2 else None
            manager.restore_database(backup_path)
        elif command == 'shell':
            if len(sys.argv) > 2:
                manager.exec_shell(sys.argv[2])
            else:
                print("Usage: devmanager.py shell <service>")
        elif command == 'build':
            no_cache = '--no-cache' in sys.argv
            manager.rebuild_services(no_cache)
        elif command == 'clean':
            manager.clean_system()
        elif command == 'health':
            services = manager.get_service_health()
            for service, health in services.items():
                if health['healthy']:
                    manager.print_success(f"{service}: {health['status']}")
                else:
                    manager.print_error(f"{service}: {health['status']}")
        elif command in ['help', '--help', '-h']:
            print("""
Speecher DevManager - Development Environment Management

Usage: python devmanager.py [options] [command] [args]

Options:
  --skip-check       Skip Docker daemon check (use if Docker is running but not detected)

Commands:
  start              Start all services
  stop               Stop all services
  restart [service]  Restart all services or specific service
  status             Show service status
  logs [service]     View logs (use -f or --follow for live logs)
  test               Run integration tests
  backup             Backup database
  restore [path]     Restore database from backup
  shell <service>    Open shell in service container
  build              Rebuild Docker images (use --no-cache for clean build)
  clean              Clean Docker system
  health             Quick health check
  help               Show this help message

Without arguments, opens interactive menu.

Examples:
  python devmanager.py start
  python devmanager.py logs backend -f
  python devmanager.py shell mongodb
  python devmanager.py test
  python devmanager.py --skip-check start  # Skip Docker check if needed
            """)
        else:
            print(f"Unknown command: {command}")
            print("Use 'python devmanager.py help' for usage information")
    else:
        # No arguments - show interactive menu
        manager.interactive_menu()

if __name__ == "__main__":
    main()
