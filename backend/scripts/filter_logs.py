#!/usr/bin/env python3
"""
Filter Docker Compose logs by Lead ID
Usage: python filter_logs.py <lead_id> [lines]

Examples:
  python filter_logs.py 6KPmcTnNXKnw9QlYO1BNCg       # Show all logs for this lead
  python filter_logs.py 6KPmcTnNXKnw9QlYO1BNCg 50    # Show last 50 matching lines
"""
import sys
import subprocess
import re
import os
from datetime import datetime


class Colors:
    RED = '\033[31m'
    YELLOW = '\033[33m' 
    GREEN = '\033[32m'
    BOLD_RED = '\033[1;31m'
    BOLD_YELLOW = '\033[1;33m'
    RESET = '\033[0m'
    

def colorize_line(line):
    """Add color coding to log lines based on content"""
    if 'ERROR' in line:
        return f"{Colors.RED}{line}{Colors.RESET}"
    elif any(word in line for word in ['WARNING', 'WARN']):
        return f"{Colors.YELLOW}{line}{Colors.RESET}"
    elif any(word in line for word in ['🛑', 'CANCEL']):
        return f"{Colors.BOLD_RED}{line}{Colors.RESET}"
    elif any(word in line for word in ['🤖', 'AUTOMATED']):
        return f"{Colors.GREEN}{line}{Colors.RESET}"
    elif any(word in line for word in ['👨‍💼', 'MANUAL']):
        return f"{Colors.BOLD_YELLOW}{line}{Colors.RESET}"
    else:
        return line


def filter_docker_logs(lead_id, max_lines=100):
    """Filter Docker Compose logs for a specific lead ID"""
    print(f"🔍 Filtering Docker logs for Lead ID: {lead_id}")
    print(f"📊 Showing last {max_lines} matching entries")
    print("=" * 50)
    
    # Try to find the correct directory
    possible_dirs = [
        '/var/www/yelp/backend',
        os.path.join(os.path.dirname(__file__), '..'),
        os.getcwd()
    ]
    
    docker_dir = None
    for directory in possible_dirs:
        if os.path.exists(os.path.join(directory, 'docker-compose.yml')):
            docker_dir = directory
            break
    
    if not docker_dir:
        print("❌ Error: Could not find Docker Compose directory")
        print("Please run this script from the backend directory or ensure docker-compose.yml exists")
        return
    
    try:
        # Change to the Docker directory
        original_dir = os.getcwd()
        os.chdir(docker_dir)
        
        # Run docker-compose logs
        result = subprocess.run(
            ['docker-compose', 'logs', '--no-color'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ Error running docker-compose logs: {result.stderr}")
            return
            
        # Filter logs by lead ID
        matching_lines = []
        for line in result.stdout.split('\n'):
            if lead_id in line:
                matching_lines.append(line)
        
        # Show the last N matching lines
        displayed_lines = matching_lines[-max_lines:] if matching_lines else []
        
        if not displayed_lines:
            print(f"❌ No logs found for Lead ID: {lead_id}")
            return
            
        # Display with color coding
        for line in displayed_lines:
            if line.strip():  # Skip empty lines
                print(colorize_line(line))
        
        # Show summary
        print()
        print("📈 Summary:")
        print(f"  Total log entries for {lead_id}: {len(matching_lines)}")
        print(f"  Displayed: {len(displayed_lines)} (last entries)")
        
        if len(matching_lines) > max_lines:
            print(f"  ℹ️  Use 'python filter_logs.py {lead_id} {len(matching_lines)}' to see all entries")
        
        # Show key insights
        analyze_logs(displayed_lines, lead_id)
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout: Docker logs command took too long")
    except FileNotFoundError:
        print("❌ Error: docker-compose command not found")
        print("Make sure Docker Compose is installed and in your PATH")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # Restore original directory
        os.chdir(original_dir)


def analyze_logs(lines, lead_id):
    """Provide insights about the logs"""
    if not lines:
        return
        
    print("\n🧠 Log Analysis:")
    
    # Count different event types
    biz_events = len([l for l in lines if 'BIZ EVENT' in l])
    consumer_events = len([l for l in lines if 'CONSUMER EVENT' in l])
    automated_msgs = len([l for l in lines if '🤖' in l or 'AUTOMATED' in l])
    manual_msgs = len([l for l in lines if '👨‍💼' in l or 'MANUAL' in l])
    task_cancellations = len([l for l in lines if 'CANCEL' in l and 'TASK' in l])
    
    print(f"  📊 Event types:")
    print(f"    - BIZ events: {biz_events}")
    print(f"    - CONSUMER events: {consumer_events}")
    print(f"    - Automated messages: {automated_msgs}")
    print(f"    - Manual messages: {manual_msgs}")
    print(f"    - Task cancellations: {task_cancellations}")
    
    # Detect potential issues
    issues = []
    if manual_msgs > 0 and automated_msgs > 0:
        issues.append("⚠️  Both manual and automated messages detected - check for misidentification")
    
    if task_cancellations > 0:
        issues.append(f"⚠️  {task_cancellations} task cancellation(s) detected")
    
    # Look for follow-up completion
    follow_up_completed = any('FOLLOW-UP COMPLETED' in l for l in lines)
    if follow_up_completed:
        print(f"  ✅ Follow-up task completed successfully")
    
    if issues:
        print(f"  🚨 Potential issues:")
        for issue in issues:
            print(f"    {issue}")
    else:
        print(f"  ✅ No obvious issues detected")


def main():
    if len(sys.argv) < 2:
        print("❌ Error: Lead ID is required")
        print("Usage: python filter_logs.py <lead_id> [lines]")
        print("Example: python filter_logs.py 6KPmcTnNXKnw9QlYO1BNCg 50")
        sys.exit(1)
    
    lead_id = sys.argv[1]
    max_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    filter_docker_logs(lead_id, max_lines)


if __name__ == '__main__':
    main()
