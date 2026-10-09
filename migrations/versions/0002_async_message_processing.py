"""Stage 1 processing persistence. Maintenance-window migration; no worker code.

Reject ambiguous legacy processing history. Never run old admission against this
revision: Stage 2 must supply sequences and atomically insert jobs.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Lock before inspecting data; migration must not race legacy admissions or revocation.
    op.execute("""
        LOCK TABLE users, courses, enrollments, assignments, problems,
            assignment_problems, student_assignment_eligibility,
            coaching_sessions, messages, idempotency_records IN ACCESS EXCLUSIVE MODE;
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM messages
                       WHERE author_type <> 'student' OR processing_status <> 'PENDING') THEN
                RAISE EXCEPTION '0002 requires review of existing non-PENDING/tutor history';
            END IF;
            IF EXISTS (
                SELECT 1 FROM messages m
                JOIN coaching_sessions s ON s.id = m.session_id
                LEFT JOIN idempotency_records i ON i.message_id = m.id
                WHERE i.id IS NULL OR i.student_id <> s.student_user_id
                   OR i.operation <> 'create_student_message'
            ) THEN
                RAISE EXCEPTION '0002 requires review of legacy idempotency relationships';
            END IF;
        END $$;

        ALTER TABLE coaching_sessions
            ADD COLUMN next_message_sequence BIGINT NOT NULL DEFAULT 1,
            ADD COLUMN closure_reason VARCHAR(24);
        UPDATE coaching_sessions SET closure_reason = 'UNKNOWN' WHERE status = 'CLOSED';
        ALTER TABLE coaching_sessions
            ADD CONSTRAINT ck_coaching_sessions_next_message_sequence
                CHECK (next_message_sequence > 0),
            ADD CONSTRAINT ck_coaching_sessions_closure_reason CHECK (
                (status = 'ACTIVE' AND closure_reason IS NULL) OR
                (status = 'CLOSED' AND closure_reason IS NOT NULL AND
                 closure_reason IN ('NORMAL','ADMINISTRATIVE','UNKNOWN')));

        ALTER TABLE messages
            ADD COLUMN session_sequence BIGINT,
            ADD COLUMN in_reply_to_message_id UUID,
            DROP CONSTRAINT ck_messages_processing_status;
        WITH numbered AS (
            SELECT id, row_number() OVER (
                PARTITION BY session_id ORDER BY created_at, id
            ) AS n FROM messages
        ) UPDATE messages m SET session_sequence = numbered.n
          FROM numbered WHERE numbered.id = m.id;
        UPDATE coaching_sessions s SET next_message_sequence = (
            SELECT COALESCE(MAX(m.session_sequence), 0) + 1
            FROM messages m WHERE m.session_id = s.id
        );
        ALTER TABLE messages
            ADD CONSTRAINT ck_messages_processing_status CHECK (
                processing_status IN ('PENDING','PROCESSING','COMPLETED','FAILED','CANCELLED')),
            ADD CONSTRAINT ck_messages_processing_shape CHECK (
                (author_type = 'student' AND session_sequence IS NOT NULL AND
                 session_sequence > 0 AND in_reply_to_message_id IS NULL) OR
                (author_type = 'tutor' AND session_sequence IS NULL AND
                 in_reply_to_message_id IS NOT NULL AND processing_status = 'COMPLETED')),
            ADD CONSTRAINT uq_messages_session_sequence UNIQUE (session_id, session_sequence),
            ADD CONSTRAINT uq_messages_id_session UNIQUE (id, session_id),
            ADD CONSTRAINT uq_messages_reply UNIQUE (in_reply_to_message_id),
            ADD CONSTRAINT fk_messages_reply_session
                FOREIGN KEY (in_reply_to_message_id, session_id)
                REFERENCES messages (id, session_id) ON DELETE RESTRICT;
        CREATE UNIQUE INDEX uq_messages_processing_session ON messages (session_id)
            WHERE author_type = 'student' AND processing_status = 'PROCESSING';
        CREATE INDEX ix_messages_unresolved_sequence ON messages (session_id, session_sequence)
            WHERE author_type = 'student'
              AND processing_status IN ('PENDING','PROCESSING','FAILED');

        CREATE TABLE message_processing_jobs (
            message_id UUID CONSTRAINT pk_message_processing_jobs PRIMARY KEY,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            cycle_attempt_count INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 2,
            retry_generation INTEGER NOT NULL DEFAULT 0,
            claim_token UUID,
            worker_instance_id UUID,
            claimed_at TIMESTAMPTZ,
            lease_expires_at TIMESTAMPTZ,
            attempt_deadline_at TIMESTAMPTZ,
            next_attempt_at TIMESTAMPTZ DEFAULT clock_timestamp(),
            last_error_code VARCHAR(64),
            last_error_at TIMESTAMPTZ,
            cancel_reason VARCHAR(32),
            finished_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT fk_message_processing_jobs_message_id_messages
                FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE RESTRICT,
            CONSTRAINT ck_message_processing_jobs_attempt_counts CHECK (
                attempt_count >= cycle_attempt_count AND cycle_attempt_count >= 0 AND
                max_attempts >= 1 AND cycle_attempt_count <= max_attempts
                AND retry_generation >= 0),
            CONSTRAINT ck_message_processing_jobs_error_pair
                CHECK ((last_error_code IS NULL) = (last_error_at IS NULL)),
            CONSTRAINT ck_message_processing_jobs_error_code CHECK (
                last_error_code IN ('MODEL_TIMEOUT','MODEL_UNAVAILABLE','MODEL_RATE_LIMITED',
                'MODEL_INVALID_OUTPUT','MODEL_CONFIGURATION','POLICY_REJECTED','PROCESSING_ERROR',
                'LEASE_EXPIRED','DATABASE_FAILURE')),
            CONSTRAINT ck_message_processing_jobs_cancel_reason CHECK (
                cancel_reason IN ('ACCOUNT_DISABLED','ENROLLMENT_REVOKED','COURSEWORK_INELIGIBLE',
                'SESSION_ADMIN_CLOSED','SESSION_CLOSURE_UNKNOWN'))
        );
        CREATE INDEX ix_jobs_due ON message_processing_jobs (next_attempt_at, message_id)
            WHERE next_attempt_at IS NOT NULL;
        CREATE INDEX ix_jobs_expiring ON message_processing_jobs (lease_expires_at, message_id)
            WHERE lease_expires_at IS NOT NULL;

        INSERT INTO message_processing_jobs (message_id, cancel_reason)
        SELECT m.id, CASE
            WHEN NOT u.is_active OR u.role <> 'STUDENT' THEN 'ACCOUNT_DISABLED'
            WHEN s.status = 'CLOSED' THEN 'SESSION_CLOSURE_UNKNOWN'
            WHEN NOT EXISTS (SELECT 1 FROM enrollments e WHERE e.student_user_id = u.id
                             AND e.course_id = s.course_id AND e.status = 'ACTIVE')
                THEN 'ENROLLMENT_REVOKED'
            WHEN NOT EXISTS (
                SELECT 1 FROM assignments a
                JOIN assignment_problems ap ON ap.assignment_id = a.id
                JOIN problems p ON p.id = ap.problem_id
                JOIN student_assignment_eligibility e ON e.assignment_id = a.id
                WHERE a.id = s.assignment_id AND p.id = s.problem_id
                  AND a.course_id = s.course_id AND p.course_id = s.course_id
                  AND e.student_user_id = u.id
            ) THEN 'COURSEWORK_INELIGIBLE'
            ELSE NULL END
        FROM messages m JOIN coaching_sessions s ON s.id = m.session_id
        JOIN users u ON u.id = s.student_user_id;
        UPDATE message_processing_jobs SET next_attempt_at = NULL,
            finished_at = clock_timestamp(), updated_at = clock_timestamp()
            WHERE cancel_reason IS NOT NULL;
        UPDATE messages m SET processing_status = 'CANCELLED'
            FROM message_processing_jobs j
            WHERE j.message_id = m.id AND j.cancel_reason IS NOT NULL;
    """)
    op.execute(VALIDATION_FUNCTIONS)
    op.execute("""
        CREATE TRIGGER messages_history_guard BEFORE INSERT OR UPDATE OR DELETE ON messages
            FOR EACH ROW EXECUTE FUNCTION guard_message_history();
        CREATE TRIGGER jobs_parent_guard
            BEFORE INSERT OR UPDATE OR DELETE ON message_processing_jobs
            FOR EACH ROW EXECUTE FUNCTION lock_job_message();
        CREATE CONSTRAINT TRIGGER messages_processing_consistency
            AFTER INSERT OR UPDATE OR DELETE ON messages
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
            EXECUTE FUNCTION check_message_processing_event();
        CREATE CONSTRAINT TRIGGER jobs_processing_consistency
            AFTER INSERT OR UPDATE OR DELETE ON message_processing_jobs
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
            EXECUTE FUNCTION check_job_processing_event();
        SELECT assert_message_processing(id) FROM messages;
    """)


# Frozen SQL belongs to this revision, not imported from mutable application metadata.
VALIDATION_FUNCTIONS = """
CREATE FUNCTION assert_message_processing(target UUID) RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    m messages%ROWTYPE;
    j message_processing_jobs%ROWTYPE;
    source_author VARCHAR(16);
    replies BIGINT;
    valid BOOLEAN;
BEGIN
    SELECT * INTO m FROM messages WHERE id = target FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    IF m.author_type = 'tutor' THEN
        IF EXISTS (SELECT 1 FROM message_processing_jobs WHERE message_id = m.id) THEN
            RAISE EXCEPTION 'tutor message cannot own a processing job' USING ERRCODE = '23514';
        END IF;
        SELECT author_type INTO source_author FROM messages WHERE id = m.in_reply_to_message_id;
        IF source_author IS DISTINCT FROM 'student' THEN
            RAISE EXCEPTION 'response must reference a student message' USING ERRCODE = '23514';
        END IF;
        RETURN;
    END IF;
    SELECT * INTO j FROM message_processing_jobs WHERE message_id = m.id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'student message requires a processing job' USING ERRCODE = '23514';
    END IF;
    SELECT count(*) INTO replies FROM messages WHERE in_reply_to_message_id = m.id;
    valid := CASE m.processing_status
        WHEN 'PENDING' THEN
            j.next_attempt_at IS NOT NULL AND j.claim_token IS NULL AND
            j.worker_instance_id IS NULL AND j.claimed_at IS NULL AND
            j.lease_expires_at IS NULL AND j.attempt_deadline_at IS NULL AND
            j.cancel_reason IS NULL AND j.finished_at IS NULL AND replies = 0
        WHEN 'PROCESSING' THEN
            j.claim_token IS NOT NULL AND j.worker_instance_id IS NOT NULL AND
            j.claimed_at IS NOT NULL AND j.lease_expires_at IS NOT NULL AND
            j.attempt_deadline_at IS NOT NULL AND j.claimed_at < j.lease_expires_at AND
            j.lease_expires_at <= j.attempt_deadline_at AND
            j.next_attempt_at IS NULL AND j.cancel_reason IS NULL AND
            j.finished_at IS NULL AND replies = 0
        WHEN 'COMPLETED' THEN
            j.claim_token IS NOT NULL AND j.finished_at IS NOT NULL AND
            j.lease_expires_at IS NULL AND j.attempt_deadline_at IS NULL AND
            j.next_attempt_at IS NULL AND j.cancel_reason IS NULL AND replies = 1
        WHEN 'FAILED' THEN
            j.last_error_code IS NOT NULL AND j.last_error_at IS NOT NULL AND
            j.finished_at IS NOT NULL AND j.lease_expires_at IS NULL AND
            j.attempt_deadline_at IS NULL AND j.next_attempt_at IS NULL AND
            j.cancel_reason IS NULL AND replies = 0
        WHEN 'CANCELLED' THEN
            j.cancel_reason IS NOT NULL AND j.finished_at IS NOT NULL AND
            j.claim_token IS NULL AND j.lease_expires_at IS NULL AND
            j.attempt_deadline_at IS NULL AND j.next_attempt_at IS NULL AND replies = 0
        ELSE FALSE
    END;
    IF valid IS NOT TRUE THEN
        RAISE EXCEPTION 'message/job/result processing invariant violated' USING ERRCODE = '23514';
    END IF;
END $$;

CREATE FUNCTION guard_message_history() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'message history is append-only' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.author_type = 'student' AND NEW.processing_status <> 'PENDING' THEN
            RAISE EXCEPTION 'student message must begin PENDING' USING ERRCODE = '23514';
        END IF;
        IF NEW.in_reply_to_message_id IS NOT NULL THEN
            PERFORM 1 FROM messages WHERE id = NEW.in_reply_to_message_id FOR UPDATE;
        END IF;
        RETURN NEW;
    END IF;
    IF ROW(NEW.id, NEW.session_id, NEW.author_type, NEW.content, NEW.created_at,
           NEW.trace_id, NEW.session_sequence, NEW.in_reply_to_message_id)
       IS DISTINCT FROM
       ROW(OLD.id, OLD.session_id, OLD.author_type, OLD.content, OLD.created_at,
           OLD.trace_id, OLD.session_sequence, OLD.in_reply_to_message_id) THEN
        RAISE EXCEPTION 'message content/provenance is immutable' USING ERRCODE = '23514';
    END IF;
    IF NEW.processing_status IS DISTINCT FROM OLD.processing_status AND NOT (
        (OLD.processing_status = 'PENDING' AND
            NEW.processing_status IN ('PROCESSING','CANCELLED')) OR
        (OLD.processing_status = 'PROCESSING' AND
            NEW.processing_status IN ('PENDING','COMPLETED','FAILED','CANCELLED')) OR
        (OLD.processing_status = 'FAILED' AND NEW.processing_status IN ('PROCESSING','CANCELLED'))
    ) THEN
        RAISE EXCEPTION 'invalid processing transition' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION lock_job_message() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.message_id IS DISTINCT FROM OLD.message_id THEN
        RAISE EXCEPTION 'job message identity is immutable' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN
        PERFORM 1 FROM messages WHERE id = OLD.message_id FOR UPDATE;
        RETURN OLD;
    END IF;
    PERFORM 1 FROM messages WHERE id = NEW.message_id FOR UPDATE;
    RETURN NEW;
END $$;

CREATE FUNCTION check_message_processing_event() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP <> 'INSERT' THEN
        PERFORM assert_message_processing(OLD.id);
        IF OLD.in_reply_to_message_id IS NOT NULL THEN
            PERFORM assert_message_processing(OLD.in_reply_to_message_id);
        END IF;
    END IF;
    IF TG_OP <> 'DELETE' THEN
        PERFORM assert_message_processing(NEW.id);
        IF NEW.in_reply_to_message_id IS NOT NULL THEN
            PERFORM assert_message_processing(NEW.in_reply_to_message_id);
        END IF;
    END IF;
    RETURN NULL;
END $$;

CREATE FUNCTION check_job_processing_event() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP <> 'INSERT' THEN PERFORM assert_message_processing(OLD.message_id); END IF;
    IF TG_OP <> 'DELETE' THEN PERFORM assert_message_processing(NEW.message_id); END IF;
    RETURN NULL;
END $$;
"""


def downgrade():
    op.execute("""
        LOCK TABLE messages, message_processing_jobs IN ACCESS EXCLUSIVE MODE;
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM messages) THEN
                RAISE EXCEPTION '0002 downgrade requires empty message history';
            END IF;
        END $$;
        DROP TRIGGER messages_processing_consistency ON messages;
        DROP TRIGGER jobs_processing_consistency ON message_processing_jobs;
        DROP TRIGGER messages_history_guard ON messages;
        DROP TRIGGER jobs_parent_guard ON message_processing_jobs;
        DROP FUNCTION check_message_processing_event();
        DROP FUNCTION check_job_processing_event();
        DROP FUNCTION guard_message_history();
        DROP FUNCTION lock_job_message();
        DROP FUNCTION assert_message_processing(UUID);
        DROP TABLE message_processing_jobs;
        DROP INDEX uq_messages_processing_session;
        DROP INDEX ix_messages_unresolved_sequence;
        ALTER TABLE messages
            DROP CONSTRAINT ck_messages_processing_shape,
            DROP CONSTRAINT fk_messages_reply_session,
            DROP CONSTRAINT uq_messages_reply,
            DROP CONSTRAINT uq_messages_id_session,
            DROP CONSTRAINT uq_messages_session_sequence,
            DROP COLUMN session_sequence,
            DROP COLUMN in_reply_to_message_id,
            DROP CONSTRAINT ck_messages_processing_status,
            ADD CONSTRAINT ck_messages_processing_status CHECK (
                processing_status IN ('PENDING','PROCESSING','COMPLETED','FAILED'));
        ALTER TABLE coaching_sessions
            DROP CONSTRAINT ck_coaching_sessions_closure_reason,
            DROP CONSTRAINT ck_coaching_sessions_next_message_sequence,
            DROP COLUMN closure_reason,
            DROP COLUMN next_message_sequence;
    """)
