"""Job routes: list, new, edit, flag."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..helpers import get_service

bp = Blueprint('jobs', __name__)


@bp.route('/jobs')
@login_required
def jobs():
    """List all job listings."""
    service, session = get_service()
    try:
        search = request.args.get('search')
        flagged_only = request.args.get('flagged')
        company_id = request.args.get('company_id', type=int)
        company_name = None
        if company_id:
            company = service.companies.get_by_id(company_id)
            if company:
                company_name = company.name
                jobs = [j for j in service.jobs.get_all() if j.company_id == company_id]
            else:
                jobs = []
        elif search:
            jobs = service.jobs.search(search)
        elif flagged_only:
            jobs = service.jobs.get_flagged()
        else:
            jobs = service.jobs.get_all()
        return render_template('jobs.html',
                             jobs=jobs,
                             search=search,
                             flagged_only=flagged_only,
                             company_id=company_id,
                             company_name=company_name)
    finally:
        session.close()


@bp.route('/jobs/new', methods=['GET', 'POST'])
@login_required
def new_job():
    """Add a new job listing."""
    service, session = get_service()
    try:
        if request.method == 'POST':
            company_id = request.form.get('company_id')
            company_name = request.form.get('company_name', '').strip()

            if not company_id and company_name:
                # Find or create company via service (which commits)
                existing = service.find_companies(search=company_name)
                if existing:
                    company_id = existing[0].id
                else:
                    company = service.add_company(name=company_name)
                    company_id = company.id

            if company_id:
                job = service.add_job(
                    company_id=int(company_id),
                    title=request.form.get('title', '').strip(),
                    description=request.form.get('description', '').strip(),
                    location=request.form.get('location', '').strip(),
                    remote_type=request.form.get('remote_type'),
                    salary_min=int(request.form.get('salary_min')) if request.form.get('salary_min') else None,
                    salary_max=int(request.form.get('salary_max')) if request.form.get('salary_max') else None,
                    job_url=request.form.get('job_url', '').strip(),
                    source=request.form.get('source', '').strip(),
                    is_flagged=bool(request.form.get('is_flagged'))
                )
                flash('Job added successfully!', 'success')
                return redirect(url_for('jobs.jobs'))
            else:
                flash('Please select or enter a company.', 'error')

        companies = service.companies.get_all()
        return render_template('job_form.html', companies=companies)
    finally:
        session.close()


@bp.route('/jobs/<int:job_id>/flag', methods=['POST'])
@login_required
def toggle_job_flag(job_id):
    """Toggle the flagged/saved status of a job."""
    service, session = get_service()
    try:
        job = service.jobs.toggle_flag(job_id)
        session.commit()
        if job:
            status = 'saved' if job.is_flagged else 'unsaved'
            flash(f'Job {status}!', 'success')
        return redirect(request.referrer or url_for('jobs.jobs'))
    finally:
        session.close()


@bp.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    """Delete a job listing."""
    service, session = get_service()
    try:
        job = service.jobs.get_by_id(job_id)
        if job:
            # Check if job has applications
            if job.applications:
                flash('This job has linked applications. Remove those applications first before deleting.', 'error')
            else:
                service.jobs.delete(job_id)
                session.commit()
                flash('Job deleted!', 'success')
        else:
            flash('Job not found.', 'error')
        return redirect(url_for('jobs.jobs'))
    finally:
        session.close()


@bp.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    """Edit job details."""
    service, session = get_service()
    try:
        job = service.jobs.get_by_id(job_id)
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('applications.applications'))

        if request.method == 'POST':
            updates = {
                'title': request.form.get('title', job.title),
                'description': request.form.get('description'),
                'requirements': request.form.get('requirements'),
                'location': request.form.get('location'),
                'remote_type': request.form.get('remote_type'),
                'job_url': request.form.get('job_url'),
                'source': request.form.get('source'),
            }

            salary_min = request.form.get('salary_min')
            salary_max = request.form.get('salary_max')
            if salary_min:
                updates['salary_min'] = int(salary_min)
            if salary_max:
                updates['salary_max'] = int(salary_max)

            service.jobs.update(job_id, **updates)
            session.commit()
            flash('Job updated!', 'success')

            # Redirect back to application if we came from there
            app_id = request.args.get('app_id')
            if app_id:
                return redirect(url_for('applications.application_detail', app_id=app_id))
            return redirect(url_for('jobs.jobs'))

        return render_template('edit_job.html', job=job)
    finally:
        session.close()
