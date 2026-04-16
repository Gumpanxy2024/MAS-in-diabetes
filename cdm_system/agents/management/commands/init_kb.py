from django.core.management.base import BaseCommand

from agents.rag_service import init_knowledge_base, reset_knowledge_base


class Command(BaseCommand):
    help = "初始化 RAG 糖尿病知识库（扫描 knowledge_base/ 目录导入 ChromaDB）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="清空现有向量库后重新导入（更新知识库内容时使用）",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("正在清空现有向量库...")
            reset_knowledge_base()
            self.stdout.write(self.style.WARNING("向量库已清空"))

        count = init_knowledge_base()
        self.stdout.write(self.style.SUCCESS(f"知识库初始化完成，共 {count} 条记录"))
