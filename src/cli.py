#!/usr/bin/env python3
"""Command-line interface for Job Hunt Tracker."""
import argparse
import sys
from datetime import datetime, timedelta
from typing import Optional

from .database.connection import DatabaseConnection, get_db
from .services import JobHuntService
from .models import ApplicationStatus, EventType, ContactType


class CLI:
    """Command-line interface handler."""

    def __init__(self, db_path: str = None):
        self.db = DatabaseConnection(db_path)
        self.db.create_tables()
        self.session = self.db.get_session()
        self.service = JobHuntService(self.session)

    def close(self):
        self.session.close()

    # === Display Helpers ===

    def print_header(self, text: str):
        print(f"\n{'='*50}")
        print(f"  {text}")
        print('='*50)

    def print_subheader(self, text: str):
        print(f"\n--- {text} ---")

    def print_company(self, company, indent: int = 0):
        prefix = "  " * indent
        print(f"{prefix}[{company.id}] {company.name}")
        if company.industry:
            print(f"{prefix}    Industry: {company.industry}")
        if company.location:
            print(f"{prefix}    Location: {company.location}")

    def print_job(self, job, show_company: bool = True, indent: int = 0):
        prefix = "  " * indent
        company_info = f" @ {job.company.name}" if show_company else ""
        status = "ACTIVE" if job.is_active else "CLOSED"
        print(f"{prefix}[{job.id}] {job.title}{company_info} [{status}]")
        if job.salary_min and job.salary_max:
            print(f"{prefix}    Salary: ${job.salary_min:,} - ${job.salary_max:,}")
        if job.remote_type:
            print(f"{prefix}    Remote: {job.remote_type}")
        if job.location:
            print(f"{prefix}    Location: {job.location}")

    def print_application(self, app, indent: int = 0):
        prefix = "  " * indent
        print(f"{prefix}[{app.id}] {app.job.title} @ {app.job.company.name}")
        print(f"{prefix}    Status: {app.status.value.upper()}")
        if app.date_applied:
            print(f"{prefix}    Applied: {app.date_applied}")
        if app.excitement_level:
            stars = '*' * app.excitement_level
            print(f"{prefix}    Excitement: {stars}")

    def print_contact(self, contact, indent: int = 0):
        prefix = "  " * indent
        company = f" @ {contact.company.name}" if contact.company else ""
        print(f"{prefix}[{contact.id}] {contact.name}{company}")
        if contact.title:
            print(f"{prefix}    Title: {contact.title}")
        if contact.contact_type:
            print(f"{prefix}    Type: {contact.contact_type.value}")
        if contact.email:
            print(f"{prefix}    Email: {contact.email}")
        if contact.next_followup_date:
            print(f"{prefix}    Next followup: {contact.next_followup_date}")

    def print_event(self, event, indent: int = 0):
        prefix = "  " * indent
        time_str = event.start_time.strftime("%Y-%m-%d %H:%M")
        status = "[DONE]" if event.completed else ""
        print(f"{prefix}[{event.id}] {time_str} - {event.title} {status}")
        if event.event_type:
            print(f"{prefix}    Type: {event.event_type.value}")
        if event.location:
            print(f"{prefix}    Location: {event.location}")
        if event.meeting_link:
            print(f"{prefix}    Link: {event.meeting_link}")

    # === Commands ===

    def cmd_dashboard(self, args):
        """Show dashboard overview."""
        dashboard = self.service.get_dashboard()
        summary = dashboard['summary']

        self.print_header("JOB HUNT DASHBOARD")

        print(f"\n  Active Applications: {summary['active_applications']}")
        print(f"  Total Applications:  {summary['total_applications']}")
        print(f"  Events Today:        {summary['events_today']}")
        print(f"  Events This Week:    {summary['events_this_week']}")
        print(f"  Contacts to Follow:  {summary['contacts_need_followup']}")
        print(f"  Awaiting Response:   {summary['apps_awaiting_response']}")

        if dashboard['today']:
            self.print_subheader("TODAY'S EVENTS")
            for event in dashboard['today']:
                self.print_event(event, indent=1)

        if dashboard['upcoming']:
            self.print_subheader("UPCOMING EVENTS")
            for event in dashboard['upcoming']:
                self.print_event(event, indent=1)

        if dashboard['needs_attention']['stale_applications']:
            self.print_subheader("APPLICATIONS AWAITING RESPONSE (14+ days)")
            for app in dashboard['needs_attention']['stale_applications'][:5]:
                self.print_application(app, indent=1)

        if dashboard['stats']['by_status']:
            self.print_subheader("APPLICATION STATS")
            for status, count in dashboard['stats']['by_status'].items():
                print(f"    {status}: {count}")

    def cmd_apply(self, args):
        """Quick apply to a job."""
        app = self.service.quick_apply(
            company_name=args.company,
            job_title=args.title,
            job_url=args.url,
            source=args.source
        )
        print(f"\nApplication created! ID: {app.id}")
        self.print_application(app)

    def cmd_status(self, args):
        """Update application status."""
        try:
            status = ApplicationStatus(args.status.lower())
        except ValueError:
            print(f"Invalid status. Valid options: {', '.join([s.value for s in ApplicationStatus])}")
            return

        app = self.service.update_application_status(args.id, status)
        if app:
            print(f"\nApplication updated!")
            self.print_application(app)
        else:
            print(f"Application {args.id} not found.")

    def cmd_pipeline(self, args):
        """Show application pipeline."""
        pipeline = self.service.get_pipeline()

        self.print_header("APPLICATION PIPELINE")

        # Order statuses logically
        status_order = [
            'interested', 'preparing', 'applied', 'screening',
            'interviewing', 'final_round', 'offer', 'negotiating',
            'accepted', 'rejected', 'withdrawn', 'ghosted'
        ]

        for status in status_order:
            if status in pipeline:
                apps = pipeline[status]
                self.print_subheader(f"{status.upper()} ({len(apps)})")
                for app in apps:
                    self.print_application(app, indent=1)

    def cmd_companies(self, args):
        """List or search companies."""
        companies = self.service.find_companies(search=args.search, industry=args.industry)

        self.print_header("COMPANIES")
        if not companies:
            print("\n  No companies found.")
        for company in companies:
            self.print_company(company, indent=1)

    def cmd_add_company(self, args):
        """Add a new company."""
        company = self.service.add_company(
            name=args.name,
            industry=args.industry,
            location=args.location,
            website=args.website
        )
        print(f"\nCompany created! ID: {company.id}")
        self.print_company(company)

    def cmd_jobs(self, args):
        """List or search jobs."""
        jobs = self.service.find_jobs(
            search=args.search,
            remote_only=args.remote,
            min_salary=args.min_salary
        )

        self.print_header("JOBS")
        if not jobs:
            print("\n  No jobs found.")
        for job in jobs:
            self.print_job(job, indent=1)

    def cmd_add_job(self, args):
        """Add a new job."""
        job = self.service.add_job(
            company_name=args.company,
            title=args.title,
            salary_min=args.salary_min,
            salary_max=args.salary_max,
            remote_type=args.remote,
            location=args.location,
            source=args.source,
            job_url=args.url
        )
        print(f"\nJob created! ID: {job.id}")
        self.print_job(job)

    def cmd_contacts(self, args):
        """List or search contacts."""
        if args.search:
            contacts = self.service.contacts.search_by_name(args.search)
        elif args.followup:
            contacts = self.service.contacts.get_needing_followup()
        else:
            contacts = self.service.contacts.get_all()

        self.print_header("CONTACTS")
        if not contacts:
            print("\n  No contacts found.")
        for contact in contacts:
            self.print_contact(contact, indent=1)

    def cmd_add_contact(self, args):
        """Add a new contact."""
        try:
            contact_type = ContactType(args.type) if args.type else ContactType.NETWORKING
        except ValueError:
            print(f"Invalid type. Valid options: {', '.join([t.value for t in ContactType])}")
            return

        contact = self.service.add_contact(
            name=args.name,
            company_name=args.company,
            email=args.email,
            title=args.title,
            contact_type=contact_type
        )
        print(f"\nContact created! ID: {contact.id}")
        self.print_contact(contact)

    def cmd_log_contact(self, args):
        """Log an interaction with a contact."""
        contact = self.service.log_contact_interaction(
            contact_id=args.id,
            followup_days=args.followup_days,
            note=args.note
        )
        if contact:
            print(f"\nContact interaction logged!")
            self.print_contact(contact)
        else:
            print(f"Contact {args.id} not found.")

    def cmd_schedule(self, args):
        """Show upcoming schedule."""
        schedule = self.service.get_schedule(days=args.days)

        self.print_header(f"SCHEDULE (Next {args.days} days)")

        if not schedule:
            print("\n  No upcoming events.")
        for day, events in schedule.items():
            self.print_subheader(day)
            for event in events:
                self.print_event(event, indent=1)

    def cmd_add_event(self, args):
        """Schedule a new event."""
        # Parse datetime
        try:
            start_time = datetime.strptime(args.datetime, "%Y-%m-%d %H:%M")
        except ValueError:
            print("Invalid datetime format. Use: YYYY-MM-DD HH:MM")
            return

        try:
            event_type = EventType(args.type) if args.type else EventType.OTHER
        except ValueError:
            print(f"Invalid type. Valid options: {', '.join([t.value for t in EventType])}")
            return

        event = self.service.schedule_event(
            title=args.title,
            start_time=start_time,
            event_type=event_type,
            application_id=args.app_id,
            contact_id=args.contact_id,
            location=args.location,
            meeting_link=args.link
        )
        print(f"\nEvent scheduled! ID: {event.id}")
        self.print_event(event)

    def cmd_interview(self, args):
        """Schedule an interview."""
        try:
            start_time = datetime.strptime(args.datetime, "%Y-%m-%d %H:%M")
        except ValueError:
            print("Invalid datetime format. Use: YYYY-MM-DD HH:MM")
            return

        try:
            interview_type = EventType(args.type) if args.type else EventType.VIDEO_INTERVIEW
        except ValueError:
            print(f"Invalid type. Use: phone_screen, video_interview, onsite_interview, technical_interview, behavioral_interview, panel_interview")
            return

        event = self.service.schedule_interview(
            application_id=args.app_id,
            start_time=start_time,
            interview_type=interview_type,
            meeting_link=args.link,
            prep_notes=args.prep
        )
        print(f"\nInterview scheduled! ID: {event.id}")
        self.print_event(event)

    def cmd_complete(self, args):
        """Mark an event as completed."""
        event = self.service.complete_event(
            event_id=args.id,
            went_well=args.good,
            notes=args.notes
        )
        if event:
            print(f"\nEvent marked complete!")
            self.print_event(event)
        else:
            print(f"Event {args.id} not found.")

    def cmd_note(self, args):
        """Add a note."""
        note = self.service.add_note(
            content=args.content,
            title=args.title,
            company_id=args.company_id,
            application_id=args.app_id,
            contact_id=args.contact_id,
            note_type=args.type or "general"
        )
        print(f"\nNote added! ID: {note.id}")

    def cmd_notes(self, args):
        """Search notes."""
        if args.search:
            notes = self.service.search_notes(args.search)
        else:
            notes = self.service.notes.get_recent(limit=20)

        self.print_header("NOTES")
        for note in notes:
            print(f"\n  [{note.id}] {note.title or 'Untitled'} ({note.note_type or 'general'})")
            print(f"       {note.content[:100]}{'...' if len(note.content) > 100 else ''}")
            print(f"       Created: {note.created_at.strftime('%Y-%m-%d %H:%M')}")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="jobhunt",
        description="Track your job hunt - applications, contacts, and schedule"
    )
    parser.add_argument("--db", help="Path to database file")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Dashboard
    subparsers.add_parser("dashboard", aliases=["d"], help="Show dashboard overview")

    # Apply
    apply_parser = subparsers.add_parser("apply", aliases=["a"], help="Quick apply to a job")
    apply_parser.add_argument("company", help="Company name")
    apply_parser.add_argument("title", help="Job title")
    apply_parser.add_argument("--url", help="Job posting URL")
    apply_parser.add_argument("--source", help="Where you found it (LinkedIn, Indeed, etc)")

    # Status update
    status_parser = subparsers.add_parser("status", aliases=["s"], help="Update application status")
    status_parser.add_argument("id", type=int, help="Application ID")
    status_parser.add_argument("status", help="New status")

    # Pipeline
    subparsers.add_parser("pipeline", aliases=["p"], help="Show application pipeline")

    # Companies
    companies_parser = subparsers.add_parser("companies", help="List companies")
    companies_parser.add_argument("--search", "-s", help="Search by name")
    companies_parser.add_argument("--industry", "-i", help="Filter by industry")

    # Add company
    add_company_parser = subparsers.add_parser("add-company", help="Add a company")
    add_company_parser.add_argument("name", help="Company name")
    add_company_parser.add_argument("--industry", "-i", help="Industry")
    add_company_parser.add_argument("--location", "-l", help="Location")
    add_company_parser.add_argument("--website", "-w", help="Website URL")

    # Jobs
    jobs_parser = subparsers.add_parser("jobs", help="List jobs")
    jobs_parser.add_argument("--search", "-s", help="Search by title")
    jobs_parser.add_argument("--remote", "-r", action="store_true", help="Remote only")
    jobs_parser.add_argument("--min-salary", type=int, help="Minimum salary")

    # Add job
    add_job_parser = subparsers.add_parser("add-job", help="Add a job")
    add_job_parser.add_argument("company", help="Company name")
    add_job_parser.add_argument("title", help="Job title")
    add_job_parser.add_argument("--salary-min", type=int, help="Minimum salary")
    add_job_parser.add_argument("--salary-max", type=int, help="Maximum salary")
    add_job_parser.add_argument("--remote", choices=["remote", "hybrid", "onsite"], help="Remote type")
    add_job_parser.add_argument("--location", "-l", help="Location")
    add_job_parser.add_argument("--source", help="Source")
    add_job_parser.add_argument("--url", help="Job URL")

    # Contacts
    contacts_parser = subparsers.add_parser("contacts", aliases=["c"], help="List contacts")
    contacts_parser.add_argument("--search", "-s", help="Search by name")
    contacts_parser.add_argument("--followup", "-f", action="store_true", help="Need followup")

    # Add contact
    add_contact_parser = subparsers.add_parser("add-contact", help="Add a contact")
    add_contact_parser.add_argument("name", help="Contact name")
    add_contact_parser.add_argument("--company", "-c", help="Company name")
    add_contact_parser.add_argument("--email", "-e", help="Email")
    add_contact_parser.add_argument("--title", "-t", help="Job title")
    add_contact_parser.add_argument("--type", help="Contact type")

    # Log contact
    log_contact_parser = subparsers.add_parser("log-contact", help="Log contact interaction")
    log_contact_parser.add_argument("id", type=int, help="Contact ID")
    log_contact_parser.add_argument("--followup-days", "-f", type=int, help="Days until next followup")
    log_contact_parser.add_argument("--note", "-n", help="Note about interaction")

    # Schedule
    schedule_parser = subparsers.add_parser("schedule", help="Show schedule")
    schedule_parser.add_argument("--days", "-d", type=int, default=7, help="Days to show")

    # Add event
    add_event_parser = subparsers.add_parser("add-event", help="Schedule an event")
    add_event_parser.add_argument("title", help="Event title")
    add_event_parser.add_argument("datetime", help="Date and time (YYYY-MM-DD HH:MM)")
    add_event_parser.add_argument("--type", "-t", help="Event type")
    add_event_parser.add_argument("--app-id", type=int, help="Application ID")
    add_event_parser.add_argument("--contact-id", type=int, help="Contact ID")
    add_event_parser.add_argument("--location", "-l", help="Location")
    add_event_parser.add_argument("--link", help="Meeting link")

    # Interview
    interview_parser = subparsers.add_parser("interview", aliases=["i"], help="Schedule an interview")
    interview_parser.add_argument("app_id", type=int, help="Application ID")
    interview_parser.add_argument("datetime", help="Date and time (YYYY-MM-DD HH:MM)")
    interview_parser.add_argument("--type", "-t", default="video_interview", help="Interview type")
    interview_parser.add_argument("--link", help="Meeting link")
    interview_parser.add_argument("--prep", help="Prep notes")

    # Complete event
    complete_parser = subparsers.add_parser("complete", help="Mark event complete")
    complete_parser.add_argument("id", type=int, help="Event ID")
    complete_parser.add_argument("--good", action="store_true", help="Went well")
    complete_parser.add_argument("--bad", dest="good", action="store_false", help="Didn't go well")
    complete_parser.add_argument("--notes", "-n", help="Outcome notes")
    complete_parser.set_defaults(good=None)

    # Notes
    notes_parser = subparsers.add_parser("notes", help="View notes")
    notes_parser.add_argument("--search", "-s", help="Search notes")

    # Add note
    add_note_parser = subparsers.add_parser("note", help="Add a note")
    add_note_parser.add_argument("content", help="Note content")
    add_note_parser.add_argument("--title", "-t", help="Note title")
    add_note_parser.add_argument("--company-id", type=int, help="Company ID")
    add_note_parser.add_argument("--app-id", type=int, help="Application ID")
    add_note_parser.add_argument("--contact-id", type=int, help="Contact ID")
    add_note_parser.add_argument("--type", help="Note type")

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = CLI(db_path=args.db)

    try:
        command_map = {
            "dashboard": cli.cmd_dashboard, "d": cli.cmd_dashboard,
            "apply": cli.cmd_apply, "a": cli.cmd_apply,
            "status": cli.cmd_status, "s": cli.cmd_status,
            "pipeline": cli.cmd_pipeline, "p": cli.cmd_pipeline,
            "companies": cli.cmd_companies,
            "add-company": cli.cmd_add_company,
            "jobs": cli.cmd_jobs,
            "add-job": cli.cmd_add_job,
            "contacts": cli.cmd_contacts, "c": cli.cmd_contacts,
            "add-contact": cli.cmd_add_contact,
            "log-contact": cli.cmd_log_contact,
            "schedule": cli.cmd_schedule,
            "add-event": cli.cmd_add_event,
            "interview": cli.cmd_interview, "i": cli.cmd_interview,
            "complete": cli.cmd_complete,
            "notes": cli.cmd_notes,
            "note": cli.cmd_note,
        }

        if args.command in command_map:
            command_map[args.command](args)
        else:
            parser.print_help()
    finally:
        cli.close()


if __name__ == "__main__":
    main()
