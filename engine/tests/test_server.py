import http.client
import json
import threading

import pytest

from apkguard.server import make_server


@pytest.fixture(scope="module")
def server():
    httpd = make_server(0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def request(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    conn.request(method, path, body=body, headers=headers or {})
    resp = conn.getresponse()
    return resp, resp.read()


def events(raw):
    return [json.loads(line) for line in raw.decode().splitlines() if line]


def test_health(server):
    resp, raw = request(server, "GET", "/health")
    assert resp.status == 200 and "flashlight" in json.loads(raw)["categories"]


def test_analyze_streams_progress_then_report(server, torch_apk):
    resp, raw = request(server, "POST", "/analyze?lang=it", torch_apk.read_bytes(),
                        {"X-Filename": "torcia.apk", "Origin": "http://localhost:5173"})
    assert resp.status == 200 and resp.getheader("Access-Control-Allow-Origin") == "http://localhost:5173"
    out = events(raw)
    assert out[0]["event"] == "progress" and out[-1]["event"] == "report"
    report = out[-1]["report"]
    assert report["file"]["name"] == "torcia.apk"  # not the server-side temp name
    assert report["verdict"]["text"]["title"] == "Non installare"


def test_category_parameter(server, torch_apk):
    _, raw = request(server, "POST", "/analyze?category=messaging", torch_apk.read_bytes())
    assert events(raw)[-1]["report"]["category"]["source"] == "user"


def test_bad_file_is_a_stream_error(server, plain_text):
    _, raw = request(server, "POST", "/analyze?lang=en", plain_text.read_bytes())
    last = events(raw)[-1]
    assert last["event"] == "error" and last["code"] == "not_zip"


def test_empty_body_and_missing_length(server):
    _, raw = request(server, "POST", "/analyze", b"")
    assert events(raw)[-1]["code"] == "empty"


def test_foreign_origin_is_rejected(server, benign_apk):
    resp, _ = request(server, "POST", "/analyze", benign_apk.read_bytes(),
                      {"Origin": "https://evil.example"})
    assert resp.status == 403


def test_foreign_host_header_is_rejected(server):
    resp, _ = request(server, "GET", "/health", headers={"Host": "attacker.example"})
    assert resp.status == 403


def test_unknown_route(server):
    resp, _ = request(server, "GET", "/nope")
    assert resp.status == 404
