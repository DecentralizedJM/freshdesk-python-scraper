import requests
import base64
import time
from typing import List, Dict, Any

class FreshdeskClient:
    def __init__(self, domain: str, api_key: str):
        self.domain = domain.rstrip('/')
        self.api_key = api_key
        self.base_url = f"https://{self.domain}/api/v2"
        self.session = requests.Session()
        
        # Freshdesk requires Basic Auth with API key as username and 'X' as password
        auth_str = f"{self.api_key}:X"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        self.session.headers.update({
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json"
        })

    def _fetch_by_query(self, final_query: str) -> List[Dict[str, Any]]:
        """Fetch tickets by a single query string; used internally."""
        all_tickets = []
        page = 1
        url = f"{self.base_url}/search/tickets"
        while True:
            params = {"query": final_query, "page": page}
            response = self.session.get(url, params=params)
            if response.status_code == 429:
                print("Rate limit exceeded. Waiting 60 seconds...")
                time.sleep(60)
                continue
            if response.status_code != 200:
                print(f"Error fetching page {page} query='{final_query}': {response.text}")
                return None  # signal failure to caller
            data = response.json()
            results = data.get("results", [])
            if not results:
                break
            all_tickets.extend(results)
            print(f"Fetched {len(results)} tickets from page {page}...")
            if len(results) < 30:
                break
            page += 1
            if page > 100:
                print("Configuration safety limit: stopping after 100 pages.")
                break
        return all_tickets

    def search_tickets(self, query: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        Searches for tickets using a keyword and optional date range.
        Freshdesk requires query format: field:value [OPERATOR field:value ...]
        (e.g. subject:'API' AND created_at:>'2023-01-01'). If subject is not
        supported, we fall back to date-only + client-side keyword filter.
        """
        print(f"Searching for query: '{query}' with Date Range: {start_date} to {end_date}")
        keyword = (query or "").strip()
        query_escaped = keyword.replace("'", "\\'")

        # Build query: subject:'keyword' and optional date filters
        final_query = f"subject:'{query_escaped}'" if query_escaped else ""
        if start_date:
            final_query += (" AND " if final_query else "") + f"created_at:>'{start_date}'"
        if end_date:
            final_query += (" AND " if final_query else "") + f"created_at:<'{end_date}'"

        # If no keyword and no dates, we need at least one condition; use a broad status filter
        if not final_query:
            final_query = "status:>0"  # any non-deleted

        tickets = self._fetch_by_query(final_query)
        if tickets is not None:
            return tickets

        # Fallback: subject may not be supported on this instance; fetch by date only and filter
        print("Query with subject failed; retrying with date-only and filtering by keyword client-side.")
        fallback_query_parts = []
        if start_date:
            fallback_query_parts.append(f"created_at:>'{start_date}'")
        if end_date:
            fallback_query_parts.append(f"created_at:<'{end_date}'")
        fallback_query = " AND ".join(fallback_query_parts) if fallback_query_parts else "status:>0"
        tickets = self._fetch_by_query(fallback_query)
        if tickets is None:
            return []

        if not keyword:
            return tickets
        kw_lower = keyword.lower()
        filtered = [
            t for t in tickets
            if kw_lower in (t.get("subject") or "").lower() or kw_lower in (t.get("description") or "").lower()
        ]
        print(f"Client-side filter: {len(filtered)} of {len(tickets)} tickets match keyword.")
        return filtered

    def get_ticket_details(self, ticket_id: int) -> Dict[str, Any]:
        """
        Fetches full details for a ticket, including conversations.
        """
        url = f"{self.base_url}/tickets/{ticket_id}"
        params = {"include": "conversations"}
        
        while True:
            response = self.session.get(url, params=params)
            
            if response.status_code == 429:
                print(f"Rate limit exceeded on ticket {ticket_id}. Waiting...")
                time.sleep(60)
                continue
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching ticket {ticket_id}: {response.text}")
                return {}
