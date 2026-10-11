import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi.testclient import TestClient

from main import app
from spotify import web_api


class SpotifyApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.environment = patch.dict("os.environ", {
            "SPOTIFY_CLIENT_ID": "test-client",
            "SPOTIFY_CLIENT_SECRET": "test-secret",
            "SPOTIFY_REDIRECT_URI": "http://testserver/callback",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(self.client.close)

    def mock_spotify(self, handler):
        real_client = httpx.AsyncClient
        mock = patch.object(web_api.httpx, "AsyncClient", side_effect=lambda **kwargs:
                            real_client(transport=httpx.MockTransport(handler), **kwargs))
        mock.start()
        self.addCleanup(mock.stop)

    def test_refresh_preserves_refresh_token(self) -> None:
        def handler(request):
            self.assertEqual(str(request.url), web_api.SPOTIFY_TOKEN_URL)
            self.assertEqual(request.headers["content-type"], "application/x-www-form-urlencoded")
            self.assertTrue(request.headers["authorization"].startswith("Basic "))
            self.assertEqual(parse_qs(request.content.decode()), {
                "grant_type": ["refresh_token"], "refresh_token": ["old-refresh"],
            })
            return httpx.Response(200, json={"access_token": "new-access", "expires_in": 3600})

        self.mock_spotify(handler)
        response = self.client.post("/spotify/token", json={
            "grant_type": "refresh_token", "refresh_token": "old-refresh",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["refresh_token"], "old-refresh")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_exchange_requires_valid_state_and_clears_cookie(self) -> None:
        self.mock_spotify(lambda request: httpx.Response(200, json={
            "access_token": "access", "refresh_token": "refresh",
        }))
        body = {"grant_type": "authorization_code", "code": "code", "state": "state"}
        self.assertEqual(self.client.post("/spotify/token", json=body).status_code, 400)
        self.client.cookies.set("spotify_oauth_state", "state")
        response = self.client.post("/spotify/token", json=body)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_token_validation(self) -> None:
        for body in ({"grant_type": "refresh_token"},
                     {"grant_type": "authorization_code", "code": "code"},
                     {"grant_type": "client_credentials"}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/spotify/token", json=body).status_code, 422)

    def test_profile_and_missing_bearer(self) -> None:
        self.assertEqual(self.client.get("/spotify/me").status_code, 401)
        self.assertEqual(self.client.get("/spotify/users/user/playlists").status_code, 401)

        def handler(request):
            self.assertEqual(str(request.url), f"{web_api.SPOTIFY_API_URL}/me")
            self.assertEqual(request.headers["authorization"], "Bearer access")
            return httpx.Response(200, json={"id": "user", "display_name": "Test User"})

        self.mock_spotify(handler)
        response = self.client.get("/spotify/me", headers={"Authorization": "Bearer access"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "user")

    def test_all_playlist_pages(self) -> None:
        offsets = []

        def handler(request):
            self.assertEqual(request.url.path, "/v1/users/user/playlists")
            self.assertEqual(request.url.params["limit"], "50")
            offset = int(request.url.params["offset"])
            offsets.append(offset)
            # A next URL must never be followed with the bearer credential.
            return httpx.Response(200, json={
                "items": [{"id": str(offset)}],
                "next": "https://untrusted.example/page" if offset == 0 else None,
            })

        self.mock_spotify(handler)
        response = self.client.get("/spotify/users/user/playlists",
                                   headers={"Authorization": "Bearer access"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(offsets, [0, 1])
        self.assertEqual(response.json(), {"items": [{"id": "0"}, {"id": "1"}], "total": 2})

    def test_upstream_errors_and_rate_limit(self) -> None:
        def handler(request):
            return httpx.Response(429, headers={"Retry-After": "30"},
                                  json={"error": {"message": "secret upstream details"}})

        self.mock_spotify(handler)
        response = self.client.get("/spotify/me", headers={"Authorization": "Bearer access"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "30")
        self.assertNotIn("secret upstream details", response.text)

    def test_timeout(self) -> None:
        def handler(request):
            raise httpx.ReadTimeout("timeout", request=request)

        self.mock_spotify(handler)
        response = self.client.get("/spotify/me", headers={"Authorization": "Bearer access"})
        self.assertEqual(response.status_code, 504)

    def test_malformed_response(self) -> None:
        self.mock_spotify(lambda request: httpx.Response(200, text="not json"))
        response = self.client.get("/spotify/me", headers={"Authorization": "Bearer access"})
        self.assertEqual(response.status_code, 502)

    def test_callback_returns_fragment_without_profile(self) -> None:
        self.mock_spotify(lambda request: httpx.Response(200, json={
            "access_token": "access", "refresh_token": "refresh",
            "token_type": "Bearer", "expires_in": 3600,
        }))
        self.client.cookies.set("spotify_oauth_state", "state")
        response = self.client.get("/callback?code=code&state=state", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        target = urlparse(response.headers["location"])
        self.assertEqual(target.query, "")
        self.assertEqual(parse_qs(target.fragment)["access_token"], ["access"])
        self.assertNotIn("profile", parse_qs(target.fragment))


if __name__ == "__main__":
    unittest.main()