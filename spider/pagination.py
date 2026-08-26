def collect_numbered_pages(
    fetch_page,
    parse_rows,
    identity,
    page_size=50,
    start_page=1,
    max_pages=100,
    metadata=None,
):
    """Collect a numbered endpoint without assuming its final page."""
    size = max(int(page_size), 1)
    page = max(int(start_page), 1)
    limit = max(int(max_pages), 1)
    rows = []
    seen = set()

    for _ in range(limit):
        response = fetch_page(page, size)
        page_rows = list(parse_rows(response) or [])
        added = 0

        for item in page_rows:
            key = str(identity(item) or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append(item)
            added += 1

        state = metadata(response) if metadata else {}
        state = state if isinstance(state, dict) else {}
        total = state.get("total")
        has_next = state.get("has_next")
        next_page = state.get("next_page")

        known_total = total not in (None, "")
        if known_total:
            try:
                if len(rows) >= int(total):
                    break
            except (TypeError, ValueError):
                pass
        if has_next is False or not page_rows or added == 0:
            break
        if (
            has_next is None
            and not known_total
            and len(page_rows) < size
        ):
            break

        if next_page not in (None, ""):
            try:
                candidate = int(next_page)
            except (TypeError, ValueError):
                candidate = page + 1
            page = candidate if candidate > page else page + 1
        else:
            page += 1

    return rows
