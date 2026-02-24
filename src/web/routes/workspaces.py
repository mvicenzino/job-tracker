"""Workspace management routes."""
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session as flask_session
from flask_login import login_required, current_user

from ...models import Workspace, WorkspaceMember

bp = Blueprint('workspaces', __name__)


def _get_db_session():
    from flask import current_app
    return current_app.extensions['db'].get_session()


@bp.route('/workspaces')
@login_required
def workspaces():
    """List user's workspaces with create/join forms."""
    session = _get_db_session()
    try:
        memberships = session.query(WorkspaceMember).filter_by(
            user_id=current_user.id
        ).all()
        ws_ids = [m.workspace_id for m in memberships]
        user_workspaces = session.query(Workspace).filter(
            Workspace.id.in_(ws_ids)
        ).all() if ws_ids else []

        # Build a role map for display
        role_map = {m.workspace_id: m.role for m in memberships}

        return render_template('workspaces.html',
                               workspaces=user_workspaces,
                               role_map=role_map,
                               active_workspace_id=flask_session.get('active_workspace_id'))
    finally:
        session.close()


@bp.route('/workspaces/create', methods=['POST'])
@login_required
def create_workspace():
    """Create a new workspace."""
    name = request.form.get('name', '').strip()
    if not name:
        flash('Workspace name is required.', 'error')
        return redirect(url_for('workspaces.workspaces'))

    session = _get_db_session()
    try:
        ws = Workspace(
            name=name,
            created_by=current_user.id,
            invite_code=uuid.uuid4().hex[:12]
        )
        session.add(ws)
        session.flush()

        # Creator is automatically an owner
        member = WorkspaceMember(
            workspace_id=ws.id,
            user_id=current_user.id,
            role='owner'
        )
        session.add(member)
        session.commit()

        flash(f'Workspace "{name}" created! Share the invite code with your team.', 'success')
        return redirect(url_for('workspaces.workspace_settings', workspace_id=ws.id))
    except Exception as e:
        session.rollback()
        flash(f'Failed to create workspace: {e}', 'error')
        return redirect(url_for('workspaces.workspaces'))
    finally:
        session.close()


@bp.route('/workspaces/join', methods=['POST'])
@login_required
def join_workspace():
    """Join a workspace via invite code."""
    code = request.form.get('invite_code', '').strip()
    if not code:
        flash('Invite code is required.', 'error')
        return redirect(url_for('workspaces.workspaces'))

    session = _get_db_session()
    try:
        ws = session.query(Workspace).filter_by(invite_code=code).first()
        if not ws:
            flash('Invalid invite code.', 'error')
            return redirect(url_for('workspaces.workspaces'))

        # Check if already a member
        existing = session.query(WorkspaceMember).filter_by(
            workspace_id=ws.id, user_id=current_user.id
        ).first()
        if existing:
            flash(f'You are already a member of "{ws.name}".', 'info')
            return redirect(url_for('workspaces.workspaces'))

        member = WorkspaceMember(
            workspace_id=ws.id,
            user_id=current_user.id,
            role='member'
        )
        session.add(member)
        session.commit()

        flash(f'You joined "{ws.name}"!', 'success')
        return redirect(url_for('workspaces.workspaces'))
    except Exception as e:
        session.rollback()
        flash(f'Failed to join workspace: {e}', 'error')
        return redirect(url_for('workspaces.workspaces'))
    finally:
        session.close()


@bp.route('/workspaces/switch', methods=['POST'])
@login_required
def switch_workspace():
    """Switch active workspace (or back to personal)."""
    ws_id = request.form.get('workspace_id', '').strip()

    if not ws_id or ws_id == 'personal':
        flask_session.pop('active_workspace_id', None)
        flash('Switched to Personal mode.', 'success')
        return redirect(url_for('dashboard.pipeline'))

    ws_id = int(ws_id)

    # Verify membership
    session = _get_db_session()
    try:
        member = session.query(WorkspaceMember).filter_by(
            workspace_id=ws_id, user_id=current_user.id
        ).first()
        if not member:
            flash('You are not a member of that workspace.', 'error')
            return redirect(url_for('workspaces.workspaces'))

        ws = session.query(Workspace).get(ws_id)
        flask_session['active_workspace_id'] = ws_id
        flash(f'Switched to workspace "{ws.name}".', 'success')
        return redirect(url_for('dashboard.pipeline'))
    finally:
        session.close()


@bp.route('/workspaces/<int:workspace_id>/settings')
@login_required
def workspace_settings(workspace_id):
    """Workspace settings page: members, invite code."""
    session = _get_db_session()
    try:
        # Verify membership
        member = session.query(WorkspaceMember).filter_by(
            workspace_id=workspace_id, user_id=current_user.id
        ).first()
        if not member:
            flash('You are not a member of that workspace.', 'error')
            return redirect(url_for('workspaces.workspaces'))

        ws = session.query(Workspace).get(workspace_id)
        members = session.query(WorkspaceMember).filter_by(
            workspace_id=workspace_id
        ).all()

        # Load user info for each member
        from ...models import User
        member_info = []
        for m in members:
            user = session.query(User).get(m.user_id)
            member_info.append({
                'user': user,
                'role': m.role,
                'joined_at': m.created_at,
            })

        return render_template('workspace_settings.html',
                               workspace=ws,
                               members=member_info,
                               current_role=member.role)
    finally:
        session.close()


@bp.route('/workspaces/<int:workspace_id>/leave', methods=['POST'])
@login_required
def leave_workspace(workspace_id):
    """Leave a workspace."""
    session = _get_db_session()
    try:
        member = session.query(WorkspaceMember).filter_by(
            workspace_id=workspace_id, user_id=current_user.id
        ).first()
        if not member:
            flash('You are not a member of that workspace.', 'error')
            return redirect(url_for('workspaces.workspaces'))

        # Prevent sole owner from leaving
        if member.role == 'owner':
            other_owners = session.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == 'owner',
                WorkspaceMember.user_id != current_user.id
            ).count()
            if other_owners == 0:
                flash('You are the only owner. Transfer ownership or delete the workspace first.', 'error')
                return redirect(url_for('workspaces.workspace_settings', workspace_id=workspace_id))

        ws = session.query(Workspace).get(workspace_id)
        session.delete(member)
        session.commit()

        # Clear active workspace if it was this one
        if flask_session.get('active_workspace_id') == workspace_id:
            flask_session.pop('active_workspace_id', None)

        flash(f'You left "{ws.name}".', 'success')
        return redirect(url_for('workspaces.workspaces'))
    except Exception as e:
        session.rollback()
        flash(f'Failed to leave workspace: {e}', 'error')
        return redirect(url_for('workspaces.workspaces'))
    finally:
        session.close()
