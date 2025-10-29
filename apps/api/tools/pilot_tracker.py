#!/usr/bin/env python3
"""
LCopilot Pilot Program Tracker
CLI tool for logging and tracking pilot outreach activities.
"""

import os
import csv
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class PilotTracker:
    def __init__(self, csv_path: str = None):
        """Initialize pilot tracker with CSV file path"""
        if csv_path is None:
            csv_path = Path(__file__).parent.parent / "crm" / "pilot_tracker.csv"

        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize CSV file if it doesn't exist
        if not self.csv_path.exists():
            self._initialize_csv()

    def _initialize_csv(self):
        """Initialize CSV file with headers"""
        headers = [
            "timestamp", "prospect_name", "prospect_type", "industry",
            "location", "contact_person", "contact_method", "outreach_type",
            "status", "notes", "follow_up_date", "pilot_value_estimate",
            "decision_timeline", "next_action", "created_by"
        ]

        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

        print(f"✅ Initialized pilot tracker CSV: {self.csv_path}")

    def log_outreach(self,
                    prospect_name: str,
                    prospect_type: str,
                    industry: str = "",
                    location: str = "",
                    contact_person: str = "",
                    contact_method: str = "",
                    outreach_type: str = "",
                    status: str = "initial_contact",
                    notes: str = "",
                    follow_up_date: str = "",
                    pilot_value_estimate: str = "",
                    decision_timeline: str = "",
                    next_action: str = "",
                    created_by: str = "") -> Dict[str, Any]:
        """Log a new pilot outreach activity"""

        # Prepare row data
        timestamp = datetime.now().isoformat()
        if not created_by:
            created_by = os.getenv('USER', 'unknown')

        row_data = [
            timestamp, prospect_name, prospect_type, industry, location,
            contact_person, contact_method, outreach_type, status, notes,
            follow_up_date, pilot_value_estimate, decision_timeline,
            next_action, created_by
        ]

        # Append to CSV
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row_data)

        # Return logged entry
        logged_entry = {
            'timestamp': timestamp,
            'prospect_name': prospect_name,
            'prospect_type': prospect_type,
            'industry': industry,
            'status': status,
            'next_action': next_action
        }

        print(f"✅ Logged outreach: {prospect_name} ({prospect_type}) - {status}")
        return logged_entry

    def update_status(self, prospect_name: str, new_status: str, notes: str = "", next_action: str = ""):
        """Update status of an existing prospect"""

        # Read existing data
        rows = []
        updated = False

        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['prospect_name'].lower() == prospect_name.lower():
                    # Update the row
                    row['status'] = new_status
                    row['timestamp'] = datetime.now().isoformat()
                    if notes:
                        row['notes'] = notes
                    if next_action:
                        row['next_action'] = next_action
                    updated = True
                    print(f"✅ Updated {prospect_name}: {new_status}")
                rows.append(row)

        if not updated:
            print(f"❌ Prospect not found: {prospect_name}")
            return False

        # Write back to CSV
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        return True

    def list_prospects(self, status: str = None, prospect_type: str = None) -> List[Dict]:
        """List prospects with optional filtering"""

        prospects = []

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Apply filters
                    if status and row['status'].lower() != status.lower():
                        continue
                    if prospect_type and row['prospect_type'].lower() != prospect_type.lower():
                        continue

                    prospects.append(dict(row))
        except FileNotFoundError:
            print("❌ No pilot tracker data found. Initialize with 'log' command first.")
            return []

        return prospects

    def generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics"""

        prospects = self.list_prospects()

        if not prospects:
            return {"message": "No data available"}

        # Count by status
        status_counts = {}
        type_counts = {}
        recent_activity = []

        for prospect in prospects:
            # Status counts
            status = prospect['status']
            status_counts[status] = status_counts.get(status, 0) + 1

            # Type counts
            p_type = prospect['prospect_type']
            type_counts[p_type] = type_counts.get(p_type, 0) + 1

            # Recent activity (last 7 days)
            try:
                timestamp = datetime.fromisoformat(prospect['timestamp'].replace('Z', '+00:00'))
                if (datetime.now() - timestamp.replace(tzinfo=None)).days <= 7:
                    recent_activity.append({
                        'name': prospect['prospect_name'],
                        'status': prospect['status'],
                        'date': timestamp.strftime('%Y-%m-%d')
                    })
            except:
                pass  # Skip invalid timestamps

        summary = {
            'total_prospects': len(prospects),
            'status_breakdown': status_counts,
            'type_breakdown': type_counts,
            'recent_activity': recent_activity[:10],  # Last 10 activities
            'generated_at': datetime.now().isoformat()
        }

        return summary

    def export_json(self, output_path: str = None) -> str:
        """Export pilot data as JSON"""

        if output_path is None:
            output_path = self.csv_path.parent / "pilot_export.json"

        prospects = self.list_prospects()
        summary = self.generate_summary()

        export_data = {
            'export_info': {
                'generated_at': datetime.now().isoformat(),
                'total_records': len(prospects),
                'source_file': str(self.csv_path)
            },
            'summary': summary,
            'prospects': prospects
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"✅ Exported pilot data to: {output_path}")
        return str(output_path)

def main():
    parser = argparse.ArgumentParser(description='LCopilot Pilot Program Tracker')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Log outreach command
    log_parser = subparsers.add_parser('log', help='Log new pilot outreach')
    log_parser.add_argument('--name', required=True, help='Prospect name')
    log_parser.add_argument('--type', required=True, choices=['sme', 'bank'], help='Prospect type')
    log_parser.add_argument('--industry', default='', help='Industry sector')
    log_parser.add_argument('--location', default='', help='Location')
    log_parser.add_argument('--contact', default='', help='Contact person')
    log_parser.add_argument('--method', default='', help='Contact method (email, phone, etc.)')
    log_parser.add_argument('--outreach-type', default='initial', help='Type of outreach')
    log_parser.add_argument('--status', default='initial_contact', help='Current status')
    log_parser.add_argument('--notes', default='', help='Additional notes')
    log_parser.add_argument('--follow-up', default='', help='Follow-up date (YYYY-MM-DD)')
    log_parser.add_argument('--value', default='', help='Estimated pilot value')
    log_parser.add_argument('--timeline', default='', help='Decision timeline')
    log_parser.add_argument('--next-action', default='', help='Next action to take')

    # Update status command
    update_parser = subparsers.add_parser('update', help='Update prospect status')
    update_parser.add_argument('--name', required=True, help='Prospect name')
    update_parser.add_argument('--status', required=True, help='New status')
    update_parser.add_argument('--notes', default='', help='Update notes')
    update_parser.add_argument('--next-action', default='', help='Next action')

    # List prospects command
    list_parser = subparsers.add_parser('list', help='List prospects')
    list_parser.add_argument('--status', help='Filter by status')
    list_parser.add_argument('--type', choices=['sme', 'bank'], help='Filter by type')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')

    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Generate summary report')
    summary_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export data as JSON')
    export_parser.add_argument('--output', help='Output file path')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize tracker
    tracker = PilotTracker()

    if args.command == 'log':
        result = tracker.log_outreach(
            prospect_name=args.name,
            prospect_type=args.type,
            industry=args.industry,
            location=args.location,
            contact_person=args.contact,
            contact_method=args.method,
            outreach_type=args.outreach_type,
            status=args.status,
            notes=args.notes,
            follow_up_date=args.follow_up,
            pilot_value_estimate=args.value,
            decision_timeline=args.timeline,
            next_action=args.next_action
        )

        if args.next_action:
            print(f"📅 Next Action: {args.next_action}")

    elif args.command == 'update':
        tracker.update_status(args.name, args.status, args.notes, args.next_action)

    elif args.command == 'list':
        prospects = tracker.list_prospects(args.status, args.type)

        if args.format == 'json':
            print(json.dumps(prospects, indent=2, default=str))
        else:
            if not prospects:
                print("No prospects found.")
            else:
                print(f"\n📋 Found {len(prospects)} prospects:")
                print("-" * 80)
                for prospect in prospects:
                    print(f"• {prospect['prospect_name']} ({prospect['prospect_type']}) - {prospect['status']}")
                    if prospect['industry']:
                        print(f"  Industry: {prospect['industry']}")
                    if prospect['next_action']:
                        print(f"  Next Action: {prospect['next_action']}")
                    print()

    elif args.command == 'summary':
        summary = tracker.generate_summary()

        if args.format == 'json':
            print(json.dumps(summary, indent=2, default=str))
        else:
            print("\n📊 Pilot Program Summary")
            print("=" * 50)
            print(f"Total Prospects: {summary.get('total_prospects', 0)}")

            print("\n📈 Status Breakdown:")
            for status, count in summary.get('status_breakdown', {}).items():
                print(f"  {status}: {count}")

            print("\n🏢 Type Breakdown:")
            for p_type, count in summary.get('type_breakdown', {}).items():
                print(f"  {p_type}: {count}")

            recent = summary.get('recent_activity', [])
            if recent:
                print("\n🕒 Recent Activity:")
                for activity in recent[:5]:
                    print(f"  {activity['date']}: {activity['name']} - {activity['status']}")

    elif args.command == 'export':
        output_path = tracker.export_json(args.output)
        print(f"📤 Data exported to: {output_path}")

if __name__ == "__main__":
    main()