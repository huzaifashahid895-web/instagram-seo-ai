# backend/tests/unit/test_phase1_models_batch.py — Phase 1 model registration smoke tests
# Cost classification: FREE + OPEN SOURCE

import unittest

from sqlalchemy.orm import configure_mappers

from app import models  # noqa: F401
from app.core.db import Base


class Phase1ModelBatchTest(unittest.TestCase):
    def test_phase1_tables_are_registered(self) -> None:
        configure_mappers()

        expected_tables = {
            "agent_runs",
            "agent_tasks",
            "analytics",
            "approval_queue",
            "audit_logs",
            "brand_profiles",
            "captions",
            "comments",
            "comment_replies",
            "content_analysis",
            "content_assets",
            "content_ideas",
            "content_performance",
            "content_strategies",
            "generated_content",
            "hashtags",
            "keywords",
            "model_configs",
            "posts",
            "post_hashtags",
            "post_keywords",
            "post_variants",
            "rag_chunks",
            "rag_documents",
            "scheduled_jobs",
            "social_accounts",
            "users",
        }

        self.assertEqual(expected_tables, set(Base.metadata.tables))

    def test_architecture_required_indexes_are_registered(self) -> None:
        configure_mappers()

        required_column_indexes = (
            ("posts", "published_at"),
            ("content_analysis", "duplicate_hash"),
            ("comments", "status"),
            ("scheduled_jobs", "run_at"),
        )

        for table_name, column_name in required_column_indexes:
            with self.subTest(table_name=table_name, column_name=column_name):
                table = Base.metadata.tables[table_name]
                self.assertTrue(any(column_name in index.columns for index in table.indexes))


if __name__ == "__main__":
    unittest.main()
