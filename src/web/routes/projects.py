"""Routes for projects and resources."""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from ..helpers import get_service, get_service_for_user
from ...models import Project, Resource

bp = Blueprint('projects', __name__)


@bp.route('/api/projects', methods=['GET'])
@login_required
def list_projects():
    """List all projects for the current user."""
    service, session = get_service()
    try:
        projects = session.query(Project).filter(Project.user_id == current_user.id).all()
        return jsonify({
            'success': True,
            'projects': [p.to_dict() for p in projects]
        })
    finally:
        session.close()


@bp.route('/api/projects', methods=['POST'])
@login_required
def create_project():
    """Create a new project."""
    service, session = get_service()
    try:
        data = request.get_json()
        project = Project(
            user_id=current_user.id,
            name=data.get('name'),
            description=data.get('description', ''),
            color=data.get('color', '#3B82F6')
        )
        session.add(project)
        session.commit()
        return jsonify({
            'success': True,
            'project': project.to_dict()
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@bp.route('/api/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """Get a single project with all its resources."""
    service, session = get_service()
    try:
        project = session.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        return jsonify({
            'success': True,
            'project': project.to_dict()
        })
    finally:
        session.close()


@bp.route('/api/projects/<int:project_id>', methods=['PATCH'])
@login_required
def update_project(project_id):
    """Update a project."""
    service, session = get_service()
    try:
        project = session.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        data = request.get_json()
        if 'name' in data:
            project.name = data['name']
        if 'description' in data:
            project.description = data['description']
        if 'color' in data:
            project.color = data['color']
        
        session.commit()
        return jsonify({
            'success': True,
            'project': project.to_dict()
        })
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@bp.route('/api/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    """Delete a project and all its resources."""
    service, session = get_service()
    try:
        project = session.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        session.delete(project)
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@bp.route('/api/projects/<int:project_id>/resources', methods=['POST'])
@login_required
def create_resource(project_id):
    """Create a new resource in a project."""
    service, session = get_service()
    try:
        # Verify project ownership
        project = session.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        data = request.get_json()
        resource = Resource(
            project_id=project_id,
            name=data.get('name'),
            url=data.get('url'),
            description=data.get('description', ''),
            resource_type=data.get('type', 'document')
        )
        session.add(resource)
        session.commit()
        return jsonify({
            'success': True,
            'resource': resource.to_dict()
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@bp.route('/api/resources/<int:resource_id>', methods=['PATCH'])
@login_required
def update_resource(resource_id):
    """Update a resource."""
    service, session = get_service()
    try:
        resource = session.query(Resource).join(Project).filter(
            Resource.id == resource_id,
            Project.user_id == current_user.id
        ).first()
        
        if not resource:
            return jsonify({'success': False, 'error': 'Resource not found'}), 404
        
        data = request.get_json()
        if 'name' in data:
            resource.name = data['name']
        if 'url' in data:
            resource.url = data['url']
        if 'description' in data:
            resource.description = data['description']
        if 'type' in data:
            resource.resource_type = data['type']
        
        session.commit()
        return jsonify({
            'success': True,
            'resource': resource.to_dict()
        })
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@bp.route('/api/resources/<int:resource_id>', methods=['DELETE'])
@login_required
def delete_resource(resource_id):
    """Delete a resource."""
    service, session = get_service()
    try:
        resource = session.query(Resource).join(Project).filter(
            Resource.id == resource_id,
            Project.user_id == current_user.id
        ).first()
        
        if not resource:
            return jsonify({'success': False, 'error': 'Resource not found'}), 404
        
        session.delete(resource)
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()
