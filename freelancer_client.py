import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import requests

API_BASE = "https://www.freelancer.com/api"

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class FreelancerClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        oauth_token: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        self.api_key = api_key or os.getenv("FREELANCER_API_KEY")
        self.oauth_token = (
            oauth_token
            or os.getenv("FREELANCER_OAUTH_TOKEN")
            or os.getenv("AccessToken")
        )
        self.timeout = timeout

        if not self.api_key and not self.oauth_token:
            raise RuntimeError(
                "Freelancer credentials are missing. Set FREELANCER_API_KEY or "
                "FREELANCER_OAUTH_TOKEN/AccessToken (via environment or .env)."
            )

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Freelancer-Developer-OAuth-Client-Id"] = self.api_key
        if self.oauth_token:
            headers["freelancer-oauth-v1"] = self.oauth_token
        return headers

    def search_projects(
        self,
        query: Optional[str] = None,
        languages: Optional[List[str]] = None,
        countries: Optional[List[str]] = None,
        jobs: Optional[List[int]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "compact": "true",
            "limit": limit,
            "offset": offset,
        }
        if query:
            params["query"] = query
        if languages:
            params["languages[]"] = languages
        if countries:
            params["countries[]"] = countries
        if jobs:
            params["jobs[]"] = [str(j) for j in jobs]

        url = f"{API_BASE}/projects/0.1/projects/active/"
        response = requests.get(
            url, headers=self._headers(), params=params, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        result = data.get("result", {})
        projects = result.get("projects")
        if not isinstance(projects, list):
            raise RuntimeError("Unexpected API response: missing 'projects' list.")
        return projects
