import urllib.parse
import urllib.request
import re

from overnight_agent.testsite import serve


def test_controlled_site_health_and_validation(tmp_path):
    server, _ = serve(upload_dir=tmp_path)
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        assert urllib.request.urlopen(base + "/health").status == 200
        body = urllib.parse.urlencode({"name": "Ada"}).encode()
        request = urllib.request.Request(base + "/step1", data=body)
        try:
            urllib.request.urlopen(request)
            raise AssertionError("expected HTTP 422")
        except urllib.error.HTTPError as error:
            assert error.code == 422
    finally:
        server.shutdown()
        server.server_close()


def test_controlled_application_can_complete_all_steps(tmp_path):
    server, _ = serve(upload_dir=tmp_path)
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        step1 = urllib.parse.urlencode(
            {
                "name": "Research Candidate",
                "email": "candidate@example.test",
                "start_date": "2027-01-01",
            }
        ).encode()
        html = (
            urllib.request.urlopen(urllib.request.Request(base + "/step1", data=step1))
            .read()
            .decode()
        )
        token = re.search(r"name=token value=([a-f0-9]+)", html).group(1)

        boundary = "----overnight-agent-test"
        parts = []
        for name, value in {
            "token": token,
            "motivation": "I am interested in this role.",
            "ai_used": "yes",
        }.items():
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
            )
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="resume"; filename="resume.pdf"\r\n'
            "Content-Type: application/pdf\r\n\r\n%PDF-fixture\r\n".encode()
        )
        parts.append(f"--{boundary}--\r\n".encode())
        request = urllib.request.Request(base + "/step2", data=b"".join(parts))
        request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        assert b"Verification challenge" in urllib.request.urlopen(request).read()

        final = urllib.parse.urlencode({"token": token, "verification": "13"}).encode()
        response = urllib.request.urlopen(
            urllib.request.Request(base + "/submit", data=final)
        ).read()
        assert b"Application submitted" in response
        assert b"LOCAL-" in response
        assert list(tmp_path.glob("*.pdf"))
    finally:
        server.shutdown()
        server.server_close()
