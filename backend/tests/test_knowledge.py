from fastapi.testclient import TestClient


def test_knowledge_catalog_endpoints(client: TestClient, auth_headers_factory) -> None:
    headers = auth_headers_factory()

    list_response = client.get("/knowledge/lessons", headers=headers)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert "lessons" in payload
    lessons = payload["lessons"]
    assert any(lesson["lesson_id"] == "civil-discovery-foundations" for lesson in lessons)
    filters = payload["filters"]
    assert "discovery" in filters["tags"]
    assert "difficulty" in filters and "advanced" in filters["difficulty"]

    lesson_id = lessons[0]["lesson_id"]
    detail_response = client.get(f"/knowledge/lessons/{lesson_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["lesson_id"] == lesson_id
    assert detail["sections"], "lesson should expose sections"

    first_section = detail["sections"][0]
    progress_response = client.post(
        f"/knowledge/lessons/{lesson_id}/progress",
        json={"section_id": first_section["id"], "completed": True},
        headers=headers,
    )
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()
    assert first_section["id"] in progress_payload["completed_sections"]
    assert progress_payload["percent_complete"] >= 1.0 / max(1, progress_payload["total_sections"])

    bookmark_response = client.post(
        f"/knowledge/lessons/{lesson_id}/bookmark",
        json={"bookmarked": True},
        headers=headers,
    )
    assert bookmark_response.status_code == 200
    bookmark_payload = bookmark_response.json()
    assert bookmark_payload["bookmarked"] is True
    assert lesson_id in bookmark_payload["bookmarks"]

    refreshed_detail = client.get(f"/knowledge/lessons/{lesson_id}", headers=headers)
    assert refreshed_detail.status_code == 200
    refreshed = refreshed_detail.json()
    assert refreshed["progress"]["completed_sections"]
    assert refreshed["bookmarked"] is True

    search_response = client.post(
        "/knowledge/search",
        json={"query": "litigation holds", "limit": 5},
        headers=headers,
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload["results"], "search should return at least one hit"
    top_hit = search_payload["results"][0]
    assert "litigation" in top_hit["snippet"].lower()
    assert top_hit["lesson_id"] in {lesson["lesson_id"] for lesson in lessons}
