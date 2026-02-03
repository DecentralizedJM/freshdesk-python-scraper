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

    def search_tickets(self, query: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        Searches for tickets using a keyword and optional date range. 
        """
        all_tickets = []
        page = 1
        
        print(f"Searching for query: '{query}' with Date Range: {start_date} to {end_date}")
        
        # Construct Query
        # Base: "keyword"
        # If dates provided: "keyword AND created_at:>'2023-01-01' AND created_at:<'2023-02-01'"
        # Note: Freshdesk requires URL encoding. We'll let requests handle the param encoding, 
        # but the query syntax itself must be correct.
        
        final_query = f"\"{query}\""
        
        if start_date:
            final_query += f" AND created_at: >'{start_date}'"
        if end_date:
            final_query += f" AND created_at: <'{end_date}'"
            
        # IMPORTANT: Freshdesk search query length is limited.
        
        while True:
            params = {
                "query": final_query,
                "page": page
            }
            
            # The URL needs the query to be properly passed. 
            # requests.get(params=params) will encode spaces as +, but Freshdesk prefers %20 usually, 
            # let's trust requests for now but if it fails we might need manual string construction.
            
            url = f"{self.base_url}/search/tickets"
            response = self.session.get(url, params=params)
            
            if response.status_code == 429:
                print("Rate limit exceeded. Waiting 60 seconds...")
                time.sleep(60)
                continue
                
            if response.status_code != 200:
                print(f"Error fetching page {page} query='{final_query}': {response.text}")
                break
                
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                break
                
            all_tickets.extend(results)
            print(f"Fetched {len(results)} tickets from page {page}...")
            
            if len(results) < 30: # Last page
                break
                
            page += 1
            
            if page > 100: # Increased safety limit for "thousands"
                print("Configuration safety limit: stopping after 100 pages.")
                break
                
        return all_tickets

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
