import os
import sys
import datetime
from config import FRESHDESK_DOMAIN, FRESHDESK_API_KEY
from freshdesk_client import FreshdeskClient
from report_generator import generate_report
from ai_processor import TicketAnalyzer

def get_input(prompt, default=None):
    text = input(prompt)
    if not text and default is not None:
        return default
    return text

def main():
    print("=== Freshdesk Smart Scraper ===")
    
    if not FRESHDESK_DOMAIN or not FRESHDESK_API_KEY:
        print("Error: Please set FRESHDESK_DOMAIN and FRESHDESK_API_KEY in .env file.")
        return

    # Initialize Clients
    client = FreshdeskClient(FRESHDESK_DOMAIN, FRESHDESK_API_KEY)
    ai = TicketAnalyzer() # Will init based on keys in .env
    
    # 1. Gather Inputs
    keyword = get_input("Enter Keyword to Search (e.g. 'refund'): ")
    start_date = get_input("Enter Start Date (YYYY-MM-DD) [Optional - Press Enter to skip]: ", default="")
    end_date = get_input("Enter End Date (YYYY-MM-DD) [Optional]: ", default="")
    intent = get_input("Enter Specific Intent for AI Analysis (e.g. 'Users asking for refunds due to app crash') [Optional]: ", default="")
    
    if not keyword:
        print("Keyword is required.")
        return

    # 2. Search
    print(f"\n--- STEP 1: Searching Freshdesk ---")
    found_tickets = client.search_tickets(keyword, start_date if start_date else None, end_date if end_date else None)
    print(f"Total Tickets Found: {len(found_tickets)}")
    
    if not found_tickets:
        print("No tickets found. Exiting.")
        return
        
    # 3. Process Details + AI Analysis
    detailed_tickets = []
    total = len(found_tickets)
    
    print(f"\n--- STEP 2: Fetching Details & Analyzing Intent ---")
    print(f"AI Mode: {ai.mode.upper()}")
    
    for i, ticket in enumerate(found_tickets):
        t_id = ticket['id']
        sys.stdout.write(f"\rProcessing {i+1}/{total} (Ticket #{t_id})...")
        sys.stdout.flush()
        
        # A. Fetch full conversation
        full_ticket = client.get_ticket_details(t_id)
        if not full_ticket:
            continue
            
        # B. AI Analysis
        # We combine subject + description + conversation for analysis
        combined_text = f"Subject: {full_ticket.get('subject')}\nDescription: {full_ticket.get('description_text')}\n"
        # Add a bit of conversation if available
        for conv in full_ticket.get('conversations', [])[:3]: # limit to first 3 to save tokens
            combined_text += f"Reply: {conv.get('body_text')}\n"
            
        is_relevant, summary = ai.analyze(combined_text, intent)
        
        full_ticket['ai_relevant'] = is_relevant
        full_ticket['ai_summary'] = summary
        
        # If user wants ONLY relevant tickets, we could filter here. 
        # But usually better to keep all in report and mark them.
        detailed_tickets.append(full_ticket)

    print("\nProcessing complete.")

    # 4. Generate Report
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_kw = "".join([c for c in keyword if c.isalnum()])
    filename = f"report_{clean_kw}_{timestamp}.xlsx"
    
    generate_report(detailed_tickets, filename=filename)
    
    print(f"\nSUCCESS! Report saved to: {filename}")
    print("Open the Excel file to see the 'AI Relevance' and 'AI Summary' columns.")

if __name__ == "__main__":
    main()
