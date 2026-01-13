from app.csv_utils import build_csv_response


def test_build_csv_response_basic():
    rows = [
        {"a": 1, "b": "x"},
        {"a": 2, "b": "y"},
    ]
    fieldnames = ["a", "b"]

    resp = build_csv_response(rows, fieldnames, filename="test.csv")

    assert resp.status_code == 200
    assert resp.media_type == "text/csv"
    assert 'attachment; filename="test.csv"' in resp.headers.get(
        "Content-Disposition", ""
    )
    body = resp.body.decode("utf-8")
    assert "a,b" in body
    assert "1,x" in body
    assert "2,y" in body


