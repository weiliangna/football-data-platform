from common.platform_registry import default_platform_id
from spider.caizhanyun_detail import get_detail
from spider.magicangle_contract import build_record
from spider.platform_pending import load_pending_order_refs
from spider.unified_ingestion import DatabaseRepository, ingest_records


PLATFORM_ID = default_platform_id("caizhanyun")
PLATFORM_NAME = "彩站云"


def sync_pending_results(
    platform_id=PLATFORM_ID,
    limit=100,
    repository=None,
    detail_fetcher=None,
    pending_refs=None,
):
    refs = pending_refs
    if refs is None:
        refs = load_pending_order_refs(platform_id, limit=limit)
    rows = [
        {
            "id": str(ref.get("platform_order_id") or ""),
            "starterId": ref.get("user_id"),
            "staterName": ref.get("nickname"),
        }
        for ref in refs[:max(int(limit), 0)]
        if str(ref.get("platform_order_id") or "").strip()
    ]
    target_repository = repository or DatabaseRepository()
    fetch_detail = detail_fetcher or get_detail

    def fetch(item):
        source_id = str(item.get("id") or "").strip()
        return source_id, fetch_detail(source_id)

    return ingest_records(
        rows,
        fetch,
        lambda item, detail: build_record(
            item,
            detail,
            platform_id=int(platform_id),
            platform_name=PLATFORM_NAME,
            avatar_source="caizhanyun_result_sync",
        ),
        int(platform_id),
        PLATFORM_NAME,
        target_repository,
    )


def main():
    summary = sync_pending_results()
    print(
        "彩站云赛果同步完成:",
        "总数",
        summary["total_count"],
        "失败",
        summary["failed_count"],
    )
    if summary["failed_count"]:
        raise SystemExit(1)
    return summary


if __name__ == "__main__":
    main()
