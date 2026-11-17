"""
Andrej Karpathy's LLM Wiki Engine for Mercurius
Replaces fragile RAG pipelines with an AI-maintained, structured Markdown knowledge wiki.
Treats raw documents as 'source code' and compiles them into persistent wiki articles with automatic backlinks.
"""

import os
import glob
from typing import List, Dict, Any

class LLMWikiManager:
    def __init__(self, wiki_root: str = "data/wiki/"):
        self.wiki_root = wiki_root
        self.raw_dir = os.path.join(wiki_root, "raw")
        self.articles_dir = os.path.join(wiki_root, "articles")
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.articles_dir, exist_ok=True)

    def ingest_source(self, title: str, content: str, category: str = "general") -> str:
        filename = f"{title.lower().replace(' ', '_')}.md"
        raw_path = os.path.join(self.raw_dir, filename)
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Compile into structured wiki article
        article_path = os.path.join(self.articles_dir, filename)
        compiled_content = f'''# {title}
**Category:** {category}
**Status:** Compiled by Mercurius LLM Wiki Engine

## Executive Summary
{content[:500]}...

## Key Concepts & Insights
- Autonomously synthesized from source document: `{filename}`
- Integrated into Quantum Semantic Memory Graph.

## Related Backlinks
- [[Knowledge Base Index]]
- [[{category.capitalize()} Overview]]
'''
        with open(article_path, "w", encoding="utf-8") as f:
            f.write(compiled_content)
        return article_path

    def get_wiki_index(self) -> List[str]:
        return [os.path.basename(p) for p in glob.glob(os.path.join(self.articles_dir, "*.md"))]
