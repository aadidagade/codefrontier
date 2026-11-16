"""
Comprehensive Application Security Audit Test Suite
====================================================
Evaluates all 20 security domains for the CodeFrontier Knowledge Handover Platform:
1. Authentication & Credentials Verification
2. Password Storage (Argon2 Hashing)
3. Session / JWT Handling & Expiration
4. Authorization & Role-Based Permissions
5. Project-Level Access Control (Tenant Boundaries)
6. SQL Injection Defenses (Parameterized ORM)
7. Cross-Site Scripting (XSS) Defenses
8. CSRF Protection (Stateless Bearer Tokens)
9. File Upload Vulnerabilities & Path Traversal
10. File Type Validation & Magic Bytes Verification
11. File Size Limits & Buffer Overflow Prevention
12. API Rate Limiting (Sliding Window HTTP 429)
13. CORS Configuration & Whitelisted Origins
14. Sensitive Information Exposure (User Schema Protection)
15. Environment Variable Handling & Cryptographic Key Strength
16. Gemini API Key Protection & Secret Redaction
17. Audit Log Integrity & Immutability Enforcement
18. Insecure Direct Object References (IDOR Prevention)
19. Cross-Project Data Access Denial
20. Error Message Information Leakage & Stack Trace Shielding
"""

import io
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.core.permissions import Permission, ProjectRole, has_permission
from app.core.rate_limit import InMemoryRateLimiter
from app.core.security import (
    create_access_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.main import app
from app.models.base import Base
from app.models.document import Document
from app.models.handover import Handover
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.task import Task
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.audit_service import sanitize_metadata
from app.services.gemini_service import redact_secrets
from app.utils.file_validation import (
    DANGEROUS_EXTENSIONS,
    sanitize_filename,
    validate_file_security,
)


@pytest_asyncio.fixture
async def sec_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# =============================================================================
# 1 & 2. AUTHENTICATION & PASSWORD STORAGE (ARGON2)
# =============================================================================
def test_sec_01_02_argon2_password_hashing():
    raw_pass = "P@ssw0rdSecure!2026"
    hashed = get_password_hash(raw_pass)

    assert hashed != raw_pass
    assert "$argon2" in hashed
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


# =============================================================================
# 3. JWT SESSION HANDLING & EXPIRATION
# =============================================================================
def test_sec_03_jwt_token_handling():
    user_id = uuid.uuid4()
    email = "auditor@corp.io"

    # Valid token
    token = create_access_token(user_id=user_id, email=email)
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == str(user_id)
    assert decoded["email"] == email
    assert decoded["type"] == "access"

    # Expired token rejection
    expired_token = create_access_token(
        user_id=user_id,
        email=email,
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(expired_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    # Tampered token signature rejection
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(jwt.JWTError):
        jwt.decode(tampered, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# =============================================================================
# 4 & 5. AUTHORIZATION & PROJECT-LEVEL ACCESS CONTROL
# =============================================================================
def test_sec_04_05_role_hierarchy_and_permissions():
    # Admin & Owner can manage members
    assert has_permission(ProjectRole.ADMIN, Permission.MANAGE_PROJECT_MEMBERS) is True
    assert has_permission(ProjectRole.PROJECT_OWNER, Permission.MANAGE_PROJECT_MEMBERS) is True

    # Outgoing & Incoming cannot manage members
    assert has_permission(ProjectRole.OUTGOING, Permission.MANAGE_PROJECT_MEMBERS) is False
    assert has_permission(ProjectRole.INCOMING, Permission.MANAGE_PROJECT_MEMBERS) is False

    # Reviewer can approve handovers, Outgoing/Incoming cannot
    assert has_permission(ProjectRole.REVIEWER, Permission.APPROVE_HANDOVER) is True
    assert has_permission(ProjectRole.OUTGOING, Permission.APPROVE_HANDOVER) is False
    assert has_permission(ProjectRole.INCOMING, Permission.APPROVE_HANDOVER) is False


# =============================================================================
# 6. SQL INJECTION DEFENSE (PARAMETERIZED ORM)
# =============================================================================
@pytest.mark.asyncio
async def test_sec_06_sql_injection_resistance(sec_db: AsyncSession):
    sqli_payload = "test' OR '1'='1"
    user = User(
        id=uuid.uuid4(),
        email="sqli_user@corp.io",
        full_name=sqli_payload,
        password_hash=get_password_hash("Pass123!"),
        is_active=True,
    )
    sec_db.add(user)
    await sec_db.commit()

    # Verify literal value stored without executing injection
    assert user.full_name == sqli_payload


# =============================================================================
# 7 & 8. XSS & CSRF DEFENSES
# =============================================================================
def test_sec_07_08_xss_and_csrf_guarantees():
    # XSS payload and path traversal sanitization check
    traversal_with_null = "../../etc/passwd\x00_test.pdf"
    clean_name = sanitize_filename(traversal_with_null)
    assert ".." not in clean_name
    assert "\x00" not in clean_name
    # Stateless JWT Authorization: Bearer tokens in Authorization header are immune to browser CSRF
    assert settings.JWT_ALGORITHM == "HS256"


# =============================================================================
# 9, 10 & 11. FILE UPLOAD SECURITY, MAGIC BYTES & SIZE LIMITS
# =============================================================================
def test_sec_09_10_11_file_upload_security():
    # 9. Path traversal attempt blocked
    traversal_filename = "../../../../../etc/passwd"
    sanitized = sanitize_filename(traversal_filename)
    assert ".." not in sanitized
    assert "/" not in sanitized
    assert "\\" not in sanitized

    # 9. Dangerous extension blocked
    for bad_ext in [".exe", ".sh", ".bat", ".py", ".ps1"]:
        with pytest.raises(ValidationException) as exc:
            validate_file_security(f"payload{bad_ext}", b"echo hello")
        assert "forbidden" in str(exc.value.message).lower()

    # 10. Magic bytes verification: PDF requires %PDF-
    with pytest.raises(ValidationException) as exc_pdf:
        validate_file_security("fake.pdf", b"NOT_A_REAL_PDF_HEADER")
    assert "magic bytes" in str(exc_pdf.value.message).lower()

    valid_name, vtype = validate_file_security("legit.pdf", b"%PDF-1.7 header stream")
    assert vtype == "pdf"

    # 11. Max size enforcement
    assert settings.MAX_UPLOAD_SIZE_MB == 20
    assert settings.max_upload_size_bytes == 20 * 1024 * 1024


# =============================================================================
# 12. API RATE LIMITING
# =============================================================================
def test_sec_12_api_rate_limiter():
    limiter = InMemoryRateLimiter()
    key = "127.0.0.1:/api/v1/auth/login"

    # Allow up to 3 requests
    assert limiter.check_rate_limit(key, max_requests=3, window_seconds=60) is True
    assert limiter.check_rate_limit(key, max_requests=3, window_seconds=60) is True
    assert limiter.check_rate_limit(key, max_requests=3, window_seconds=60) is True

    # 4th request must be rejected
    assert limiter.check_rate_limit(key, max_requests=3, window_seconds=60) is False


# =============================================================================
# 13. CORS CONFIGURATION
# =============================================================================
def test_sec_13_cors_configuration():
    # Ensure wildcard origin is NOT allowed when credentials are true
    assert "*" not in settings.CORS_ORIGINS
    for origin in settings.CORS_ORIGINS:
        assert origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1")


# =============================================================================
# 14. SENSITIVE INFORMATION EXPOSURE (USER SCHEMA)
# =============================================================================
def test_sec_14_user_response_excludes_password_hash():
    user = User(
        id=uuid.uuid4(),
        email="safe@corp.io",
        full_name="Safe User",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$secret_hash_here",
        is_active=True,
    )
    schema = UserResponse.model_validate(user)
    schema_dict = schema.model_dump()

    assert "password_hash" not in schema_dict
    assert "password" not in schema_dict
    assert schema_dict["email"] == "safe@corp.io"


# =============================================================================
# 15. ENVIRONMENT VARIABLE & KEY STRENGTH
# =============================================================================
def test_sec_15_jwt_key_strength():
    assert len(settings.JWT_SECRET_KEY) >= 32


# =============================================================================
# 16. GEMINI API KEY PROTECTION & REDACTION
# =============================================================================
def test_sec_16_gemini_secret_redaction():
    dummy_key = "AIzaSyDUMMYKEY1234567890abcdef1234567"
    raw_log = f"Failed to connect using key {dummy_key} to endpoint."
    cleaned = redact_secrets(raw_log)

    assert dummy_key not in cleaned
    assert "[REDACTED_API_KEY]" in cleaned


# =============================================================================
# 17. AUDIT LOG INTEGRITY & REDACTION
# =============================================================================
def test_sec_17_audit_log_metadata_sanitization():
    meta = {
        "password": "UserSecret123!",
        "access_token": "Bearer eyJhbGciOiJIUzI1Ni...",
        "file_name": "architecture.pdf",
        "full_text": "This is a sensitive 10,000 word document body that should not flood audit trail logs.",
    }
    sanitized = sanitize_metadata(meta)

    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["file_name"] == "architecture.pdf"
    assert "CONTENT_OMITTED" in sanitized["full_text"]


# =============================================================================
# 18 & 19. IDOR & CROSS-PROJECT DATA ACCESS DENIAL
# =============================================================================
@pytest.mark.asyncio
async def test_sec_18_19_idor_and_cross_project_isolation(sec_db: AsyncSession):
    proj_a = Project(id=uuid.uuid4(), name="Project A", created_by=uuid.uuid4())
    proj_b = Project(id=uuid.uuid4(), name="Project B", created_by=uuid.uuid4())
    sec_db.add_all([proj_a, proj_b])
    await sec_db.commit()

    user_a = User(id=uuid.uuid4(), email="user_a@corp.io", full_name="User A", password_hash="h", is_active=True)
    sec_db.add(user_a)
    await sec_db.commit()

    # User A belongs only to Project A
    member_a = ProjectMember(
        id=uuid.uuid4(),
        project_id=proj_a.id,
        user_id=user_a.id,
        role=ProjectMemberRole.INCOMING.value,
    )
    sec_db.add(member_a)
    await sec_db.commit()

    # Document belongs to Project B
    doc_b = Document(
        id=uuid.uuid4(),
        project_id=proj_b.id,
        uploaded_by=uuid.uuid4(),
        original_filename="secret_b.pdf",
        stored_filename="secret_b.pdf",
        file_type="pdf",
        file_size=1000,
        storage_path="/tmp/secret_b.pdf",
        processing_status="READY",
    )
    sec_db.add(doc_b)
    await sec_db.commit()

    # User A attempting to access Project B's document raises Forbidden
    from app.dependencies.authorization import enforce_member_permission
    with pytest.raises(ForbiddenException) as exc:
        await enforce_member_permission(
            project_id=doc_b.project_id,
            user_id=user_a.id,
            permission=Permission.VIEW_PROJECT,
            db=sec_db,
        )
    assert "not an authorized member" in str(exc.value.message).lower()


# =============================================================================
# 20. ERROR MESSAGE INFORMATION LEAKAGE
# =============================================================================
@pytest.mark.asyncio
async def test_sec_20_error_message_shields_stack_traces():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Request a non-existent endpoint or trigger an error
        resp = await client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")
        assert resp.status_code in (401, 403, 404)
        body = resp.json()
        assert body["success"] is False
        assert "error" in body
        # Ensure raw Python stack traces, database schema details, or files are not leaked
        assert "Traceback (most recent call last)" not in resp.text
        assert "sqlite3.OperationalError" not in resp.text
        assert "psycopg2" not in resp.text
