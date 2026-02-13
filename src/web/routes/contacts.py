"""Contact routes: list, new, edit, log, delete, export."""
import csv
from datetime import date
from io import StringIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required

from ..helpers import get_service
from ...models import ContactType, NoteMention

bp = Blueprint('contacts', __name__)


@bp.route('/contacts')
@login_required
def contacts():
    """List all contacts."""
    service, session = get_service()
    try:
        search = request.args.get('search')
        followup = request.args.get('followup')
        if search:
            contacts = service.contacts.search_by_name(search)
        elif followup:
            contacts = service.contacts.get_needing_followup()
        else:
            contacts = service.contacts.get_all()

        # Build mention counts for each contact
        mention_counts = {}
        for contact in contacts:
            mention_counts[contact.id] = session.query(NoteMention).filter(
                NoteMention.contact_id == contact.id
            ).count()

        return render_template('contacts.html',
                             contacts=contacts,
                             mention_counts=mention_counts,
                             search=search,
                             followup=followup,
                             today=date.today())
    finally:
        session.close()


@bp.route('/contacts/export')
@login_required
def export_contacts_csv():
    """Export contacts to CSV."""
    service, session = get_service()
    try:
        contacts = service.contacts.get_all()

        # Check if user wants Google Sheets format (opens in browser)
        format_type = request.args.get('format')

        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow(['Name', 'Email', 'Phone', 'Company', 'Title', 'Type', 'LinkedIn', 'Last Contact', 'Next Follow-up', 'Notes'])

        # Data rows
        for contact in contacts:
            writer.writerow([
                contact.name,
                contact.email or '',
                contact.phone or '',
                contact.company.name if contact.company else '',
                contact.title or '',
                contact.contact_type.value.replace('_', ' ').title(),
                contact.linkedin_url or '',
                contact.last_contact_date.strftime('%Y-%m-%d') if contact.last_contact_date else '',
                contact.next_followup_date.strftime('%Y-%m-%d') if contact.next_followup_date else '',
                contact.notes or ''
            ])

        csv_content = output.getvalue()
        output.close()

        if format_type == 'sheets':
            # Redirect to Google Sheets with the CSV data
            # This creates a new sheet from CSV
            import urllib.parse
            encoded_csv = urllib.parse.quote(csv_content)
            sheets_url = f"https://docs.google.com/spreadsheets/d/create?title=Stride%20Contacts%20Export"
            # For now, just download - proper Sheets integration requires OAuth
            # Fall back to CSV download
            pass

        # Return as downloadable CSV
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=stride_contacts_{date.today().strftime("%Y%m%d")}.csv'}
        )
    finally:
        session.close()


@bp.route('/contacts/new', methods=['GET', 'POST'])
@login_required
def new_contact():
    """Add a new contact."""
    service, session = get_service()
    try:
        if request.method == 'POST':
            contact_type = ContactType(request.form.get('contact_type', 'networking'))
            contact = service.add_contact(
                name=request.form['name'],
                company_name=request.form.get('company'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                title=request.form.get('title'),
                contact_type=contact_type,
                linkedin_url=request.form.get('linkedin_url'),
                notes=request.form.get('notes')
            )
            flash(f'Contact {contact.name} added!', 'success')
            return redirect(url_for('contacts.contacts'))
        companies = service.companies.get_all()
        return render_template('contact_form.html',
                             companies=companies,
                             ContactType=ContactType)
    finally:
        session.close()


@bp.route('/contacts/<int:contact_id>/log', methods=['POST'])
@login_required
def log_contact(contact_id):
    """Log an interaction with a contact."""
    service, session = get_service()
    try:
        followup_days = request.form.get('followup_days')
        followup_days = int(followup_days) if followup_days else None
        service.log_contact_interaction(
            contact_id=contact_id,
            followup_days=followup_days,
            note=request.form.get('note')
        )
        flash('Interaction logged!', 'success')
    finally:
        session.close()
    return redirect(request.referrer or url_for('contacts.contacts'))


@bp.route('/contacts/<int:contact_id>/delete', methods=['POST'])
@login_required
def delete_contact(contact_id):
    """Delete a contact."""
    service, session = get_service()
    try:
        contact = service.contacts.get_by_id(contact_id)
        if contact:
            name = contact.name
            service.contacts.delete(contact_id)
            session.commit()
            flash(f'Contact {name} deleted.', 'success')
        else:
            flash('Contact not found.', 'error')
    finally:
        session.close()
    return redirect(url_for('contacts.contacts'))


@bp.route('/contacts/<int:contact_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_contact(contact_id):
    """Edit contact details."""
    service, session = get_service()
    try:
        contact = service.contacts.get_by_id(contact_id)
        if not contact:
            flash('Contact not found', 'error')
            return redirect(url_for('contacts.contacts'))

        if request.method == 'POST':
            contact_type = ContactType(request.form.get('contact_type', 'networking'))
            updates = {
                'name': request.form.get('name', contact.name),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'title': request.form.get('title'),
                'contact_type': contact_type,
                'linkedin_url': request.form.get('linkedin_url'),
                'how_we_met': request.form.get('how_we_met'),
                'notes': request.form.get('notes'),
            }

            relationship_strength = request.form.get('relationship_strength')
            if relationship_strength:
                updates['relationship_strength'] = int(relationship_strength)

            service.contacts.update(contact_id, **updates)
            session.commit()
            flash('Contact updated!', 'success')
            return redirect(url_for('contacts.contacts'))

        companies = service.companies.get_all()
        return render_template('edit_contact.html',
                             contact=contact,
                             companies=companies,
                             ContactType=ContactType)
    finally:
        session.close()
