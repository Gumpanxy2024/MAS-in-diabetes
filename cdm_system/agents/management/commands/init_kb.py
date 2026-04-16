from django.core.management.base import BaseCommand

from agents.rag_service import init_knowledge_base


class Command(BaseCommand):
    help = "初始化 RAG 糖尿病知识库（扫描 knowledge_base/ 目录导入 ChromaDB）"

    def handle(self, *args, **options):
        count = init_knowledge_base()
        self.stdout.write(self.style.SUCCESS(f"知识库初始化完成，共 {count} 条记录"))
