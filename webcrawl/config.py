"""配置构建模块"""

# 深度爬取相关导入
try:
    from crawl4ai.deep_crawling import (
        BFSDeepCrawlStrategy,
        DFSDeepCrawlStrategy,
        BestFirstCrawlingStrategy,
    )
    from crawl4ai.deep_crawling.filters import (
        FilterChain,
        URLPatternFilter,
        DomainFilter,
    )
    from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
    DEEP_CRAWL_AVAILABLE = True
except ImportError:
    DEEP_CRAWL_AVAILABLE = False


def build_deep_crawl_strategy(
    enabled: bool,
    strategy_type: str,
    max_depth: int,
    include_external: bool,
    max_pages: int,
    url_patterns: str,
    allowed_domains: str,
    blocked_domains: str,
    keywords: str,
    scorer_weight: float,
    score_threshold: float,
) -> object:
    """构建深度爬取策略"""
    if not DEEP_CRAWL_AVAILABLE or not enabled:
        return None

    max_pages_value = max_pages if max_pages < 1000 else None

    # 构建过滤器链
    filters = []
    
    # URL模式过滤器
    url_pattern_list = [p.strip() for p in url_patterns.split(",") if p.strip()]
    if url_pattern_list:
        filters.append(URLPatternFilter(patterns=url_pattern_list))

    # 域名过滤器
    allowed_domain_list = [d.strip() for d in allowed_domains.split(",") if d.strip()]
    blocked_domain_list = [d.strip() for d in blocked_domains.split(",") if d.strip()]
    if allowed_domain_list or blocked_domain_list:
        filters.append(DomainFilter(
            allowed_domains=allowed_domain_list if allowed_domain_list else None,
            blocked_domains=blocked_domain_list if blocked_domain_list else None
        ))

    filter_chain = FilterChain(filters) if filters else None

    # 构建评分器
    url_scorer = None
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if keyword_list:
        url_scorer = KeywordRelevanceScorer(
            keywords=keyword_list,
            weight=scorer_weight
        )

    # 根据策略类型创建策略
    score_threshold_value = score_threshold if score_threshold > -1.0 else float('-inf')

    if "BFS" in strategy_type:
        return BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=include_external,
            max_pages=max_pages_value,
            filter_chain=filter_chain,
            url_scorer=url_scorer,
            score_threshold=score_threshold_value if url_scorer else None
        )
    elif "DFS" in strategy_type:
        return DFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=include_external,
            max_pages=max_pages_value,
            filter_chain=filter_chain,
            url_scorer=url_scorer,
            score_threshold=score_threshold_value if url_scorer else None
        )
    else:  # BestFirst
        return BestFirstCrawlingStrategy(
            max_depth=max_depth,
            include_external=include_external,
            max_pages=max_pages_value,
            filter_chain=filter_chain,
            url_scorer=url_scorer
        )

