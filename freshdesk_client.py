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

    def _list_tickets(
        self,
        updated_since: str = None,
        max_pages: int = 150,
        order_by: str = None,
        order_type: str = None,
        stop_after_date: str = None,
    ) -> List[Dict[str, Any]]:
        """Fetch tickets via list endpoint (GET /tickets)."""
        all_tickets = []
        page = 1
        url = f"{self.base_url}/tickets"
        while page <= max_pages:
            params = {"page": page, "per_page": 100, "include": "description"}
            if updated_since:
                params["updated_since"] = updated_since
            if order_by:
                params["order_by"] = order_by
            if order_type:
                params["order_type"] = order_type
            response = self.session.get(url, params=params)
            if response.status_code == 429:
                print("Rate limit exceeded. Waiting 60 seconds...")
                time.sleep(60)
                continue
            if response.status_code != 200:
                print(f"Error listing tickets page {page}: {response.text}")
                return []
            tickets = response.json()
            if not tickets:
                break
            for t in tickets:
                if stop_after_date:
                    created = (t.get("created_at") or "")[:10]
                    if created and created > stop_after_date:
                        print(f"Fetched {len(all_tickets)} tickets (reached end_date), stopping.")
                        return all_tickets
                all_tickets.append(t)
            print(f"Fetched {len(tickets)} tickets from page {page}...")
            if len(tickets) < 100:
                break
            page += 1
            time.sleep(0.5)
        return all_tickets

    def search_tickets(self, query: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        Searches for tickets using a keyword and optional date range.
        Uses list tickets API + client-side filtering; the search/tickets query format
        is not reliably supported across Freshdesk instances.
        """
        print(f"Searching for query: '{query}' with Date Range: {start_date} to {end_date}")
        keyword = (query or "").strip()

        # Use list endpoint - updated_since + order for date ranges
        from datetime import datetime, timedelta, timezone
        updated_since = None
        order_by = None
        order_type = None
        stop_after_date = None
        if start_date:
            try:
                d = datetime.strptime(start_date, "%Y-%m-%d")
                updated_since = d.strftime("%Y-%m-%dT00:00:00Z")
            except ValueError:
                updated_since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        elif end_date:
            updated_since = "2020-01-01T00:00:00Z"
        else:
            updated_since = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
        if end_date:
            stop_after_date = end_date
        if start_date or end_date:
            order_by = "created_at"
            order_type = "asc"
            max_pages = 150
        else:
            max_pages = 50

        tickets = self._list_tickets(
            updated_since=updated_since,
            max_pages=max_pages,
            order_by=order_by,
            order_type=order_type,
            stop_after_date=stop_after_date,
        )

        # Filter by keyword
        if keyword:
            kw_lower = keyword.lower()
            tickets = [
                t for t in tickets
                if kw_lower in (t.get("subject") or "").lower()
                or kw_lower in (str(t.get("description") or t.get("description_text") or "")).lower()
            ]
            print(f"Client-side filter: {len(tickets)} tickets match keyword.")

        # Filter by date range
        if start_date or end_date:
            filtered = []
            for t in tickets:
                created = (t.get("created_at") or "")[:10]
                if not created:
                    continue
                if start_date and created < start_date:
                    continue
                if end_date and created > end_date:
                    continue
                filtered.append(t)
            tickets = filtered

        return tickets

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
