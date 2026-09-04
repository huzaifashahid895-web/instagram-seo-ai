# backend/tests/integration/test_baseline_crud.py — Phase 1 baseline DB CRUD tests
# Cost classification: FREE + OPEN SOURCE

import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.db import Base
from app.core.security import encrypt_secret, hash_password
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.agent_task import AgentTask, AgentTaskStatus
from app.models.analytics import Analytics
from app.models.approval_queue import ApprovalQueue, ApprovalStatus
from app.models.audit_log import AuditLog
from app.models.brand_profile import BrandProfile
from app.models.caption import Caption
from app.models.comment import Comment, CommentClassification, CommentSentiment, CommentStatus
from app.models.comment_reply import CommentReply, CommentReplyStatus
from app.models.content_analysis import ContentAnalysis
from app.models.content_asset import ContentAsset
from app.models.content_idea import ContentIdea
from app.models.content_performance import ContentPerformance
from app.models.content_strategy import ContentStrategy, ContentStrategyStatus
from app.models.generated_content import GeneratedContent
from app.models.hashtag import Hashtag
from app.models.keyword import Keyword
from app.models.model_config import ModelCapability, ModelConfig
from app.models.post import Post, PostStatus
from app.models.post_variant import PostVariant
from app.models.rag_chunk import RagChunk
from app.models.rag_document import RagDocument, RagSourceType
from app.models.scheduled_job import ScheduledJob, ScheduledJobStatus
from app.models.social_account import Platform, SocialAccount
from app.models.user import User


class BaselineCrudTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / "tmp" / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.temp_dir / "test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.original_encryption_key = settings.ENCRYPTION_KEY
        settings.ENCRYPTION_KEY = "test-encryption-key"
        self.db = self.SessionLocal()

        self.user = User(
            email="owner@example.com",
            hashed_password=hash_password("local-password"),
            full_name="Owner",
            is_superuser=True,
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self) -> None:
        settings.ENCRYPTION_KEY = self.original_encryption_key
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()
        self.temp_dir.rmdir()

    def test_database_connectivity(self) -> None:
        self.assertEqual(1, self.db.scalar(text("select 1")))

    def test_identity_and_social_account_crud(self) -> None:
        account = SocialAccount(
            user_id=self.user.id,
            platform=Platform.INSTAGRAM,
            platform_user_id="17841400000000000",
            username="local_operator",
            access_token_encrypted=encrypt_secret("access-token"),
            refresh_token_encrypted=encrypt_secret("refresh-token"),
            token_expires_at=datetime.utcnow() + timedelta(days=60),
            scopes='["instagram_business_basic"]',
        )
        self.db.add(account)
        self.db.commit()

        stored = self.db.scalar(select(SocialAccount).where(SocialAccount.username == "local_operator"))
        self.assertIsNotNone(stored)
        assert stored is not None
        stored.username = "updated_operator"
        self.db.commit()
        self.assertEqual("updated_operator", self.db.get(SocialAccount, stored.id).username)

        self.db.delete(stored)
        self.db.commit()
        self.assertIsNone(self.db.get(SocialAccount, stored.id))

    def test_content_pipeline_crud(self) -> None:
        account, brand = self._make_account_and_brand()
        asset = ContentAsset(
            brand_profile_id=brand.id,
            filename="clip.mp4",
            file_path="storage/raw/clip.mp4",
            file_size=1024,
            mime_type="video/mp4",
            media_type="video",
            duration=12.5,
        )
        self.db.add(asset)
        self.db.flush()
        analysis = ContentAnalysis(asset_id=asset.id, topic="local launch", duplicate_hash="hash-1")
        idea = ContentIdea(brand_profile_id=brand.id, source_asset_id=asset.id, topic="launch tip", format="reel")
        strategy = ContentStrategy(
            brand_profile_id=brand.id,
            name="Launch strategy",
            status=ContentStrategyStatus.ACTIVE,
            is_active=True,
        )
        self.db.add_all([analysis, idea, strategy])
        self.db.flush()
        generated = GeneratedContent(idea_id=idea.id, script="Open with the result.", status="approved")
        self.db.add(generated)
        self.db.commit()

        stored = self.db.get(ContentIdea, idea.id)
        self.assertEqual("launch tip", stored.topic)
        stored.status = "generated"
        self.db.commit()
        self.assertEqual("generated", self.db.get(ContentIdea, idea.id).status)

        self.db.delete(asset)
        self.db.delete(strategy)
        self.db.commit()
        self.assertIsNone(self.db.get(ContentAsset, asset.id))
        self.assertIsNone(self.db.get(ContentStrategy, strategy.id))
        self.assertIsNotNone(account)

    def test_publishing_engagement_and_analytics_crud(self) -> None:
        account, _brand, generated = self._make_publishable_content()
        keyword = Keyword(term="instagram seo", cluster="seo", relevance=0.9)
        hashtag = Hashtag(tag="#localseo", historical_performance=0.5)
        post = Post(
            generated_content_id=generated.id,
            social_account_id=account.id,
            status=PostStatus.SCHEDULED,
            caption="A useful local SEO post",
            hashtags_text='["#localseo"]',
        )
        post.keywords.append(keyword)
        post.hashtags.append(hashtag)
        self.db.add(post)
        self.db.flush()

        variant = PostVariant(post_id=post.id, variant_type="hook", variant_data='{"text":"Start here"}')
        caption = Caption(post_id=post.id, text="A useful local SEO post", cta="Save this")
        analytics = Analytics(post_id=post.id, reach=10, views=12, likes=3)
        performance = ContentPerformance(social_account_id=account.id, post_id=post.id, content_format="reel", topic="seo")
        comment = Comment(
            post_id=post.id,
            platform_comment_id="comment-1",
            author_username="follower",
            text="Great tip",
            classification=CommentClassification.PRAISE,
            sentiment=CommentSentiment.POSITIVE,
            status=CommentStatus.NEW,
        )
        self.db.add_all([variant, caption, analytics, performance, comment])
        self.db.flush()
        reply = CommentReply(comment_id=comment.id, reply_text="Thanks!", status=CommentReplyStatus.SENT)
        self.db.add(reply)
        self.db.commit()

        stored = self.db.get(Post, post.id)
        self.assertEqual(1, len(stored.comments))
        stored.status = PostStatus.PUBLISHED
        self.db.commit()
        self.assertEqual(PostStatus.PUBLISHED, self.db.get(Post, post.id).status)

        self.db.delete(stored)
        self.db.commit()
        self.assertIsNone(self.db.get(Post, post.id))

    def test_scheduler_agents_settings_rag_approvals_and_audit_crud(self) -> None:
        _account, brand = self._make_account_and_brand()
        job = ScheduledJob(job_type="publish_post", run_at=datetime.utcnow(), status=ScheduledJobStatus.PENDING)
        agent_run = AgentRun(agent_name="strategy_agent", run_type="plan", status=AgentRunStatus.RUNNING)
        model_config = ModelConfig(
            capability=ModelCapability.LLM,
            provider_name="ollama",
            model_name="qwen2.5:3b-instruct-q4_K_M",
        )
        rag_document = RagDocument(
            brand_profile_id=brand.id,
            source_type=RagSourceType.BRAND_PROFILE,
            title="Brand voice",
            content="Helpful and concise.",
        )
        approval = ApprovalQueue(
            requested_by_user_id=self.user.id,
            entity_type="post",
            entity_id=uuid.uuid4(),
            approval_type="publish",
            title="Review post",
            status=ApprovalStatus.PENDING,
        )
        audit = AuditLog(
            actor_user_id=self.user.id,
            actor_type="user",
            action="create",
            entity_type="model_config",
            entity_id=uuid.uuid4(),
        )
        self.db.add_all([job, agent_run, model_config, rag_document, approval, audit])
        self.db.flush()
        task = AgentTask(run_id=agent_run.id, task_name="score topics", status=AgentTaskStatus.SUCCEEDED)
        chunk = RagChunk(document_id=rag_document.id, chunk_index=0, text="Helpful and concise.", vector_id="vec-1")
        self.db.add_all([task, chunk])
        self.db.commit()

        job.status = ScheduledJobStatus.SUCCEEDED
        agent_run.status = AgentRunStatus.SUCCEEDED
        approval.status = ApprovalStatus.APPROVED
        model_config.max_tokens = 800
        self.db.commit()

        self.assertEqual(ScheduledJobStatus.SUCCEEDED, self.db.get(ScheduledJob, job.id).status)
        self.assertEqual(1, len(self.db.get(AgentRun, agent_run.id).tasks))
        self.assertEqual(800, self.db.get(ModelConfig, model_config.id).max_tokens)
        self.assertEqual(1, len(self.db.get(RagDocument, rag_document.id).chunks))
        self.assertEqual(ApprovalStatus.APPROVED, self.db.get(ApprovalQueue, approval.id).status)

        self.db.delete(job)
        self.db.delete(agent_run)
        self.db.delete(model_config)
        self.db.delete(rag_document)
        self.db.delete(approval)
        self.db.delete(audit)
        self.db.commit()

        self.assertIsNone(self.db.get(ScheduledJob, job.id))
        self.assertIsNone(self.db.get(AgentRun, agent_run.id))
        self.assertIsNone(self.db.get(ModelConfig, model_config.id))
        self.assertIsNone(self.db.get(RagDocument, rag_document.id))
        self.assertIsNone(self.db.get(ApprovalQueue, approval.id))
        self.assertIsNone(self.db.get(AuditLog, audit.id))

    def _make_account_and_brand(self) -> tuple[SocialAccount, BrandProfile]:
        account = SocialAccount(
            user_id=self.user.id,
            platform=Platform.INSTAGRAM,
            platform_user_id=uuid.uuid4().hex,
            username=f"operator_{uuid.uuid4().hex[:8]}",
            access_token_encrypted=encrypt_secret("access-token"),
        )
        self.db.add(account)
        self.db.flush()
        brand = BrandProfile(
            user_id=self.user.id,
            social_account_id=account.id,
            niche="local business",
            tone="helpful",
            posting_frequency="5 posts/week",
        )
        self.db.add(brand)
        self.db.commit()
        self.db.refresh(account)
        self.db.refresh(brand)
        return account, brand

    def _make_publishable_content(self) -> tuple[SocialAccount, BrandProfile, GeneratedContent]:
        account, brand = self._make_account_and_brand()
        idea = ContentIdea(brand_profile_id=brand.id, topic="local SEO checklist", format="reel")
        self.db.add(idea)
        self.db.flush()
        generated = GeneratedContent(idea_id=idea.id, script="Three local SEO checks.", status="approved")
        self.db.add(generated)
        self.db.commit()
        self.db.refresh(generated)
        return account, brand, generated


if __name__ == "__main__":
    unittest.main()
