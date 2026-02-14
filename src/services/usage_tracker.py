"""Usage tracking and feature gating for free/pro tiers."""

FREE_TIER_LIMITS = {
    'ai_scores': 5,
    'ai_cover_letters': 2,
    'ai_interview_preps': 0,  # Pro only
    'resume_versions': 3,
}


class UsageTracker:
    """Track and enforce per-user monthly AI usage limits."""

    def __init__(self, user, session):
        self.user = user
        self.session = session
        # Auto-reset counters if month changed
        user.ensure_usage_month_current()

    def can_use_ai_score(self):
        """Check if user can run another AI fit score."""
        if self.user.is_pro:
            return True, None
        used = self.user.ai_scores_used or 0
        limit = FREE_TIER_LIMITS['ai_scores']
        if used >= limit:
            return False, {
                'upgrade_required': True,
                'feature': 'AI Fit Scores',
                'used': used,
                'limit': limit,
                'message': f'You\'ve used all {limit} free AI fit scores this month. Upgrade to Pro for unlimited scores.'
            }
        return True, None

    def can_use_cover_letter(self):
        """Check if user can generate another cover letter."""
        if self.user.is_pro:
            return True, None
        used = self.user.ai_cover_letters_used or 0
        limit = FREE_TIER_LIMITS['ai_cover_letters']
        if used >= limit:
            return False, {
                'upgrade_required': True,
                'feature': 'AI Cover Letters',
                'used': used,
                'limit': limit,
                'message': f'You\'ve used all {limit} free AI cover letters this month. Upgrade to Pro for unlimited cover letters.'
            }
        return True, None

    def can_use_interview_prep(self):
        """Check if user can use interview prep (Pro only)."""
        if self.user.is_pro:
            return True, None
        return False, {
            'upgrade_required': True,
            'feature': 'Interview Prep',
            'used': 0,
            'limit': 0,
            'message': 'Interview Prep is a Pro-only feature. Upgrade to Pro to get AI-powered interview preparation.'
        }

    def can_add_resume_version(self, existing_count):
        """Check if user can add another resume version."""
        if self.user.is_pro:
            return True, None
        limit = FREE_TIER_LIMITS['resume_versions']
        if existing_count >= limit:
            return False, {
                'upgrade_required': True,
                'feature': 'Resume Versions',
                'used': existing_count,
                'limit': limit,
                'message': f'Free accounts are limited to {limit} resume versions. Upgrade to Pro for unlimited resumes.'
            }
        return True, None

    def remaining_scores(self):
        """Get remaining AI score uses for this month."""
        if self.user.is_pro:
            return None  # unlimited
        used = self.user.ai_scores_used or 0
        return max(0, FREE_TIER_LIMITS['ai_scores'] - used)

    def record_ai_score(self):
        """Record one AI score use."""
        self.user.ai_scores_used = (self.user.ai_scores_used or 0) + 1

    def record_cover_letter(self):
        """Record one cover letter use."""
        self.user.ai_cover_letters_used = (self.user.ai_cover_letters_used or 0) + 1

    def record_interview_prep(self):
        """Record one interview prep use."""
        self.user.ai_interview_preps_used = (self.user.ai_interview_preps_used or 0) + 1

    def get_usage_summary(self):
        """Get usage data for template rendering."""
        scores_used = self.user.ai_scores_used or 0
        letters_used = self.user.ai_cover_letters_used or 0
        preps_used = self.user.ai_interview_preps_used or 0

        return {
            'scores_used': scores_used,
            'scores_limit': FREE_TIER_LIMITS['ai_scores'],
            'scores_remaining': max(0, FREE_TIER_LIMITS['ai_scores'] - scores_used),
            'letters_used': letters_used,
            'letters_limit': FREE_TIER_LIMITS['ai_cover_letters'],
            'letters_remaining': max(0, FREE_TIER_LIMITS['ai_cover_letters'] - letters_used),
            'preps_used': preps_used,
            'preps_limit': FREE_TIER_LIMITS['ai_interview_preps'],
            'resume_limit': FREE_TIER_LIMITS['resume_versions'],
        }
