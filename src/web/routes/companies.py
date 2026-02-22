"""Company routes: list, new, edit, delete."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..helpers import get_service

bp = Blueprint('companies', __name__)


@bp.route('/companies')
@login_required
def companies():
    """List all companies."""
    service, session = get_service()
    try:
        search = request.args.get('search')
        companies = service.find_companies(search=search)
        return render_template('companies.html', companies=companies, search=search)
    finally:
        session.close()


@bp.route('/companies/new', methods=['GET', 'POST'])
@login_required
def new_company():
    """Add a new company."""
    if request.method == 'POST':
        service, session = get_service()
        try:
            company = service.add_company(
                name=request.form['name'],
                industry=request.form.get('industry'),
                location=request.form.get('location'),
                website=request.form.get('website'),
                description=request.form.get('description')
            )
            flash(f'Company {company.name} added!', 'success')
            return redirect(url_for('companies.companies'))
        finally:
            session.close()
    return render_template('company_form.html')


@bp.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_company(company_id):
    """Edit company details."""
    service, session = get_service()
    try:
        company = service.companies.get_by_id(company_id)
        if not company:
            flash('Company not found', 'error')
            return redirect(url_for('companies.companies'))

        if request.method == 'POST':
            updates = {
                'name': request.form.get('name', company.name),
                'website': request.form.get('website'),
                'industry': request.form.get('industry'),
                'size': request.form.get('size'),
                'location': request.form.get('location'),
                'description': request.form.get('description'),
                'culture_notes': request.form.get('culture_notes'),
                'glassdoor_rating': request.form.get('glassdoor_rating'),
                'linkedin_url': request.form.get('linkedin_url'),
            }

            service.companies.update(company_id, **updates)
            session.commit()
            flash('Company updated!', 'success')

            # Redirect back to application if we came from there
            app_id = request.args.get('app_id')
            if app_id:
                return redirect(url_for('applications.application_detail', app_id=app_id))
            return redirect(url_for('companies.companies'))

        return render_template('edit_company.html', company=company)
    finally:
        session.close()


@bp.route('/companies/<int:company_id>/delete', methods=['POST'])
@login_required
def delete_company(company_id):
    """Delete a company."""
    service, session = get_service()
    try:
        company = service.companies.get_by_id(company_id)
        if company:
            name = company.name
            service.companies.delete(company_id)
            session.commit()
            flash(f'Company {name} deleted.', 'success')
        else:
            flash('Company not found.', 'error')
    finally:
        session.close()
    return redirect(url_for('companies.companies'))
