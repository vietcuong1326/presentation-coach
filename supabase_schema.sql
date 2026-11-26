-- ========================================================
-- AI Presentation Coach - Supabase Database Schema (MVP)
-- Copy and paste this into Supabase SQL Editor, then click RUN
-- ========================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. PROFILES
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 2. PROJECTS
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    topic TEXT,
    objectives TEXT,
    target_audience TEXT,
    presentation_type TEXT NOT NULL DEFAULT 'INDIVIDUAL' CHECK (presentation_type IN ('INDIVIDUAL', 'GROUP')),
    expected_duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 3. PROJECT MEMBERS
CREATE TABLE IF NOT EXISTS public.project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    start_time_seconds NUMERIC,
    end_time_seconds NUMERIC,
    display_order INTEGER DEFAULT 0 NOT NULL
);

-- 4. EVALUATIONS
CREATE TABLE IF NOT EXISTS public.evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'PARTIAL', 'FAILED')),
    error_code TEXT,
    error_message TEXT,
    rubric_version TEXT DEFAULT 'v1.0' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    completed_at TIMESTAMPTZ
);

-- 5. EVALUATION FILES
CREATE TABLE IF NOT EXISTS public.evaluation_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES public.evaluations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_role TEXT NOT NULL CHECK (file_role IN ('SLIDES', 'AUDIO', 'VIDEO', 'REPORT', 'OTHER')),
    storage_bucket TEXT NOT NULL DEFAULT 'presentations',
    storage_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    mime_type TEXT,
    size_bytes BIGINT,
    processing_status TEXT DEFAULT 'UPLOADED' CHECK (processing_status IN ('UPLOADED', 'PROCESSED', 'FAILED')),
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 6. TRANSCRIPTS
CREATE TABLE IF NOT EXISTS public.transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES public.evaluations(id) ON DELETE CASCADE,
    language TEXT DEFAULT 'en' NOT NULL,
    full_text TEXT NOT NULL,
    segments JSONB DEFAULT '[]'::jsonb NOT NULL,
    provider TEXT DEFAULT 'whisper' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 7. ANALYSIS REPORTS
CREATE TABLE IF NOT EXISTS public.analysis_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES public.evaluations(id) ON DELETE CASCADE,
    version INTEGER DEFAULT 1 NOT NULL,
    report_json JSONB NOT NULL,
    evaluated_count INTEGER DEFAULT 0 NOT NULL,
    not_evaluated_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    UNIQUE (evaluation_id, version)
);

-- 8. EVALUATION EVIDENCE
CREATE TABLE IF NOT EXISTS public.evaluation_evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES public.analysis_reports(id) ON DELETE CASCADE,
    criterion_id TEXT NOT NULL,
    member_id UUID REFERENCES public.project_members(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('AUDIO', 'TRANSCRIPT', 'SLIDE', 'DOCUMENT', 'USER_INPUT')),
    start_seconds NUMERIC,
    end_seconds NUMERIC,
    page_number INTEGER,
    excerpt TEXT NOT NULL,
    confidence NUMERIC,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 9. CHAT SESSIONS & MESSAGES
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES public.evaluations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('USER', 'ASSISTANT')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- ========================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ========================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluation_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can view, insert, and update their own profile
CREATE POLICY "Users can read own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Projects: Users can CRUD own projects
CREATE POLICY "Users can read own projects" ON public.projects FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own projects" ON public.projects FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own projects" ON public.projects FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own projects" ON public.projects FOR DELETE USING (auth.uid() = user_id);

-- Project Members: Accessed via project ownership
CREATE POLICY "Members viewable by project owner" ON public.project_members FOR SELECT
    USING (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_members.project_id AND projects.user_id = auth.uid()));
CREATE POLICY "Members insertable by project owner" ON public.project_members FOR INSERT
    WITH CHECK (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_members.project_id AND projects.user_id = auth.uid()));
CREATE POLICY "Members updatable by project owner" ON public.project_members FOR UPDATE
    USING (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_members.project_id AND projects.user_id = auth.uid()));
CREATE POLICY "Members deletable by project owner" ON public.project_members FOR DELETE
    USING (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_members.project_id AND projects.user_id = auth.uid()));

-- Evaluations: Owner can CRUD
CREATE POLICY "Users can read own evaluations" ON public.evaluations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own evaluations" ON public.evaluations FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own evaluations" ON public.evaluations FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own evaluations" ON public.evaluations FOR DELETE USING (auth.uid() = user_id);

-- Evaluation Files: Owner can CRUD
CREATE POLICY "Users can read own files" ON public.evaluation_files FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own files" ON public.evaluation_files FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own files" ON public.evaluation_files FOR DELETE USING (auth.uid() = user_id);

-- Transcripts: Accessible via evaluation owner
CREATE POLICY "Users can view transcripts" ON public.transcripts FOR SELECT
    USING (EXISTS (SELECT 1 FROM public.evaluations WHERE evaluations.id = transcripts.evaluation_id AND evaluations.user_id = auth.uid()));

-- Analysis Reports: Accessible via evaluation owner
CREATE POLICY "Users can view reports" ON public.analysis_reports FOR SELECT
    USING (EXISTS (SELECT 1 FROM public.evaluations WHERE evaluations.id = analysis_reports.evaluation_id AND evaluations.user_id = auth.uid()));

-- Evidence: Accessible via report -> evaluation owner
CREATE POLICY "Users can view evidence" ON public.evaluation_evidence FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.analysis_reports r
        JOIN public.evaluations e ON e.id = r.evaluation_id
        WHERE r.id = evaluation_evidence.report_id AND e.user_id = auth.uid()
    ));

-- Chat Sessions & Messages: Owner access
CREATE POLICY "Users can CRUD own chat sessions" ON public.chat_sessions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can CRUD chat messages" ON public.chat_messages FOR ALL
    USING (EXISTS (SELECT 1 FROM public.chat_sessions s WHERE s.id = chat_messages.session_id AND s.user_id = auth.uid()));

-- ========================================================
-- PRIVATE STORAGE BUCKET & RLS POLICIES (presentations)
-- Object paths follow: {user_id}/{project_id}/{file_uuid}_{filename}
-- ========================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('presentations', 'presentations', false)
ON CONFLICT (id) DO UPDATE SET public = false;

CREATE POLICY "Users can read own presentation files"
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'presentations'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users can upload own presentation files"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'presentations'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users can delete own presentation files"
ON storage.objects FOR DELETE TO authenticated
USING (
    bucket_id = 'presentations'
    AND (storage.foldername(name))[1] = auth.uid()::text
);



-- ========================================================
-- SCHEMA & TABLE PERMISSIONS (GRANTS)
-- ========================================================
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON ROUTINES TO anon, authenticated, service_role;
