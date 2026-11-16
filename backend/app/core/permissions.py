import enum
from typing import Dict, List, Optional, Set, Union


class Permission(str, enum.Enum):
    """
    Granular permissions for project workspace operations.
    """
    VIEW_PROJECT = "view_project"
    EDIT_PROJECT = "edit_project"
    UPLOAD_DOCUMENTS = "upload_documents"
    DELETE_DOCUMENTS = "delete_documents"
    GENERATE_HANDOVER = "generate_handover"
    VIEW_HANDOVER = "view_handover"
    EDIT_HANDOVER = "edit_handover"
    SUBMIT_HANDOVER_FOR_REVIEW = "submit_handover_for_review"
    APPROVE_HANDOVER = "approve_handover"
    SHARE_HANDOVER = "share_handover"
    MANAGE_PROJECT_MEMBERS = "manage_project_members"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    RESOLVE_CONFLICT = "resolve_conflict"

    # Explicit override permission for incoming members on approved handovers
    EDIT_APPROVED_HANDOVER = "edit_approved_handover"


class ProjectRole(str, enum.Enum):
    """
    Authorized system roles for project members.
    """
    ADMIN = "ADMIN"
    PROJECT_OWNER = "PROJECT_OWNER"
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"
    REVIEWER = "REVIEWER"
    LEAD = "LEAD"  # Backward compatibility alias


# Canonical display names for roles
ROLE_DISPLAY_NAMES = {
    ProjectRole.ADMIN: "Admin",
    ProjectRole.PROJECT_OWNER: "Project Owner",
    ProjectRole.OUTGOING: "Outgoing Member",
    ProjectRole.INCOMING: "Incoming Member",
    ProjectRole.REVIEWER: "Reviewer",
    ProjectRole.LEAD: "Lead",
}


def normalize_role(role: Union[ProjectRole, str]) -> ProjectRole:
    """
    Normalizes any role input (case-insensitive, user-facing label or enum name)
    to a canonical ProjectRole.
    """
    if isinstance(role, ProjectRole):
        return role

    if hasattr(role, "value"):
        raw = str(role.value)
    else:
        raw = str(role)

    # Strip enum class prefix if present (e.g. "ProjectMemberRole.OUTGOING" -> "OUTGOING")
    if "." in raw:
        raw = raw.split(".")[-1]

    val = raw.strip().upper().replace(" ", "_").replace("-", "_")

    alias_map = {
        "ADMIN": ProjectRole.ADMIN,
        "ADMINISTRATOR": ProjectRole.ADMIN,
        "PROJECT_OWNER": ProjectRole.PROJECT_OWNER,
        "OWNER": ProjectRole.PROJECT_OWNER,
        "OUTGOING": ProjectRole.OUTGOING,
        "OUTGOING_MEMBER": ProjectRole.OUTGOING,
        "INCOMING": ProjectRole.INCOMING,
        "INCOMING_MEMBER": ProjectRole.INCOMING,
        "REVIEWER": ProjectRole.REVIEWER,
        "LEAD": ProjectRole.LEAD,
    }

    if val in alias_map:
        return alias_map[val]

    # Try direct enum matching
    try:
        return ProjectRole(val)
    except ValueError:
        return ProjectRole.INCOMING


# Default Permission Mapping Matrix per Role
ROLE_PERMISSIONS: Dict[ProjectRole, Set[Permission]] = {
    ProjectRole.ADMIN: {
        Permission.VIEW_PROJECT,
        Permission.EDIT_PROJECT,
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.GENERATE_HANDOVER,
        Permission.VIEW_HANDOVER,
        Permission.EDIT_HANDOVER,
        Permission.SUBMIT_HANDOVER_FOR_REVIEW,
        Permission.APPROVE_HANDOVER,
        Permission.SHARE_HANDOVER,
        Permission.MANAGE_PROJECT_MEMBERS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.RESOLVE_CONFLICT,
        Permission.EDIT_APPROVED_HANDOVER,
    },
    ProjectRole.PROJECT_OWNER: {
        Permission.VIEW_PROJECT,
        Permission.EDIT_PROJECT,
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.GENERATE_HANDOVER,
        Permission.VIEW_HANDOVER,
        Permission.EDIT_HANDOVER,
        Permission.SUBMIT_HANDOVER_FOR_REVIEW,
        Permission.APPROVE_HANDOVER,
        Permission.SHARE_HANDOVER,
        Permission.MANAGE_PROJECT_MEMBERS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.RESOLVE_CONFLICT,
        Permission.EDIT_APPROVED_HANDOVER,
    },
    ProjectRole.OUTGOING: {
        Permission.VIEW_PROJECT,
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.GENERATE_HANDOVER,
        Permission.VIEW_HANDOVER,
        Permission.EDIT_HANDOVER,
        Permission.SUBMIT_HANDOVER_FOR_REVIEW,
        Permission.SHARE_HANDOVER,
        Permission.VIEW_AUDIT_LOGS,
    },
    ProjectRole.INCOMING: {
        Permission.VIEW_PROJECT,
        Permission.VIEW_HANDOVER,
    },
    ProjectRole.REVIEWER: {
        Permission.VIEW_PROJECT,
        Permission.VIEW_HANDOVER,
        Permission.SUBMIT_HANDOVER_FOR_REVIEW,
        Permission.APPROVE_HANDOVER,
        Permission.SHARE_HANDOVER,
        Permission.VIEW_AUDIT_LOGS,
    },
    ProjectRole.LEAD: {
        Permission.VIEW_PROJECT,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_HANDOVER,
        Permission.EDIT_HANDOVER,
        Permission.SUBMIT_HANDOVER_FOR_REVIEW,
        Permission.APPROVE_HANDOVER,
        Permission.SHARE_HANDOVER,
        Permission.VIEW_AUDIT_LOGS,
        Permission.RESOLVE_CONFLICT,
    },
}


def get_member_permissions(
    role: Union[ProjectRole, str],
    custom_permissions: Optional[Union[List[str], Set[str]]] = None,
) -> Set[Permission]:
    """
    Computes effective permissions for a project member, combining role defaults
    with any explicit custom permission overrides.
    """
    canonical_role = normalize_role(role)
    effective = set(ROLE_PERMISSIONS.get(canonical_role, set()))

    if custom_permissions:
        for p in custom_permissions:
            try:
                if isinstance(p, Permission):
                    effective.add(p)
                elif isinstance(p, str):
                    effective.add(Permission(p))
            except ValueError:
                pass

    return effective


def has_permission(
    role: Union[ProjectRole, str],
    permission: Permission,
    custom_permissions: Optional[Union[List[str], Set[str]]] = None,
    handover_status: Optional[str] = None,
) -> bool:
    """
    Evaluates whether a role (with optional custom permissions) has permission to execute
    an operation, enforcing special business rules such as:
    - Requirement 4: Prevent incoming members from editing approved handovers unless explicitly permitted.
    """
    canonical_role = normalize_role(role)
    perms = get_member_permissions(canonical_role, custom_permissions)

    if permission not in perms:
        return False

    # Enforcement: Incoming members cannot edit approved handovers unless explicitly permitted
    if permission == Permission.EDIT_HANDOVER and canonical_role == ProjectRole.INCOMING:
        if handover_status:
            status_upper = handover_status.strip().upper()
            if status_upper in ("APPROVED", "SHARED", "ACKNOWLEDGED"):
                # Must have explicit EDIT_APPROVED_HANDOVER override
                if Permission.EDIT_APPROVED_HANDOVER not in perms:
                    return False

    return True
